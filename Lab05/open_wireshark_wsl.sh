#!/usr/bin/env bash
set -euo pipefail

IFACE="${1:-lo}"
FILTER="${2:-tcp port 5001}"
WIRESHARK_WIN="${WIRESHARK_WIN:-/mnt/c/Program Files/Wireshark/Wireshark.exe}"

if [ ! -x "$WIRESHARK_WIN" ]; then
    echo "No encontre Wireshark en: $WIRESHARK_WIN" >&2
    echo "Si esta en otra ruta, ejecuta:" >&2
    echo "WIRESHARK_WIN='/mnt/c/ruta/a/Wireshark.exe' $0" >&2
    exit 1
fi

if ! command -v tcpdump >/dev/null 2>&1; then
    echo "tcpdump no esta instalado en WSL." >&2
    echo "Instalalo con: sudo apt update && sudo apt install tcpdump" >&2
    exit 1
fi

echo "Capturando en WSL interfaz: $IFACE" >&2
echo "Filtro: $FILTER" >&2
echo "Abriendo Wireshark de Windows..." >&2
echo "Deten la captura cerrando Wireshark o presionando Ctrl+C aqui." >&2

sudo tcpdump -i "$IFACE" -p -n -U -s 0 -w - "$FILTER" | "$WIRESHARK_WIN" -k -i -
