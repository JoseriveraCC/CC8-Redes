"""Pruebas locales del ayudante; no usan radio ni simulan éxito criptográfico."""

import contextlib
import io
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import lab10


class Lab10Tests(unittest.TestCase):
    def quiet(self, args):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return lab10.main(args)

    def test_rejects_invalid_radio_parameters(self):
        base = ["capturar", "--interfaz", "wlan0mon", "--bssid",
                "02:11:22:33:44:55", "--canal", "6", "--simular"]
        for index, value in ((2, "wlan0;id"), (4, "FF:FF:FF:FF:FF:FF"),
                             (4, "00:00:00:00:00:00"), (4, "incorrecto"),
                             (6, "0"), (6, "197"), (6, "seis")):
            with self.subTest(value=value), self.assertRaises(SystemExit) as error:
                args = base.copy()
                args[index] = value
                self.quiet(args)
            self.assertEqual(error.exception.code, 2)

    def test_simulation_does_not_transmit_or_create_outputs(self):
        with tempfile.TemporaryDirectory() as folder, patch("lab10.subprocess.call") as run:
            output = Path(folder) / "nuevo" / "captura"
            result = self.quiet(["capturar", "--interfaz", "wlan0mon", "--bssid",
                                 "02:11:22:33:44:55", "--canal", "6",
                                 "--salida", str(output), "--simular"])
            self.assertEqual(result, 0)
            run.assert_not_called()
            self.assertFalse(output.parent.exists())

    def test_monitor_builds_start_and_stop_without_transmitting(self):
        with patch("lab10.shutil.which", return_value="/usr/bin/airmon-ng"), \
                patch("lab10.subprocess.call", return_value=0) as run:
            self.quiet(["monitor", "--interfaz", "wlan0", "--canal", "6"])
            self.assertEqual(run.call_args.args[0], ["airmon-ng", "start", "wlan0", "6"])
            self.quiet(["monitor", "--interfaz", "wlan0mon", "--detener"])
            self.assertEqual(run.call_args.args[0], ["airmon-ng", "stop", "wlan0mon"])

    def test_scan_simulation_is_passive_and_creates_no_outputs(self):
        with tempfile.TemporaryDirectory() as folder, patch("lab10.subprocess.call") as run:
            output = Path(folder) / "nuevo" / "scan"
            result = self.quiet(["escanear", "--interfaz", "wlan0mon", "--canal", "6",
                                 "--salida", str(output), "--simular"])
            self.assertEqual(result, 0)
            run.assert_not_called()
            self.assertFalse(output.parent.exists())

    def test_inject_builds_arpreplay_and_fakeauth_against_given_bssid(self):
        with patch("lab10.shutil.which", return_value="/usr/bin/aireplay-ng"), \
                patch("lab10.subprocess.call", return_value=0) as run:
            self.quiet(["inyectar", "--interfaz", "wlan0mon", "--bssid",
                        "02:11:22:33:44:55", "--mac", "AA:BB:CC:DD:EE:FF"])
            self.assertEqual(run.call_args.args[0], ["aireplay-ng", "--arpreplay", "-b",
                             "02:11:22:33:44:55", "-h", "AA:BB:CC:DD:EE:FF", "wlan0mon"])
            self.quiet(["inyectar", "--interfaz", "wlan0mon", "--bssid",
                        "02:11:22:33:44:55", "--modo", "fakeauth"])
            self.assertEqual(run.call_args.args[0], ["aireplay-ng", "--fakeauth", "0", "-a",
                             "02:11:22:33:44:55", "wlan0mon"])
            for modo, flag in (("chopchop", "--chopchop"), ("fragment", "--fragment")):
                self.quiet(["inyectar", "--interfaz", "wlan0mon", "--bssid",
                            "02:11:22:33:44:55", "--modo", modo])
                self.assertEqual(run.call_args.args[0], ["aireplay-ng", flag, "-b",
                                 "02:11:22:33:44:55", "wlan0mon"])

    def test_deauth_builds_targeted_and_broadcast_variants(self):
        with patch("lab10.shutil.which", return_value="/usr/bin/aireplay-ng"), \
                patch("lab10.subprocess.call", return_value=0) as run:
            self.quiet(["deauth", "--interfaz", "wlan0mon", "--bssid",
                        "02:11:22:33:44:55", "--cliente", "AA:BB:CC:DD:EE:FF",
                        "--cantidad", "25"])
            self.assertEqual(run.call_args.args[0], ["aireplay-ng", "--deauth", "25", "-a",
                             "02:11:22:33:44:55", "-c", "AA:BB:CC:DD:EE:FF", "wlan0mon"])
            self.quiet(["deauth", "--interfaz", "wlan0mon", "--bssid", "02:11:22:33:44:55"])
            self.assertEqual(run.call_args.args[0], ["aireplay-ng", "--deauth", "10", "-a",
                             "02:11:22:33:44:55", "wlan0mon"])

    def test_deauth_rejects_out_of_range_count(self):
        for value in ("-1", "65536", "muchas"):
            with self.subTest(value=value), self.assertRaises(SystemExit) as error:
                self.quiet(["deauth", "--interfaz", "wlan0mon", "--bssid",
                            "02:11:22:33:44:55", "--cantidad", value, "--simular"])
            self.assertEqual(error.exception.code, 2)

    def test_block_simulation_reports_plan_and_touches_no_socket(self):
        with patch("lab10.socket.socket") as sock:
            result = self.quiet(["bloquear", "--interfaz", "wlan0", "--objetivo",
                                 "192.168.1.50", "--gateway", "192.168.1.1", "--simular"])
            self.assertEqual(result, 0)
            sock.assert_not_called()

    def test_block_rejects_invalid_addresses(self):
        base = ["bloquear", "--interfaz", "wlan0", "--objetivo", "192.168.1.50",
                "--gateway", "192.168.1.1", "--intervalo", "2", "--simular"]
        for index, value in ((4, "999.1.1.1"), (4, "1.2.3"), (6, "no.ip"), (8, "0")):
            with self.subTest(value=value), self.assertRaises(SystemExit) as error:
                args = base.copy()
                args[index] = value
                self.quiet(args)
            self.assertEqual(error.exception.code, 2)

    def test_recovery_requires_capture_and_preserves_existing_key(self):
        with tempfile.TemporaryDirectory() as folder:
            capture = Path(folder) / "ejemplo.cap"
            key = Path(folder) / "clave.txt"
            args = ["recuperar", str(capture), "--bssid", "02:11:22:33:44:55",
                    "--clave", str(key), "--simular"]
            with self.assertRaises(SystemExit):
                self.quiet(args)
            capture.touch()
            key.write_text("conservar")
            with self.assertRaises(SystemExit):
                self.quiet(args)
            self.assertEqual(key.read_text(), "conservar")

    def test_recovery_passes_paths_literally_and_returns_tool_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            capture = Path(folder) / "captura con espacios.cap"
            capture.touch()
            key = Path(folder) / "clave con espacios.txt"
            with patch("lab10.shutil.which", return_value="/usr/bin/aircrack-ng"), \
                    patch("lab10.subprocess.call", return_value=7) as run:
                result = self.quiet(["recuperar", str(capture), "--bssid",
                                     "02:11:22:33:44:55", "--clave", str(key)])
            self.assertEqual(result, 7)
            self.assertEqual(run.call_args.args[0], ["aircrack-ng", "-a", "1", "-b",
                             "02:11:22:33:44:55", "-l", str(key), str(capture)])

    @unittest.skipUnless(shutil.which("aircrack-ng"), "requiere instalar aircrack-ng")
    def test_official_sample_recovers_known_key_without_radio(self):
        root = Path(__file__).resolve().parent
        with tempfile.TemporaryDirectory() as folder:
            key = Path(folder) / "clave.txt"
            result = subprocess.run(
                [sys.executable, str(root / "lab10.py"), "recuperar",
                 str(root / "muestras" / "ptw.cap"), "--bssid", "00:12:BF:12:32:29",
                 "--clave", str(key)], capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("KEY FOUND!", result.stdout)
            self.assertEqual(key.read_text().strip().replace(":", "").upper(), "1F1F1F1F1F")


if __name__ == "__main__":
    unittest.main()
