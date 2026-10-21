# SPDX-License-Identifier: MIT
"""Check the acquisition trust boundary without network access or inference."""
import importlib.util
import hashlib
import io
import json
from pathlib import Path
import struct
import tempfile
from types import SimpleNamespace
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


if __name__ == "__main__":
    unittest.main()
