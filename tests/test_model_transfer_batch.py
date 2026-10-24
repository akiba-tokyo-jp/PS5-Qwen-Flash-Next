# SPDX-License-Identifier: MIT
"""Synthetic sequencing/failure injection. The real complete-model gate is
deliberately stubbed only in sequencing tests; no real receipt or network is used.
"""
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import model_transfer_batch as batch
from model_transport import REMOTE_ROOT, source_identity


class FakeConnection:
    def __init__(self):
        self.files = {}; self.stores = 0; self.renames = 0; self.fail_store = None
        self.free = 10**12; self.corrupt_receipt_readback = False
        self.rename_response = "250 Rename complete"

    @contextmanager
    def ftp(self): yield self

    def absent(self, path):
        if path in self.files: raise ValueError("Existing destination")

    def storbinary(self, command, reader, blocksize):
        self.stores += 1; path = command.removeprefix("STOR "); data = bytearray(); self.files[path] = data
        while True:
            chunk = reader.read(blocksize)
            if not chunk: break
            data.extend(chunk)
        if self.stores == self.fail_store: raise TimeoutError("Ambiguous positive-length transfer")
        return "226 Transfer complete"

    def rename(self, source, destination):
        self.absent(destination); self.renames += 1
        self.files[destination] = self.files.pop(source)
        return self.rename_response

    def voidcmd(self, command): assert command == "TYPE I"
    def size(self, path): return len(self.files[path])

    def retrlines(self, command, callback):
        assert command == "LIST " + REMOTE_ROOT
        for path in self.files: callback("-rw-r--r-- 1 0 0 1 Jan 1 00:00 " + path.rsplit("/", 1)[1])

    def directory_metadata(self, ftp):
        return [dict(name=path.rsplit("/", 1)[1], mode="-rw-r--r--") for path in self.files]

    def model_get(self, path, limit):
        if self.corrupt_receipt_readback: return b"incorrect synthetic metadata"
        return bytes(self.files[path])

    def capacity(self, out):
        out.mkdir(exist_ok=False)
        return dict(capture_completion_proven=True, host_after_epoch_ms=time.time_ns() // 1000000,
                    free_bytes_lower_bound=self.free)


class BatchSequence(unittest.TestCase):
    def setUp(self):
        base = Path(__file__).resolve().parents[1] / ".test-tmp"; base.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=base); self.root = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup); self.connection = FakeConnection(); self.guard_calls = 0
        rows = []
        for index in range(2):
            data = ("synthetic-file-" + str(index)).encode(); path = self.root / (str(index) + ".gguf"); path.write_bytes(data)
            rows.append(dict(original=dict(path=path.name, bytes=len(data), sha256=hashlib.sha256(data).hexdigest()),
                source=str(path), source_identity=source_identity(path.stat())))
        self.total = sum(row["original"]["bytes"] for row in rows)
        self.plan = dict(schema="ps5-qwen-model-transfer-plan-v1", nonce="a" * 32,
            remote_root=REMOTE_ROOT, maximum_upload_connections=1, console_access=False,
            remote_payload_SHA_verified=False, input_hashes_stable=True,
            source_directory=str(self.root), files=rows, total_bytes=self.total, file_timeout_seconds=21600)
        self.receipt = b'{"synthetic_metadata_only":true}'

    def guard(self): self.guard_calls += 1

    def run_sequence(self, **options):
        with patch.object(batch, "validate_plan", return_value=self.total):
            return batch.run_batch(self.plan, self.receipt, self.connection,
                self.root / "run", self.root / "writer.lock", guard=self.guard, **options)

    def test_all_files_precede_receipt_and_require_native_SHA_later(self):
        result = self.run_sequence()
        self.assertEqual(self.connection.stores, 3)
        self.assertEqual(self.connection.renames, 3)
        self.assertEqual(self.connection.files[REMOTE_ROOT + "/model-receipt.json"], self.receipt)
        self.assertEqual(result["positively_completed_files"], 2)
        self.assertFalse(result["native_payload_SHA_verified"])
        self.assertFalse(result["model_loaded"])
        self.assertEqual(result["state"], "awaiting_native_SHA_admission")

    def test_insufficient_capacity_prevents_first_write(self):
        self.connection.free = 1
        with self.assertRaisesRegex(ValueError, "storage headroom"): self.run_sequence()
        self.assertEqual(self.connection.stores, 0)
        self.assertEqual(len(list((self.root / "run").glob("batch-failure-*.private.json"))), 1)

    def test_positive_200_publishes_files_and_receipt_without_claiming_250(self):
        self.connection.rename_response = "200 Rename complete"
        result = self.run_sequence()
        self.assertEqual(result["positively_completed_files"], 2)
        first = json.loads((self.root / "run/files/0.gguf.complete.private.json").read_text())
        self.assertFalse(first["FTP_250"])
        self.assertTrue(first["remote_partial_absent"])
        self.assertEqual(self.connection.renames, 3)

    def test_reviewed_publication_binds_original_and_retained_proof(self):
        out = self.root / "reviewed"; out.mkdir()
        original = self.plan["files"][0]["original"]; destination = REMOTE_ROOT + "/" + original["path"]
        proof = dict(schema="ps5-qwen-reviewed-model-file-publication-v1", original=original,
            destination=destination, source_stream_SHA_verified=True, source_identity_stable=True,
            FTP_226=True, FTP_2xx_rename=True, exact_rename_reply_not_recorded=True,
            destination_size_verified=True, partial_absent=True, remote_regular_world_readable=True,
            uncertain_rename_repeated=False, title_launches=0, GPU_calls=0)
        path = out / "proof.json"; path.write_text(json.dumps(proof))
        row = dict(path=str(path), bytes=path.stat().st_size, sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        value = dict(FTP_250=False, FTP_2xx_rename=True, remote_partial_absent=True, reviewed_publication=row)
        self.assertTrue(batch.positive_rename_record(value, original, destination, out))
        self.assertFalse(batch.positive_rename_record(value, dict(original, bytes=1), destination, out))
        path.write_text(json.dumps(dict(proof, uncertain_rename_repeated=True)))
        self.assertFalse(batch.positive_rename_record(value, original, destination, out))

    def test_oversized_prior_metadata_rejects_before_network_write(self):
        self.connection.free = 1
        with self.assertRaises(ValueError): self.run_sequence()
        (self.root / "run/batch.intent.private.json").write_bytes(b" " * ((1 << 20) + 1))
        with self.assertRaisesRegex(ValueError, "metadata exceeded"): self.run_sequence(resume=True)
        self.assertEqual(self.connection.stores, 0)

    def test_ambiguous_file_is_never_retried_on_resume(self):
        self.connection.fail_store = 2
        with self.assertRaises(TimeoutError): self.run_sequence()
        with self.assertRaisesRegex(ValueError, "uncertain prior attempt"): self.run_sequence(resume=True)
        self.assertEqual(self.connection.stores, 2)
        self.assertNotIn(REMOTE_ROOT + "/model-receipt.json", self.connection.files)
        self.assertEqual(len(list((self.root / "run").glob("batch-failure-*.private.json"))), 2)

    def test_ambiguous_receipt_is_not_repeated(self):
        self.connection.fail_store = 3
        with self.assertRaises(TimeoutError): self.run_sequence()
        with self.assertRaisesRegex(ValueError, "publication already has an attempt"): self.run_sequence(resume=True)
        self.assertEqual(self.connection.stores, 3)
        self.assertNotIn(REMOTE_ROOT + "/model-receipt.json", self.connection.files)

    def test_read_only_capacity_failure_can_resume_without_replacing_evidence(self):
        self.connection.free = 1
        with self.assertRaises(ValueError): self.run_sequence()
        self.connection.free = 10**12
        self.run_sequence(resume=True)
        self.assertEqual(self.connection.stores, 3)
        self.assertEqual(len(list((self.root / "run").glob("capacity-*"))), 3)
        self.assertEqual(len(list((self.root / "run").glob("batch-failure-*.private.json"))), 1)

    def test_receipt_readback_mismatch_prevents_final_publication(self):
        self.connection.corrupt_receipt_readback = True
        with self.assertRaisesRegex(ValueError, "full readback differs"): self.run_sequence()
        self.assertEqual(self.connection.renames, 2)
        self.assertNotIn(REMOTE_ROOT + "/model-receipt.json", self.connection.files)

    def test_whole_deadline_expires_before_network_write(self):
        values = iter([0, 4000])
        with self.assertRaises(TimeoutError): self.run_sequence(now=lambda: next(values), timeout_seconds=3600)
        self.assertEqual(self.connection.stores, 0)

    def test_host_clock_discontinuity_prevents_network_write(self):
        values = iter([0, 4])
        with self.assertRaisesRegex(ValueError, "clock continuity"):
            self.run_sequence(now=lambda: next(values))
        self.assertEqual(self.connection.stores, 0)

    def test_real_gate_rejects_metadata_fixture_before_any_batch_or_network(self):
        receipt = json.dumps(dict(schema="ps5-qwen-bf16-conversion-v2", outtype="bf16",
            original_shards_verified=True, test_fixture_only=True)).encode()
        with self.assertRaises(ValueError):
            batch.run_batch(self.plan, receipt, self.connection, self.root / "run",
                            self.root / "writer.lock", guard=self.guard)
        self.assertFalse((self.root / "run").exists())
        self.assertEqual(self.connection.stores, 0)


if __name__ == "__main__": unittest.main()
