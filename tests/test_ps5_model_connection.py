# SPDX-License-Identifier: MIT
"""Protocol fault injection only; every socket and HTTP request is simulated."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import urllib.error
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import ps5_model_connection as connection


class Response:
    def __init__(self, data): self.data = data
    def read(self, size): return self.data[:size]
    def __enter__(self): return self
    def __exit__(self, *args): pass


class Socket:
    def __init__(self, chunks): self.chunks = iter(chunks); self.sent = []
    def settimeout(self, value): pass
    def recv(self, size): return next(self.chunks, b"")
    def sendall(self, data): self.sent.append(data)
    def __enter__(self): return self
    def __exit__(self, *args): pass


class ModelConnection(unittest.TestCase):
    def setUp(self):
        self.client = connection.PS5ModelConnection("10.255.254.253")
        self.service = dict(name="synthetic_service", pid=123)
        self.marker = b"QWEN_CAPACITY_DONE_" + b"a" * 24

    def capacity(self, chunks):
        base = Path(__file__).resolve().parents[1] / ".test-tmp"; base.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=base); self.addCleanup(self.temp.cleanup)
        out = Path(self.temp.name) / "capture"
        sock = Socket(chunks)
        with patch.object(connection.socket, "create_connection", return_value=sock), \
                patch.object(connection.secrets, "token_hex", return_value="a" * 24), \
                patch.object(connection.time, "monotonic", return_value=0), \
                patch.object(connection.time, "time_ns", return_value=1000000000):
            value = self.client.capacity(out)
        self.assertEqual(sock.sent, [b"df\necho " + self.marker + b"\n"])
        return value, out

    def process_response(self, rows):
        self.client.opener = type("Opener", (), {"open": lambda *args, **kwargs:
            Response(json.dumps(dict(processes=rows)).encode())})()

    def test_private_LAN_address_only(self):
        for value in [123, "127.0.0.1", "0.0.0.0", "198.51.100.1", "example.invalid", "::1", "224.0.0.1"]:
            with self.assertRaises(ValueError): connection.PS5ModelConnection(value)

    def test_exact_idle_services(self):
        self.process_response([self.service])
        self.client.idle_guard([self.service])

    def test_active_native_owner_rejects(self):
        self.process_response([self.service, dict(name="eboot.bin", pid=124)])
        with self.assertRaisesRegex(ValueError, "native title is active"): self.client.idle_guard([self.service])

    def test_changed_or_duplicate_service_rejects(self):
        for rows in [[], [dict(self.service, pid=124)], [self.service, self.service]]:
            self.process_response(rows)
            with self.assertRaises(ValueError): self.client.idle_guard([self.service])

    def test_only_owned_model_metadata_paths_are_read(self):
        for path in ["/data/other", connection.REMOTE_ROOT + "/../secret", connection.REMOTE_ROOT + "/x?other"]:
            with self.assertRaises(ValueError): self.client.model_get(path, 10)

    def test_network_or_permission_error_is_not_absence(self):
        def fail(*args, **kwargs): raise urllib.error.HTTPError("synthetic", 403, "denied", {}, None)
        self.client.opener = type("Opener", (), {"open": fail})()
        with self.assertRaises(urllib.error.HTTPError): self.client.absent(connection.REMOTE_ROOT + "/new.gguf")

    def test_positive_404_is_absence(self):
        def missing(*args, **kwargs): raise urllib.error.HTTPError("synthetic", 404, "missing", {}, None)
        self.client.opener = type("Opener", (), {"open": missing})()
        self.client.absent(connection.REMOTE_ROOT + "/new.gguf")

    def test_capacity_requires_separate_completed_marker(self):
        data = b"/user/data 625.1G 69.3G 536.5G 11% /data\n" + self.marker + b"\n$ "
        value, out = self.capacity([b"$ ", data])
        self.assertEqual(value["free_bytes_lower_bound"], 536400000000)
        self.assertTrue(value["capture_completion_proven"])
        self.assertFalse(value["freshness_proven"])
        self.assertEqual(value["capture_bytes"], len((out / "capture.private.log").read_bytes()))

    def test_echoed_command_alone_does_not_prove_completion(self):
        with self.assertRaises(TimeoutError): self.capacity([b"$ ", b"echo " + self.marker + b"\n$ "])

    def test_prompt_prefixed_echo_output_completes(self):
        data = b"/user/data 625.1G 69.3G 536.5G 11% /data\r\n/$ " + self.marker + b" \r\n/$ "
        value, _ = self.capacity([b"/$ ", data])
        self.assertTrue(value["capture_completion_proven"])

    def test_prompt_prefixed_echo_command_is_not_output(self):
        with self.assertRaises(TimeoutError): self.capacity([b"/$ ", b"/$ echo " + self.marker + b"\r\n/$ "])

    def test_unadmitted_prompt_rejects(self):
        with self.assertRaises(ValueError): self.capacity([b"unknown prompt", b""])

    def test_capacity_capture_bound_rejects(self):
        with self.assertRaisesRegex(ValueError, "capture exceeded"):
            self.capacity([b"$ "] + [b"x" * 65536] * 17)


if __name__ == "__main__": unittest.main()
