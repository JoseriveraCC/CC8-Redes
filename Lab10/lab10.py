#!/usr/bin/env python3
"""Ayuda mínima para captura WEP autorizada y recuperación sin diccionario."""

import argparse
from pathlib import Path
import platform
import re
import shlex
import shutil
import subprocess


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


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    commands = result.add_subparsers(dest="accion", required=True)
    commands.add_parser("comprobar", help="diagnóstico local, sin escanear redes")
    capture = commands.add_parser("capturar", help="captura pasiva del AP autorizado")
    capture.add_argument("--interfaz", required=True, type=interfaz)
    capture.add_argument("--bssid", required=True, type=bssid)
    capture.add_argument("--canal", required=True, type=canal)
    capture.add_argument("--salida", default="capturas/captura")
    recover = commands.add_parser("recuperar", help="analiza un archivo WEP, sin transmitir")
    recover.add_argument("captura", type=Path)
    recover.add_argument("--bssid", required=True, type=bssid)
    recover.add_argument("--clave", default="capturas/clave.txt")
    for command in (capture, recover):
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


def main(argv=None):
    cli = parser()
    args = cli.parse_args(argv)
    if args.accion == "comprobar":
        return comprobar()
    if args.accion == "capturar":
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
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        return subprocess.call(command)
    except KeyboardInterrupt:
        return 130
    except OSError as error:
        cli.error(str(error))


if __name__ == "__main__":
    raise SystemExit(main())
