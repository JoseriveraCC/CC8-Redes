#!/usr/bin/env python3
"""Prueba RAW real; ejecutar con sudo make integration en Linux."""

import csv
import hashlib
import os
from pathlib import Path
import select
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parent_netns = os.environ.get("LAB09_PARENT_NETNS")
    if os.geteuid() != 0 or not parent_netns or os.readlink("/proc/self/ns/net") == parent_netns:
        raise RuntimeError("Use make integration-user o sudo make integration: requiere una red aislada")
    subprocess.run(["ip", "link", "set", "lo", "up"], check=True)
    rule = ["OUTPUT", "-p", "tcp", "-s", "127.0.0.1", "--sport", "40000",
            "-d", "127.0.0.1", "--dport", "3001", "--tcp-flags", "RST", "RST", "-j", "DROP"]
    subprocess.run(["iptables", "-I", *rule], check=True)
    try:
        with tempfile.TemporaryDirectory(prefix="lab09-integration-") as folder:
            output, samples = Path(folder) / "received.bin", Path(folder) / "samples.csv"
            receiver = subprocess.Popen([sys.executable, "-u", str(ROOT / "server.py"),
                                         "--output", str(output)],
                                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            try:
                if not select.select([receiver.stdout], [], [], 5)[0]:
                    raise RuntimeError("El receptor no inició en cinco segundos")
                ready = receiver.stdout.readline()
                if "Esperando" not in ready:
                    raise RuntimeError(f"No inició el receptor: {ready}")
                client = subprocess.run([sys.executable, str(ROOT / "speedtest.py"),
                                         "--csv", str(samples), "--verbose"],
                                        capture_output=True, text=True, timeout=30)
                print(client.stdout, end="")
                if client.returncode:
                    raise RuntimeError(client.stderr)
                receiver_log = receiver.communicate(timeout=5)[0]
                print(ready + receiver_log, end="")
                if receiver.returncode:
                    raise RuntimeError("El receptor falló")
                expected = (ROOT / "archivo_1kb.bin").read_bytes() * 10
                assert output.read_bytes() == expected, "Contenido recibido distinto"
                with samples.open(newline="") as stream:
                    rows = list(csv.DictReader(stream))
                assert len(rows) == 10
                assert [int(row["archivo"]) for row in rows] == list(range(1, 11))
                assert all(int(row["bytes"]) == 1000 and float(row["rtt_transmision_ms"]) > 0 for row in rows)
                assert client.stdout.count("[TX] SYN ") == 1
                assert client.stdout.count("[TX] PSH|ACK ") == 10
                assert client.stdout.count("[TX] FIN|ACK ") == 1
                assert "[RX] SYN|ACK " in client.stdout and "[RX] FIN|ACK " in client.stdout
                assert "Retransmisiones: 0;" in client.stdout
                print("Integración RAW correcta: una conexión, 10000 bytes, diez muestras y cierre FIN/ACK.")
                print(f"SHA-256 verificado: {hashlib.sha256(expected).hexdigest()}")
            finally:
                if receiver.poll() is None:
                    receiver.terminate()
                    receiver.wait(timeout=5)
    finally:
        subprocess.run(["iptables", "-D", *rule], check=True)


if __name__ == "__main__":
    main()
