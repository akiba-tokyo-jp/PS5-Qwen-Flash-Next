# SPDX-License-Identifier: MIT
"""Synthetic writer tests; no original weights, model or console is accessed."""
from enum import Enum
import hashlib
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from resumable_gguf import install


class State(Enum):
    NO_FILE = 0; EMPTY = 1; KV_DATA = 2; WEIGHTS = 3


class Tensor:
    def __init__(self, value): self.value = value; self.nbytes = len(value); self.calls = 0
    def tofile(self, file): self.calls += 1; file.write(self.value)


class Writer:
    def __init__(self, path):
        self.path = path; self.fout = None; self.state = State.NO_FILE; self.dry_run = False
        self.temp_file = None; self.data_alignment = 32
        self.values = [Tensor(bytes([i])*65) for i in (1, 2, 3)]
        self.tensors = [{"tensor" + str(i): SimpleNamespace(nbytes=65, tensor=t)} for i, t in enumerate(self.values)]
    def print_plan(self): return [self.path / ("model-" + str(i) + ".gguf") for i in range(3)]
    def open_output_file(self, path=None): raise AssertionError("The test must use the bounded adapter")
    def write_tensors_to_file(self, progress=False): raise AssertionError("The test must use the bounded adapter")
    @staticmethod
    def ggml_pad(size, alignment): return (size + alignment - 1) // alignment * alignment
    def write_padding(self, file, size): file.write(bytes(self.ggml_pad(size, 32) - size))
    def write_ti_data_to_file(self):
        for i, fp in enumerate(self.fout): fp.write(b"-tensor-info-" + bytes([i]))
    def run(self):
        self.open_output_file()
        for fp in self.fout: fp.write(b"synthetic-GGUF-header")
        self.state = State.KV_DATA; self.write_tensors_to_file()
        for fp in self.fout: fp.close()


class ResumeWriterTests(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).resolve().parents[1] / ".test-tmp"; root.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=root); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.old = self.root / "old"; self.new = self.root / "new"
        self.old.mkdir(); self.new.mkdir()
    def seed(self):
        result, restore = install(Writer, State, self.old, self.new, lambda _: None)
        try: Writer(self.new).run()
        finally: restore()
        for file in self.new.glob("*.gguf"): file.replace(self.old / file.name)
        return result
    def test_completed_splits_are_linked_and_only_partial_split_materializes(self):
        self.seed(); partial = self.old / "model-2.gguf"
        partial.write_bytes(partial.read_bytes()[:-1])
        old = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in self.old.glob("*.gguf")}
        events = []; outcome, restore = install(Writer, State, self.old, self.new, events.append)
        writer = Writer(self.new)
        try: writer.run()
        finally: restore()
        self.assertEqual([v.calls for v in writer.values], [0, 0, 1])
        self.assertEqual(len(outcome["retained"]), 2); self.assertEqual(len(outcome["written"]), 1)
        self.assertEqual([e["retained"] for e in events], [True, True, False])
        self.assertEqual(outcome["retained_payload_bytes"], 130)
        self.assertEqual(outcome["newly_written_payload_bytes"], 65)
        self.assertEqual(old, {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in self.old.glob("*.gguf")})
        self.assertTrue(all(row["payload_audited"] is False for row in outcome["retained"]))
    def test_same_size_wrong_header_is_recomputed_and_prior_bytes_are_kept(self):
        self.seed(); file = self.old / "model-0.gguf"; raw = bytearray(file.read_bytes()); raw[0] ^= 1; file.write_bytes(raw)
        outcome, restore = install(Writer, State, self.old, self.new, lambda _: None)
        writer = Writer(self.new)
        try: writer.run()
        finally: restore()
        self.assertEqual(writer.values[0].calls, 1); self.assertEqual(file.read_bytes(), raw)
        self.assertEqual(len(outcome["retained"]), 2)
    def test_nonempty_output_is_rejected(self):
        (self.new / "occupied").write_text("keep")
        with self.assertRaises(ValueError): install(Writer, State, self.old, self.new, lambda _: None)

    def test_failed_progress_closes_files_and_retains_partial_evidence(self):
        def failed(_): raise RuntimeError("Injected journal failure")
        outcome, restore = install(Writer, State, self.old, self.new, failed)
        writer = Writer(self.new)
        try:
            with self.assertRaises(RuntimeError): writer.run()
        finally: restore()
        self.assertFalse(outcome["all_splits_written"])
        self.assertTrue(all(fp.closed for fp in writer.fout))
        file = self.new / "model-0.gguf"
        self.assertTrue(file.is_file()); file.rename(self.new / "preserved.gguf")

    def test_failed_tensor_write_closes_unfinished_payload(self):
        outcome, restore = install(Writer, State, self.old, self.new, lambda _: None)
        writer = Writer(self.new)
        def failed(file):
            file.write(b"partial"); raise RuntimeError("Injected payload failure")
        writer.values[0].tofile = failed
        try:
            with self.assertRaises(RuntimeError): writer.run()
        finally: restore()
        self.assertFalse(outcome["all_splits_written"])
        file = self.new / "model-0.gguf"
        self.assertTrue(file.is_file()); file.rename(self.new / "partial.gguf")

    def test_unexpected_rewrite_volume_is_rejected_before_exceeding_the_bound(self):
        outcome, restore = install(Writer, State, self.old, self.new, lambda _: None)
        writer = Writer(self.new)
        try:
            with patch("resumable_gguf.MAX_NEW_PAYLOAD_BYTES", 128):
                with self.assertRaisesRegex(ValueError, "new-payload bound"): writer.run()
        finally: restore()
        self.assertEqual(outcome["newly_written_payload_bytes"], 65)
        self.assertFalse((self.new / "model-1.gguf").exists())
        self.assertFalse(outcome["all_splits_written"])


if __name__ == "__main__": unittest.main()
