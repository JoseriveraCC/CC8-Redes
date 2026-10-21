"""Pruebas sin privilegios: bytes en la red, estados TCP, medición y receptor."""

import hashlib
import io
from pathlib import Path
import socket
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import server
import speedtest as st

SOURCE = ("192.0.2.10", 40000)
DESTINATION = ("192.0.2.20", 3001)
PAYLOAD = bytes(range(250)) * 4


def tcp_checksum(packet):
    ihl = (packet[0] & 15) * 4
    tcp = packet[ihl:]
    pseudo = packet[12:20] + struct.pack("!BBH", 0, 6, len(tcp))
    return st.checksum(pseudo + tcp)


class Peer:
    """Peer determinista que recibe los bytes RAW, no métodos internos del cliente."""

    def __init__(self, *, lose_ack=False, lose_syn=False, separate_fin=False, omit_fin=False):
        self.incoming, self.sent, self.data = [], [], bytearray()
        self.seq = st.MASK
        self.expected = None
        self.lose_ack, self.lose_syn = lose_ack, lose_syn
        self.separate_fin, self.omit_fin = separate_fin, omit_fin
        self.duplicate_fin = False

    def settimeout(self, timeout):
        assert timeout > 0

    def reply(self, ack, flags=st.ACK, seq=None, options=b""):
        self.incoming.append(st.build_packet(DESTINATION, SOURCE,
                             self.seq if seq is None else seq, ack, flags, options=options))

    def sendto(self, packet, destination):
        assert destination == (DESTINATION[0], 0)
        assert st.checksum(packet[:20]) == 0
        assert tcp_checksum(packet) == 0
        segment = st.parse_packet(packet)
        assert segment.source == SOURCE and segment.destination == DESTINATION
        self.sent.append(segment)
        if segment.flags == st.SYN:
            self.expected = (segment.seq + 1) & st.MASK
            if self.lose_syn:
                self.lose_syn = False
                return
            self.reply(self.expected, st.SYN | st.ACK, seq=(self.seq - 1) & st.MASK,
                       options=struct.pack("!BBH", 2, 4, 512))
        elif segment.data:
            assert len(segment.data) <= 512
            assert segment.ack == self.seq
            if segment.seq == self.expected:
                self.data.extend(segment.data)
                self.expected = (self.expected + len(segment.data)) & st.MASK
            else:
                assert (segment.seq + len(segment.data)) & st.MASK == self.expected
            if self.lose_ack:
                self.lose_ack = False
                return
            # Ruido ajeno, ACK viejo y ACK con SEQ ajeno no deben completar la muestra.
            self.incoming.append(st.build_packet((DESTINATION[0], 9999), SOURCE,
                                                  self.seq, self.expected, st.ACK))
            self.reply(segment.seq)
            self.reply(self.expected, seq=3)
            self.reply(self.expected)
        elif segment.flags & st.FIN:
            assert segment.seq == self.expected
            if self.omit_fin:
                self.reply((segment.seq + 1) & st.MASK)
                return
            if self.separate_fin:
                self.reply((segment.seq + 1) & st.MASK)
            self.reply((segment.seq + 1) & st.MASK, st.FIN | st.ACK)
            self.duplicate_fin = True
        elif segment.flags == st.ACK and segment.ack == 0 and self.duplicate_fin:
            self.duplicate_fin = False
            self.reply((self.expected + 1) & st.MASK, st.FIN | st.ACK)

    def recvfrom(self, size):
        if not self.incoming:
            raise socket.timeout("Pérdida simulada")
        return self.incoming.pop(0), (DESTINATION[0], 0)


class PacketTests(unittest.TestCase):
    def test_checksum_known_vector(self):
        self.assertEqual(st.checksum(bytes.fromhex("0001f203f4f5f6f7")), 0x220D)

    def test_wire_format_and_odd_payload_checksum(self):
        packet = st.build_packet(SOURCE, DESTINATION, st.MASK + 2, 17, st.PSH | st.ACK,
                                 b"\x00\xff\x81", options=b"\x01\x01\x00\x00")
        self.assertEqual(len(packet), 47)
        self.assertEqual(st.checksum(packet[:20]), 0)
        self.assertEqual(tcp_checksum(packet), 0)
        self.assertEqual(struct.unpack_from("!H", packet, 2)[0], len(packet))
        segment = st.parse_packet(packet)
        self.assertEqual((segment.source, segment.destination), (SOURCE, DESTINATION))
        self.assertEqual((segment.seq, segment.ack, segment.flags), (1, 17, st.PSH | st.ACK))
        self.assertEqual(segment.data, b"\x00\xff\x81")

    def test_invalid_headers_and_truncation(self):
        packet = st.build_packet(SOURCE, DESTINATION, 10, 20, st.ACK)
        variants = [packet[:n] for n in range(len(packet))]
        for offset, value in [(0, 0x65), (0, 0x44), (9, 17), (6, 0x20), (32, 0xF0), (32, 0x40)]:
            bad = bytearray(packet)
            bad[offset] = value
            variants.append(bytes(bad))
        for bad in variants:
            with self.subTest(packet=bad.hex()):
                self.assertIsNone(st.parse_packet(bad))

    def test_mss_options(self):
        self.assertEqual(st.peer_mss(b""), 536)
        self.assertEqual(st.peer_mss(bytes.fromhex("01020405b4000000")), 1460)
        for options in [b"\x02", b"\x02\x00", b"\x02\x04\x00", b"\x02\x04\x00\x00", b"\x02\x02"]:
            with self.subTest(options=options), self.assertRaises(ConnectionError):
                st.peer_mss(options)

    def test_pdf_example(self):
        self.assertAlmostEqual(st.estimate_kbps(1000, 0.032, 0.032), 125.0)


class ConnectionTests(unittest.TestCase):
    def connection(self, peer, retries=1):
        connection = st.RawTCP(peer, SOURCE, DESTINATION, timeout=0.01, retries=retries)
        connection.seq = st.MASK - 3
        return connection

    def test_ten_uploads_single_connection_wraparound_and_fin_variants(self):
        for separate_fin in [False, True]:
            with self.subTest(separate_fin=separate_fin):
                peer = Peer(separate_fin=separate_fin)
                connection = self.connection(peer)
                self.assertGreater(connection.connect(), 0)
                samples = [connection.upload_file(PAYLOAD) for _ in range(10)]
                connection.disconnect()
                self.assertEqual(bytes(peer.data), PAYLOAD * 10)
                self.assertEqual(len(samples), 10)
                self.assertTrue(all(sample > 0 for sample in samples))
                self.assertEqual(sum(segment.flags == st.SYN for segment in peer.sent), 1)
                self.assertEqual(sum(bool(segment.data) for segment in peer.sent), 20)
                self.assertEqual(sum(bool(segment.flags & st.FIN) for segment in peer.sent), 1)
                self.assertEqual(connection.ack, 0)  # FIN del servidor consume un SEQ.
                self.assertEqual(peer.sent[-1].flags, st.ACK)
                self.assertEqual(connection.seq, (st.MASK - 3 + 1 + 10000 + 1) & st.MASK)

    def test_retransmission_does_not_duplicate_data(self):
        peer = Peer(lose_ack=True, lose_syn=True)
        connection = self.connection(peer)
        connection.connect()
        connection.upload_file(PAYLOAD)
        connection.disconnect()
        self.assertEqual(bytes(peer.data), PAYLOAD)
        self.assertEqual(connection.retransmissions, 2)

    def test_missing_fin_is_failure(self):
        connection = self.connection(Peer(omit_fin=True), retries=0)
        connection.connect()
        with self.assertRaisesRegex(TimeoutError, "Cierre TCP incompleto"):
            connection.disconnect()

    def test_reset_and_timeout_are_failures(self):
        peer = Peer()
        peer.incoming.append(st.build_packet(DESTINATION, SOURCE, 0, 0, st.RST | st.ACK))
        with self.assertRaisesRegex(ConnectionError, "RST"):
            self.connection(peer).connect()
        peer = Peer(lose_syn=True)
        with self.assertRaisesRegex(TimeoutError, "SYN"):
            self.connection(peer, retries=0).connect()

    def test_zero_window_is_explicit_failure(self):
        connection = self.connection(Peer())
        connection.connect()
        connection.window = 0
        with self.assertRaisesRegex(ConnectionError, "Ventana"):
            connection.upload_file(PAYLOAD)


class FragmentedStream:
    def __init__(self, data):
        self.input = io.BytesIO(data)

    def recv(self, size):
        return self.input.read(min(size, 137))


class ReceiverTests(unittest.TestCase):
    def test_stream_fragmentation_and_integrity(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "received.bin"
            data = PAYLOAD * 10
            digest = server.receive_upload(FragmentedStream(data), output)
            self.assertEqual(output.read_bytes(), data)
            self.assertEqual(digest, hashlib.sha256(data).hexdigest())

    def test_incomplete_extra_and_changed_files_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "received.bin"
            for data in [PAYLOAD * 9, PAYLOAD * 10 + b"x", PAYLOAD * 9 + b"z" * 1000]:
                with self.subTest(length=len(data)), self.assertRaises(ValueError):
                    server.receive_upload(FragmentedStream(data), output)
                self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
