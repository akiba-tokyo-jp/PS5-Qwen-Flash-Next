# SPDX-License-Identifier: MIT
"""Fault injection for directory sequencing; no real receipt, network or PS5 ELF.

The full original-plan and CPU admissions are explicitly outside these tests.
Callbacks model only the already-admitted small metadata operation.
"""
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import model_directory_stage as stage


class FakeConnection:
    def __init__(self):
        self.created = False; self.marker = None; self.calls = []
        self.fail = None; self.finalized = False
    def absent(self, path):
        if path == stage.REMOTE_ROOT and self.created: raise ValueError("Existing directory")
        if path.endswith(stage.MARKER) and self.marker is not None: raise ValueError("Existing marker")
    @contextmanager
    def ftp(self): yield self
    def mkd(self, path):
        self.calls.append("mkdir")
        if self.fail == "mkdir": raise TimeoutError("Ambiguous mkdir")
        self.created = True; return path
    def directory_metadata(self, ftp):
        if self.marker is None: return []
        return [dict(name=stage.MARKER, mode="-rw-r--r--")]
    def storbinary(self, command, stream, block):
        self.calls.append("upload"); self.marker = stream.read(block)
        return "426 Transfer interrupted" if self.fail == "upload" else "226 Transfer complete"
    def size(self, path): return len(self.marker)
    def model_get(self, path, limit):
        if self.fail == "readback" or (self.fail == "final_readback" and self.finalized): return b"changed"
        return self.marker


class DirectoryStage(unittest.TestCase):
    def setUp(self):
        base = Path(__file__).resolve().parents[1] / ".test-tmp"; base.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=base); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.out = self.root / "run"; self.connection = FakeConnection()
        raw = json.dumps(dict(schema="ps5-qwen-model-directory-owner-v1", nonce="a" * 32,
            original_receipt_sha256="b" * 64)).encode()
        self.path = self.root / "marker.json"; self.path.write_bytes(raw)
        self.manifest = dict(schema="ps5-qwen-model-directory-controller-v1", remote_root=stage.REMOTE_ROOT,
            allowed_actions=["prepare", "finalize", "verify"], input_hashes_stable=True,
            imports_subset_of_qualified_controller=True, console_access=False,
            title_launches=0, GPU_calls=0, owner_nonce="a" * 32, plan_sha256="c" * 64,
            artifact=dict(path="synthetic-never-executed.elf"), marker=dict(path=str(self.path),
            bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest()))
        self.controls = []; self.bad_control = None; self.guard_count = 0
    def guard(self): self.guard_count += 1
    def control(self, mode, out):
        self.controls.append(mode)
        if self.bad_control == mode: return b"END success=0\n"
        lines = [f"BEGIN mode={mode} uid=1 euid=0 GPU_calls=0 title_launches=0"]
        if mode == "finalize":
            self.connection.finalized = True
            lines += [("MODEL_DIRECTORY uid=0 gid=0 mode=0755 marker_bytes=" +
                str(self.manifest["marker"]["bytes"]) + " no_symlinks=1 marker_verified=1")] * 2
        lines += [f"END success=1 mode={mode} parent_ownership_restored={int(mode != 'prepare')} GPU_calls=0 title_launches=0"]
        return ("\n".join(lines) + "\n").encode()
    def run_stage(self):
        return stage.prepare_directory_once(self.connection, self.manifest, self.out,
            guard=self.guard, control=self.control)
    def failure(self): return json.loads((self.out / "failure.private.json").read_text())

    def test_positive_finalize_and_readback_precede_proof(self):
        result = self.run_stage()
        self.assertTrue(result["parent_ownership_restored"])
        self.assertEqual(self.controls, ["prepare", "finalize"])
        self.assertEqual(self.connection.calls, ["mkdir", "upload"])
        self.assertGreaterEqual(self.guard_count, 7)
        self.assertTrue((self.out / "complete.private.json").exists())

    def test_guard_refusal_precedes_all_mutations(self):
        def refuse(): raise ValueError("Reservation changed")
        with self.assertRaises(ValueError):
            stage.prepare_directory_once(self.connection, self.manifest, self.out,
                guard=refuse, control=self.control)
        self.assertEqual(self.controls, []); self.assertEqual(self.connection.calls, [])

    def test_failed_prepare_is_not_followed_by_mkdir_or_retry(self):
        self.bad_control = "prepare"
        with self.assertRaises(ValueError): self.run_stage()
        self.assertEqual(self.controls, ["prepare"]); self.assertEqual(self.connection.calls, [])
        with self.assertRaises(FileExistsError): self.run_stage()
        self.assertEqual(self.controls, ["prepare"])

    def test_ambiguous_mkdir_never_uploads_or_automatically_finalizes(self):
        self.connection.fail = "mkdir"
        with self.assertRaises(TimeoutError): self.run_stage()
        self.assertEqual(self.controls, ["prepare"]); self.assertEqual(self.connection.calls, ["mkdir"])
        self.assertTrue(self.failure()["unresolved_attempt_requires_review"])

    def test_upload_completion_and_full_readback_are_required(self):
        for failure in ("upload", "readback"):
            with self.subTest(failure=failure):
                self.out = self.root / failure; self.connection = FakeConnection(); self.controls = []
                self.connection.fail = failure
                with self.assertRaises(ValueError): self.run_stage()
                self.assertEqual(self.controls, ["prepare"])
                self.assertFalse((self.out / "complete.private.json").exists())
                self.assertTrue(self.failure()["remote_partials_retained"])

    def test_failed_finalize_retains_record_without_readmission(self):
        self.bad_control = "finalize"
        with self.assertRaises(ValueError): self.run_stage()
        self.assertEqual(self.controls, ["prepare", "finalize"])
        self.assertFalse(self.failure()["parent_ownership_restored"])
        self.assertFalse((self.out / "complete.private.json").exists())

    def test_post_finalize_failure_preserves_positive_parent_restoration(self):
        self.connection.fail = "final_readback"
        with self.assertRaises(ValueError): self.run_stage()
        self.assertTrue(self.failure()["parent_ownership_restored"])
        self.assertFalse((self.out / "complete.private.json").exists())

    def test_changed_marker_rejects_before_controls_or_network(self):
        self.path.write_bytes(b"changed")
        with self.assertRaises(ValueError): self.run_stage()
        self.assertEqual(self.controls, []); self.assertEqual(self.connection.calls, [])
        self.assertFalse(self.out.exists())


if __name__ == "__main__": unittest.main()
