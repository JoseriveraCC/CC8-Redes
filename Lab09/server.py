#!/usr/bin/env python3
"""Receptor TCP de una subida de diez archivos de 1000 bytes en una conexión."""

import argparse
import hashlib
from pathlib import Path
import socket
import sys

from speedtest import FILE_COUNT, FILE_SIZE, port_number, positive_seconds


def receive_upload(connection, output):
    """TCP es un flujo: un recv() no equivale a un archivo o a un segmento."""
    expected = FILE_COUNT * FILE_SIZE
    data = bytearray()
    while True:
        chunk = connection.recv(min(4096, expected + 1 - len(data)))
        if not chunk:
            break
        data.extend(chunk)
        if len(data) > expected:
            raise ValueError(f"Se recibieron más de {expected} bytes")
    if len(data) != expected:
        raise ValueError(f"Subida incompleta: {len(data)}/{expected} bytes")
    first = data[:FILE_SIZE]
    if any(data[i:i + FILE_SIZE] != first for i in range(FILE_SIZE, expected, FILE_SIZE)):
        raise ValueError("Los diez bloques no son copias del mismo archivo")
    output.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bind", default="127.0.0.1")
    parser.add_argument("--port", type=port_number, default=3001)
    parser.add_argument("--output", type=Path, default=Path("recibido.bin"))
    parser.add_argument("--timeout", type=positive_seconds, default=15.0)
    args = parser.parse_args()
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.bind((args.bind, args.port))
            listener.listen(1)
            print(f"Esperando una conexión TCP en {args.bind}:{args.port}", flush=True)
            connection, address = listener.accept()
            with connection:
                connection.settimeout(args.timeout)
                print(f"Cliente: {address[0]}:{address[1]}", flush=True)
                digest = receive_upload(connection, args.output)
        print(f"Recibidos {FILE_COUNT} archivos de {FILE_SIZE} bytes: {FILE_COUNT * FILE_SIZE} bytes")
        print(f"SHA-256 de la subida completa: {digest}")
        print(f"Guardado: {args.output}")
        return 0
    except (OSError, ValueError) as error:
        print(f"Error del receptor: {error}", file=sys.stderr)
    except KeyboardInterrupt:
        print("Receptor interrumpido", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
