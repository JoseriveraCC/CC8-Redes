#!/usr/bin/env python3
"""Lab09: subida TCP con encabezados y estado construidos en espacio de usuario."""

import argparse
import csv
from dataclasses import dataclass
import hashlib
import math
from pathlib import Path
import secrets
import socket
import statistics
import struct
import sys
import time

FILE_SIZE = 1000  # KB decimal, como en el ejemplo numérico del PDF.
FILE_COUNT = 10
FIN, SYN, RST, PSH, ACK = 0x01, 0x02, 0x04, 0x08, 0x10
MASK = 0xFFFFFFFF


def checksum(data):
    """Complemento a uno de palabras de 16 bits en orden de red."""
    data += b"\0" * (len(data) % 2)
    total = sum(struct.unpack(f"!{len(data) // 2}H", data))
    while total >> 16:
        total = (total & 0xFFFF) + (total >> 16)
    return (~total) & 0xFFFF


def build_packet(source, destination, seq, ack, flags, data=b"", options=b"", window=65535):
    """Construye IPv4 + TCP, incluido el pseudoencabezado para el checksum TCP."""
    src, dst = socket.inet_aton(source[0]), socket.inet_aton(destination[0])
    if len(options) % 4 or len(options) > 40:
        raise ValueError("Las opciones TCP deben ocupar múltiplos de 4 bytes, máximo 40")
    tcp = struct.pack("!HHIIBBHHH", source[1], destination[1], seq & MASK, ack & MASK,
                      (5 + len(options) // 4) << 4, flags, window, 0, 0) + options
    pseudo = src + dst + struct.pack("!BBH", 0, socket.IPPROTO_TCP, len(tcp) + len(data))
    tcp = tcp[:16] + struct.pack("!H", checksum(pseudo + tcp + data)) + tcp[18:]
    ip = struct.pack("!BBHHHBBH4s4s", 0x45, 0, 20 + len(tcp) + len(data),
                     0, 0x4000, 64, socket.IPPROTO_TCP, 0, src, dst)
    ip = ip[:10] + struct.pack("!H", checksum(ip)) + ip[12:]
    return ip + tcp + data


@dataclass(frozen=True)
class Segment:
    source: tuple
    destination: tuple
    seq: int
    ack: int
    flags: int
    window: int
    options: bytes
    data: bytes


def parse_packet(packet):
    """Descarta paquetes truncados, fragmentados o que no son IPv4/TCP."""
    if len(packet) < 40 or packet[0] >> 4 != 4 or packet[9] != socket.IPPROTO_TCP:
        return None
    ihl = (packet[0] & 15) * 4
    total = struct.unpack_from("!H", packet, 2)[0]
    fragment = struct.unpack_from("!H", packet, 6)[0]
    if ihl < 20 or total < ihl + 20 or total > len(packet) or fragment & 0x3FFF:
        return None
    if checksum(packet[:ihl]) != 0:
        return None
    tcp = packet[ihl:total]
    sport, dport, seq, ack, offset, flags, window = struct.unpack_from("!HHIIBBH", tcp)
    header_length = (offset >> 4) * 4
    if header_length < 20 or header_length > len(tcp):
        return None
    # ponytail: capturas locales pueden tener checksum TCP pendiente por offload;
    # validar también recepción requiere metadatos PACKET_AUXDATA de AF_PACKET.
    return Segment((socket.inet_ntoa(packet[12:16]), sport),
                   (socket.inet_ntoa(packet[16:20]), dport), seq, ack, flags, window,
                   tcp[20:header_length], tcp[header_length:])


def peer_mss(options):
    """Sin opción MSS, el valor TCP por defecto en IPv4 es 536 bytes."""
    index = 0
    while index < len(options):
        kind = options[index]
        if kind == 0:
            break
        if kind == 1:
            index += 1
            continue
        if index + 1 >= len(options):
            raise ConnectionError("Opción TCP truncada")
        length = options[index + 1]
        if length < 2 or index + length > len(options):
            raise ConnectionError("Longitud de opción TCP inválida")
        if kind == 2:
            if length != 4:
                raise ConnectionError("Opción MSS inválida")
            value = struct.unpack_from("!H", options, index + 2)[0]
            if value == 0:
                raise ConnectionError("MSS cero")
            return value
        index += length
    return 536


def flag_names(flags):
    return "|".join(name for bit, name in [(SYN, "SYN"), (PSH, "PSH"), (FIN, "FIN"),
                                            (RST, "RST"), (ACK, "ACK")] if flags & bit)


class RawTCP:
    """Una conexión de subida, con una ventana de envío de un segmento."""

    def __init__(self, wire, source, destination, timeout=2.0, retries=2, verbose=False):
        self.wire, self.source, self.destination = wire, source, destination
        self.timeout, self.retries, self.verbose = timeout, retries, verbose
        self.seq, self.ack = secrets.randbits(32), 0
        self.mss, self.window = 536, 65535
        self.retransmissions = 0

    def send(self, flags, data=b"", options=b""):
        packet = build_packet(self.source, self.destination, self.seq, self.ack, flags, data, options)
        self.wire.sendto(packet, (self.destination[0], 0))
        if self.verbose:
            print(f"[TX] {flag_names(flags)} SEQ={self.seq} ACK={self.ack} bytes={len(data)}")

    def receive(self, deadline):
        while True:
            remaining = deadline - time.perf_counter()
            if remaining <= 0:
                raise TimeoutError("Se agotó el tiempo de espera TCP")
            self.wire.settimeout(remaining)
            segment = parse_packet(self.wire.recvfrom(65535)[0])
            if segment is None or segment.source != self.destination or segment.destination != self.source:
                continue
            if self.verbose:
                print(f"[RX] {flag_names(segment.flags)} SEQ={segment.seq} "
                      f"ACK={segment.ack} bytes={len(segment.data)}")
            if segment.flags & RST:
                raise ConnectionError("RST del servidor: revise el puerto y el bloqueo RST local")
            return segment

    def connect(self):
        expected = (self.seq + 1) & MASK
        started = time.perf_counter()
        for attempt in range(self.retries + 1):
            self.retransmissions += int(attempt > 0)
            self.send(SYN, options=struct.pack("!BBH", 2, 4, 1460))
            deadline = time.perf_counter() + self.timeout
            try:
                while True:
                    segment = self.receive(deadline)
                    if (segment.flags & (SYN | ACK | FIN)) != (SYN | ACK) or segment.ack != expected:
                        continue
                    if segment.data:
                        raise ConnectionError("No se admiten datos en SYN+ACK")
                    elapsed = time.perf_counter() - started
                    self.seq, self.ack = expected, (segment.seq + 1) & MASK
                    self.mss, self.window = peer_mss(segment.options), segment.window
                    self.send(ACK)
                    return elapsed
            except TimeoutError:
                if attempt == self.retries:
                    raise TimeoutError("Sin SYN+ACK; revise servidor, ruta y regla RST") from None

    def upload_file(self, data):
        started = time.perf_counter()
        position = 0
        while position < len(data):
            if self.window == 0:
                raise ConnectionError("Ventana del receptor en cero; esta práctica no implementa persistencia")
            chunk = data[position:position + min(self.mss, self.window)]
            expected = (self.seq + len(chunk)) & MASK
            for attempt in range(self.retries + 1):
                self.retransmissions += int(attempt > 0)
                self.send(PSH | ACK, chunk)
                deadline = time.perf_counter() + self.timeout
                try:
                    while True:
                        segment = self.receive(deadline)
                        if segment.flags & FIN or segment.data:
                            raise ConnectionError("El receptor cerró o envió datos antes de terminar")
                        if segment.flags & SYN:
                            if segment.ack == self.seq and (segment.seq + 1) & MASK == self.ack:
                                self.send(ACK)  # SYN+ACK repetido si se perdió el tercer paso.
                            continue
                        if segment.flags & ACK and segment.ack == expected and segment.seq == self.ack:
                            self.window = segment.window
                            break
                    break
                except TimeoutError:
                    if attempt == self.retries:
                        raise TimeoutError("No llegó el ACK de los datos") from None
            self.seq = expected
            position += len(chunk)
        return time.perf_counter() - started

    def disconnect(self):
        """Admite ACK y FIN separados o combinados, y vuelve a confirmar FIN duplicado."""
        fin_seq, expected = self.seq, (self.seq + 1) & MASK
        acknowledged = finished = False
        for attempt in range(self.retries + 1):
            self.retransmissions += int(attempt > 0)
            self.seq = fin_seq
            self.send(FIN | ACK)
            self.seq = expected
            deadline = time.perf_counter() + self.timeout
            try:
                while not (acknowledged and finished):
                    segment = self.receive(deadline)
                    if segment.data or segment.flags & SYN:
                        raise ConnectionError("Segmento inesperado durante el cierre")
                    if segment.flags & ACK and segment.ack == expected:
                        acknowledged = True
                    if segment.flags & FIN and segment.seq == self.ack:
                        self.ack = (self.ack + 1) & MASK
                        finished = True
                        self.send(ACK)
                    elif segment.flags & FIN and (segment.seq + 1) & MASK == self.ack:
                        self.send(ACK)
                break
            except TimeoutError:
                if attempt == self.retries:
                    raise TimeoutError("Cierre TCP incompleto: falta ACK o FIN") from None
        # ponytail: TIME-WAIT didáctico de un segundo; TCP general necesita 2*MSL.
        deadline = time.perf_counter() + 1.0
        try:
            while True:
                segment = self.receive(deadline)
                if segment.flags & FIN and (segment.seq + 1) & MASK == self.ack:
                    self.send(ACK)
        except TimeoutError:
            pass


def port_number(text):
    value = int(text)
    if not 1 <= value <= 65535:
        raise argparse.ArgumentTypeError("El puerto debe estar entre 1 y 65535")
    return value


def positive_seconds(text):
    value = float(text)
    if not math.isfinite(value) or value <= 0:
        raise argparse.ArgumentTypeError("El tiempo debe ser finito y mayor que cero")
    return value


def estimate_kbps(size, latency, average):
    return size * 8 / (latency + average) / 1000


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server", default="127.0.0.1", help="Nombre o IPv4 del receptor")
    parser.add_argument("--port", type=port_number, default=3001)
    parser.add_argument("--source-port", type=port_number, default=40000)
    parser.add_argument("--file", type=Path, default=Path(__file__).with_name("archivo_1kb.bin"))
    parser.add_argument("--csv", type=Path, default=Path("resultados.csv"))
    parser.add_argument("--timeout", type=positive_seconds, default=2.0)
    parser.add_argument("--retries", type=int, choices=range(0, 6), default=2)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    try:
        data = args.file.read_bytes()
        if len(data) != FILE_SIZE:
            raise ValueError(f"El archivo debe tener exactamente {FILE_SIZE} bytes")
        destination = (socket.gethostbyname(args.server), args.port)
        # Solo consulta la ruta; no envía UDP ni establece una conexión TCP del SO.
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as route:
            route.connect(destination)
            source = (route.getsockname()[0], args.source_port)
        if source == destination:
            raise ValueError("Los extremos local y remoto deben ser distintos")
        # Reserva el puerto para que ningún otro proceso lo use; nunca llama connect().
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as reservation:
            reservation.bind(source)
            with socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_TCP) as wire:
                wire.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
                wire.bind((source[0], 0))
                tcp = RawTCP(wire, source, destination, args.timeout, args.retries, args.verbose)
                print(f"Subida RAW {source[0]}:{source[1]} -> {destination[0]}:{destination[1]}")
                latency = tcp.connect()
                samples = []
                try:
                    for index in range(1, FILE_COUNT + 1):
                        elapsed = tcp.upload_file(data)
                        samples.append(elapsed)
                        print(f"Archivo {index:02d}/{FILE_COUNT}: {len(data)} bytes, "
                              f"RTT + transmisión = {elapsed * 1000:.6f} ms")
                    tcp.disconnect()
                except (OSError, ValueError):
                    tcp.send(RST | ACK)
                    raise
        average = statistics.mean(samples)
        with args.csv.open("w", newline="", encoding="utf-8") as output:
            writer = csv.writer(output)
            writer.writerow(["archivo", "bytes", "rtt_transmision_ms"])
            writer.writerows((i, len(data), f"{sample * 1000:.9f}")
                             for i, sample in enumerate(samples, 1))
        print(f"Latencia TCP (SYN -> SYN+ACK): {latency * 1000:.6f} ms")
        print(f"Promedio RTT + transmisión ({FILE_COUNT} archivos): {average * 1000:.6f} ms")
        print(f"Velocidad de subida estimada (fórmula PDF): {estimate_kbps(len(data), latency, average):.6f} Kbps")
        print(f"Total confirmado: {len(data) * FILE_COUNT} bytes en una conexión")
        print(f"Retransmisiones: {tcp.retransmissions}; muestras guardadas en {args.csv}")
        print(f"SHA-256 del archivo: {hashlib.sha256(data).hexdigest()}")
        return 0
    except PermissionError as error:
        print(f"Error: {error}. SOCK_RAW requiere root o CAP_NET_RAW en Linux.", file=sys.stderr)
    except (OSError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
    except KeyboardInterrupt:
        print("Medición interrumpida", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
