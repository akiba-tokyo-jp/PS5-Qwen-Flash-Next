# SPDX-License-Identifier: MIT
"""Check the acquisition trust boundary without network access or inference."""
import importlib.util
import hashlib
import io
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import threading
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("qwen_acquire", Path(__file__).resolve().parents[1] / "tools/qwen_flash_next.py")
acquire = importlib.util.module_from_spec(spec)
spec.loader.exec_module(acquire)


class Response(io.BytesIO):
    def __init__(self, data, status, content_range=""):
        super().__init__(data)
        self.status = status
        self.headers = {"Content-Range": content_range}


class CheckpointIO(unittest.TestCase):
    def test_paths_cannot_escape_the_model_directory(self):
        for name in ("../weight", "/weight", "a/b", "a\\b", "C:weight", "..", ""):
            with self.subTest(name=name), self.assertRaises(ValueError):
                acquire.safe_name(name)

    def test_range_rejects_a_whole_file_response_before_reading(self):
        response = Response(b"unexpected entire model", 200)
        with patch.object(acquire, "request", return_value=response), self.assertRaises(ValueError):
            acquire.fetch_range("https://example.invalid/model", 0, 8)
        self.assertTrue(response.closed)

    def test_range_rejects_wrong_offsets_and_truncated_data(self):
        for response in (Response(b"12345678", 206, "bytes 1-8/100"), Response(b"12", 206, "bytes 0-7/100")):
            with self.subTest(headers=response.headers), patch.object(acquire, "request", return_value=response), self.assertRaises(ValueError):
                acquire.fetch_range("https://example.invalid/model", 0, 8)

    def test_exact_range(self):
        with patch.object(acquire, "request", return_value=Response(b"12345678", 206, "bytes 8-15/100")):
            self.assertEqual(acquire.fetch_range("https://example.invalid/model", 8, 8), b"12345678")

    def test_pinned_redirect_is_reused_with_the_new_range_and_expiry_refreshes_from_origin(self):
        origin = acquire.BASE + "fixture.safetensors"
        response = SimpleNamespace(geturl=lambda: "https://cdn.example.invalid/signed", close=lambda: None)
        with patch.object(acquire, "_redirect", threading.local()), \
             patch.object(acquire.urllib.request, "urlopen", return_value=response) as opened:
            acquire.request(origin, 0, 7)
            self.assertEqual(opened.call_args.args[0].full_url, origin)
            acquire.request(origin, 8, 15)
            self.assertEqual(opened.call_args.args[0].full_url, "https://cdn.example.invalid/signed")
            self.assertEqual(opened.call_args.args[0].get_header("Range"), "bytes=8-15")
            expired = acquire.urllib.error.HTTPError("https://cdn.example.invalid/signed", 403, "Expired", {}, None)
            opened.side_effect = [expired, response]
            acquire.request(origin, 16, 23)
            self.assertEqual(opened.call_args.args[0].full_url, origin)
            self.assertEqual(opened.call_args.args[0].get_header("Range"), "bytes=16-23")
            opened.side_effect = None
            acquire.request(acquire.BASE + "other.safetensors", 0, 7)
            self.assertEqual(opened.call_args.args[0].full_url, acquire.BASE + "other.safetensors")

    def test_ranges_remain_bounded_and_full_responses_are_rejected(self):
        with patch.object(acquire, "request") as request:
            for length in (0, acquire.MAX_RANGE + 1):
                with self.assertRaises(ValueError):
                    acquire.fetch_range(acquire.BASE + "fixture", 0, length)
            request.assert_not_called()

    def test_optional_session_transport_keeps_exact_range_and_closes_each_response(self):
        class Raw(io.BytesIO):
            def read(self, maximum, decode_content=False):
                return super().read(maximum)
        raw = Raw(b"12345678")
        response = SimpleNamespace(status_code=206, headers={"Content-Range": "bytes 8-15/100"},
                                   url="https://cdn.example.invalid/signed", raw=raw, close=raw.close)
        class Session:
            def get(self, url, **options):
                self.options = options
                return response
        session = Session()
        state = threading.local(); state.http_session = session
        with patch.object(acquire, "_redirect", state):
            self.assertEqual(acquire.fetch_range(acquire.BASE + "fixture", 8, 8), b"12345678")
        self.assertEqual(session.options["headers"]["Range"], "bytes=8-15")
        self.assertEqual(session.options["timeout"], (10, 30))
        self.assertTrue(raw.closed)

    def test_session_transport_errors_do_not_expose_signed_urls(self):
        class Session:
            def get(self, *args, **kwargs):
                raise RuntimeError("https://cdn.example.invalid/?secret=must-not-log")
        state = threading.local(); state.http_session = Session()
        with patch.object(acquire, "_redirect", state), self.assertRaises(OSError) as failure:
            acquire.request(acquire.BASE + "fixture", 0, 7)
        self.assertNotIn("secret", str(failure.exception))
        self.assertTrue(failure.exception.__suppress_context__)

    def header(self, tensors, data_bytes):
        raw = json.dumps(tensors).encode()
        with patch.object(acquire, "fetch_range", side_effect=(struct.pack("<Q", len(raw)), raw)):
            return acquire.tensor_header("model.safetensors", 8 + len(raw) + data_bytes)

    def test_original_bf16_and_integer_hash_constants(self):
        tensors = {"expert": {"dtype": "BF16", "shape": [2, 3, 4], "data_offsets": [0, 48]},
                   "hash": {"dtype": "I64", "shape": [1], "data_offsets": [48, 56]}}
        result, offset, raw = self.header(tensors, 56)
        self.assertEqual(result, tensors)
        self.assertEqual(offset, 8 + len(raw))

    def test_corrupt_shape_or_offsets_are_rejected(self):
        for tensors in (
            {"x": {"dtype": "BF16", "shape": [4], "data_offsets": [0, 7]}},
            {"x": {"dtype": "BF16", "shape": [-1], "data_offsets": [0, 8]}},
            {"x": {"dtype": "I8", "shape": [8], "data_offsets": [0, 8]}},
            {"x": {"dtype": "BF16", "shape": [4], "data_offsets": [0, 8]},
             "y": {"dtype": "BF16", "shape": [2], "data_offsets": [4, 8]}},
        ):
            with self.subTest(tensors=tensors), self.assertRaises(ValueError):
                self.header(tensors, 8)

    def test_unindexed_bytes_are_rejected(self):
        with self.assertRaises(ValueError):
            self.header({"x": {"dtype": "BF16", "shape": [4], "data_offsets": [0, 8]}}, 10)

    def download_fixture(self, root, payload, digest):
        (root / "model").mkdir()
        acquire.json_write(root / "metadata/checkpoint.json", {
            "revision": acquire.REVISION, "quantization": False,
            "files": [{"name": "model.safetensors", "bytes": len(payload), "sha256": digest}]})

    def test_resumed_download_publishes_only_after_original_digest_matches(self):
        payload = b"original-bf16-weights"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.download_fixture(root, payload, hashlib.sha256(payload).hexdigest())
            partial = root / "model/model.safetensors.partial"
            partial.write_bytes(payload[:5])
            with patch.object(acquire.shutil, "disk_usage", return_value=SimpleNamespace(free=1 << 40)), \
                 patch.object(acquire, "fetch_range", side_effect=lambda url, start, length: payload[start:start + length]) as fetch:
                acquire.download(root, 1)
            self.assertEqual(fetch.call_args.args[1], 5)
            self.assertEqual((root / "model/model.safetensors").read_bytes(), payload)
            self.assertFalse(partial.exists())
            self.assertTrue(json.loads((root / "download-progress.json").read_text())["complete"])

    def test_digest_failure_retains_partial_and_does_not_publish_a_shard(self):
        payload = b"corrupt"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.download_fixture(root, payload, "0" * 64)
            with patch.object(acquire.shutil, "disk_usage", return_value=SimpleNamespace(free=1 << 40)), \
                 patch.object(acquire, "fetch_range", return_value=payload), self.assertRaisesRegex(ValueError, "SHA256"):
                acquire.download(root, 1)
            self.assertFalse((root / "model/model.safetensors").exists())
            self.assertEqual((root / "model/model.safetensors.partial").read_bytes(), payload)
            status = json.loads((root / "download-progress.json").read_text())
            self.assertEqual(status["phase"], "failed")
            self.assertFalse(status["complete"])

    def test_writer_lease_blocks_another_process_and_releases_after_exit(self):
        with tempfile.TemporaryDirectory() as directory:
            lease = Path(directory) / "writer.lock"
            code = ("import sys; sys.path.insert(0,sys.argv[1]); from qwen_flash_next import writer_lease; "
                    "from pathlib import Path; exec('with writer_lease(Path(sys.argv[2])): pass')")
            command = [sys.executable, "-B", "-c", code, str(Path(acquire.__file__).parent), str(lease)]
            with acquire.writer_lease(lease):
                rejected = subprocess.run(command, capture_output=True, timeout=15)
                self.assertNotEqual(rejected.returncode, 0)
                self.assertIn(b"Another host writer", rejected.stderr)
            accepted = subprocess.run(command, capture_output=True, timeout=15)
            self.assertEqual(accepted.returncode, 0, accepted.stderr)

    def test_deadline_retains_partial_and_records_failure(self):
        payload = b"original-bf16-weights"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.download_fixture(root, payload, hashlib.sha256(payload).hexdigest())
            with patch.object(acquire.shutil, "disk_usage", return_value=SimpleNamespace(free=1 << 40)), \
                 patch.object(acquire.time, "monotonic", side_effect=lambda: self.clock()), \
                 patch.object(acquire, "fetch_range") as fetch, self.assertRaises(TimeoutError):
                self.tick = 0
                acquire.download(root, 1, 1)
            fetch.assert_not_called()
            status = json.loads((root / "download-progress.json").read_text())
            self.assertEqual((status["phase"], status["error_type"]), ("failed", "TimeoutError"))
            self.assertFalse((root / "model/model.safetensors").exists())

    def test_deferred_retained_file_verification_does_not_claim_original_digest_success(self):
        payload = b"original-bf16-weights"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.download_fixture(root, payload, hashlib.sha256(payload).hexdigest())
            (root / "model/model.safetensors").write_bytes(b"X" * len(payload))
            with patch.object(acquire.shutil, "disk_usage", return_value=SimpleNamespace(free=1 << 40)), \
                 patch.object(acquire, "fetch_range") as fetch:
                acquire.download(root, 1, verify_existing=False)
            fetch.assert_not_called()
            status = json.loads((root / "download-progress.json").read_text())
            self.assertTrue(status["complete"])
            self.assertFalse(status["original_shards_verified"])
            self.assertEqual((status["verified_shards"], status["reused_unverified_shards"]), (0, 1))
            with patch.object(acquire.shutil, "disk_usage", return_value=SimpleNamespace(free=1 << 40)), \
                 self.assertRaisesRegex(ValueError, "SHA256"):
                acquire.download(root, 1)

    def clock(self):
        self.tick += 1
        return self.tick

    @unittest.skipUnless(acquire.os.name == "nt", "Windows sharing behavior")
    def test_status_replace_retries_only_bounded_windows_sharing_errors(self):
        conflict = PermissionError("Scanner still holds the status file")
        conflict.winerror = 32
        with patch.object(acquire.os, "replace", side_effect=[conflict, None]) as replace, \
             patch.object(acquire.time, "sleep") as sleep:
            acquire.atomic_replace(Path("status.next"), Path("status.json"))
            self.assertEqual(replace.call_count, 2)
            self.assertEqual(sleep.call_count, 1)
        with patch.object(acquire.os, "replace", side_effect=conflict) as replace, \
             patch.object(acquire.time, "sleep") as sleep, self.assertRaises(PermissionError):
            acquire.atomic_replace(Path("status.next"), Path("status.json"))
        self.assertEqual((replace.call_count, sleep.call_count), (5, 4))
        with patch.object(acquire.os, "replace", side_effect=OSError("Disk failure")) as replace, \
             self.assertRaises(OSError):
            acquire.atomic_replace(Path("status.next"), Path("status.json"))
        self.assertEqual(replace.call_count, 1)


if __name__ == "__main__":
    unittest.main()
