# SPDX-License-Identifier: MIT
"""Fault injection for large-file publication; no network or model execution."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import model_transport as transfer


class FTP:
    def __init__(self):
        self.files = {}; self.stores = 0; self.renames = 0
        self.mode = "-rw-r--r--"; self.response = "226 Transfer complete"
        self.after_store = lambda: None; self.after_rename = lambda: None

    def storbinary(self, command, reader, blocksize):
        self.stores += 1; path = command.removeprefix("STOR "); data = bytearray()
        self.files[path] = data
        while True:
            chunk = reader.read(blocksize)
            if not chunk: break
            data.extend(chunk)
        self.after_store()
        return self.response

    def voidcmd(self, command):
        assert command == "TYPE I"

    def size(self, path): return len(self.files[path])
    def retrlines(self, command, callback): callback(self.mode + " 1 0 0 1 Jan 1 00:00 model")

    def rename(self, source, destination):
        self.renames += 1
        if destination in self.files: raise AssertionError("Existing file overwrite")
        self.files[destination] = self.files.pop(source)
        self.after_rename()
        return "250 Rename complete"


class ModelTransport(unittest.TestCase):
    def setUp(self):
        base = Path(__file__).resolve().parents[1] / ".test-tmp"
        base.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=base)
        self.root = Path(self.temp.name); self.data = b"synthetic-transport-data" * 100000
        self.source = self.root / "model.gguf"; self.source.write_bytes(self.data)
        self.row = dict(path=self.source.name, bytes=len(self.data), sha256=hashlib.sha256(self.data).hexdigest())
        self.ftp = FTP(); self.guard_calls = 0

    def tearDown(self): self.temp.cleanup()

    def guard(self): self.guard_calls += 1

    def absent(self, path):
        if path in self.ftp.files: raise ValueError("Already exists")

    def upload(self, **options):
        return transfer.upload_file_once(self.ftp, self.root, self.row, self.root / "records", "a" * 32,
            guard=self.guard, absent=self.absent, **options)

    def failed_record(self):
        return json.loads((self.root / "records/model.gguf.failure.private.json").read_text())

    def test_success_requires_later_native_SHA(self):
        progress = []
        result = self.upload(progress=progress.append)
        self.assertEqual(self.ftp.files[result["destination"]], self.data)
        self.assertEqual(progress[-1], len(self.data))
        self.assertTrue(result["source_stream_SHA_verified"])
        self.assertFalse(result["native_SHA_verified"])
        self.assertEqual(result["state"], "awaiting_native_SHA_admission")
        self.assertEqual((self.ftp.stores, self.ftp.renames), (1, 1))

    def test_wrong_source_digest_retains_partial(self):
        self.row["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "source bytes differ"): self.upload()
        self.assertEqual(self.ftp.renames, 0)
        self.assertEqual(self.failed_record()["remote_state"], "retained_for_review")

    def test_ambiguous_transfer_is_never_repeated(self):
        def ambiguous(): raise TimeoutError("Reply lost after complete data")
        self.ftp.after_store = ambiguous
        with self.assertRaises(TimeoutError): self.upload()
        with self.assertRaisesRegex(ValueError, "already has an attempt"): self.upload()
        self.assertEqual(self.ftp.stores, 1)
        self.assertEqual(self.failed_record()["automatic_retries"], 0)

    def test_post_transfer_source_mutation_prevents_publication(self):
        self.ftp.after_store = lambda: self.source.write_bytes(self.data + b"changed")
        with self.assertRaisesRegex(ValueError, "source changed"): self.upload()
        self.assertEqual(self.ftp.renames, 0)

    def test_missing_positive_completion_prevents_rename(self):
        self.ftp.response = "150 Opening transfer"
        with self.assertRaisesRegex(ValueError, "Positive FTP"): self.upload()
        self.assertEqual(self.ftp.renames, 0)

    def test_native_unreadable_file_prevents_rename(self):
        self.ftp.mode = "-rw-------"
        with self.assertRaisesRegex(ValueError, "must be able to read"): self.upload()
        self.assertEqual(self.ftp.renames, 0)

    def test_ambiguous_rename_is_not_repeated_or_deleted(self):
        def ambiguous(): raise TimeoutError("Reply lost after rename")
        self.ftp.after_rename = ambiguous
        with self.assertRaises(TimeoutError): self.upload()
        with self.assertRaisesRegex(ValueError, "already has an attempt"): self.upload()
        self.assertEqual((self.ftp.stores, self.ftp.renames), (1, 1))
        self.assertEqual(self.failed_record()["delete_calls"], 0)

    def test_deadline_before_payload_retains_attempt(self):
        with patch.object(transfer.time, "monotonic", side_effect=[0, 61]):
            with self.assertRaises(TimeoutError): self.upload(timeout_seconds=60)
        self.assertEqual(self.ftp.renames, 0)

    def test_existing_destination_is_preserved(self):
        remote = transfer.REMOTE_ROOT + "/model.gguf"
        self.ftp.files[remote] = b"preserved"
        with self.assertRaisesRegex(ValueError, "Already exists"): self.upload()
        self.assertEqual(self.ftp.files[remote], b"preserved")
        self.assertEqual(self.ftp.stores, 0)

    def test_second_writer_is_rejected(self):
        lock = self.root / "writer.lock"
        with transfer.writer_lease(lock):
            with self.assertRaises(OSError):
                with transfer.writer_lease(lock): self.fail("Concurrent writer admitted")
        with transfer.writer_lease(lock): pass

    def test_invalid_relative_names_and_sizes(self):
        for name in ["../model.gguf", "/model.gguf", "x\\model.gguf", "model.gguf\r\nSTOR x"]:
            with self.assertRaises(ValueError): transfer.validate_file(dict(self.row, path=name))
        for size in [True, 0, -1, 513 << 30, 2.0]:
            with self.assertRaises(ValueError): transfer.validate_file(dict(self.row, bytes=size))
        self.assertEqual(self.ftp.stores, 0)


if __name__ == "__main__": unittest.main()
