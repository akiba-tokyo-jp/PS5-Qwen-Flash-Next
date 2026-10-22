# SPDX-License-Identifier: MIT
"""Reject incomplete resume provenance without reading weights or a console."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import resume_provenance as gate


class ResumeAdmission(unittest.TestCase):
    def setUp(self):
        root = gate.ROOT / ".test-tmp"; root.mkdir(exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=root); self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.tools = {"bounded_conversion.py": "original-test-only"}
        self.resume = {name: gate.sha(gate.ROOT / "tools" / name) for name in gate.RESUME_TOOLS}
        self.retention = dict(all_splits_written=True, retained=[{}] * 75, written=[{}],
            retained_tensors=["test." + str(i) for i in range(1250)], written_tensors=["test." + str(i) for i in range(1250, 1256)],
            retained_payload_bytes=359235922400, newly_written_payload_bytes=32)
        checkpoint = dict(schema="ps5-qwen-source-verification-checkpoint-v1", original_verification_reused=True,
            fresh_original_payload_rehash=False, preparation_tool_sources=self.tools, sources=[{}] * 131,
            console_access=False, learned_inference_performed=False)
        self.adapter = dict(schema="ps5-qwen-resumed-copy-adapter-v1", pinned_sources_modified=False,
            chunk_limit_bytes=8 << 20, maximum_source_read_bytes=8 << 20, complete_planned_copy_partition=True,
            original_copy_tensors=150, original_copy_BF16_bytes=351568363520,
            independent_payload_audit_required=True, console_access=False, learned_inference_performed=False,
            preparation_tool_sources=self.tools, resume_tool_sources=self.resume, retained_copy_tensors=149,
            written_copy_tensors=1, retained_copy_BF16_bytes=351568363488, written_copy_BF16_bytes=32,
            retention_record=self.record("retention.json", self.retention), checkpoint=self.record("checkpoint.json", checkpoint))
    def record(self, name, value):
        path = self.root / name; path.write_text(json.dumps(value), encoding="utf-8")
        return dict(path=str(path), bytes=path.stat().st_size, sha256=gate.sha(path))
    def test_structural_gate_accepts_complete_record_only(self):
        # The independent payload audit and compiled native gate remain mandatory.
        gate.validate_adapter(self.adapter, self.tools, self.resume)
    def test_counts_types_bounds_and_source_changes_fail(self):
        for key, value in (("retained_copy_tensors", 148), ("written_copy_tensors", True),
            ("retained_copy_BF16_bytes", 1), ("maximum_source_read_bytes", (8 << 20) + 1),
            ("complete_planned_copy_partition", False), ("pinned_sources_modified", True),
            ("console_access", True), ("learned_inference_performed", True), ("resume_tool_sources", {})):
            with self.subTest(key=key):
                adapter = deepcopy(self.adapter); adapter[key] = value
                with self.assertRaises(ValueError): gate.validate_adapter(adapter, self.tools, self.resume)
    def test_partial_duplicate_missing_and_false_payloads_fail(self):
        for key, value in (("all_splits_written", False), ("retained", []),
            ("written_tensors", ["test.0"] * 6), ("retained_payload_bytes", 359235922399)):
            with self.subTest(key=key):
                retention = deepcopy(self.retention); retention[key] = value
                adapter = deepcopy(self.adapter); adapter["retention_record"] = self.record("changed.json", retention)
                with self.assertRaises(ValueError): gate.validate_adapter(adapter, self.tools, self.resume)
    def test_modified_record_is_rejected(self):
        Path(self.adapter["checkpoint"]["path"]).write_text("{}", encoding="utf-8")
        with self.assertRaises(ValueError): gate.validate_adapter(self.adapter, self.tools, self.resume)

    def test_fully_completed_orphan_writer_requires_no_new_source_reads(self):
        retention = deepcopy(self.retention)
        retention.update(retained=[{}] * 76, written=[], retained_tensors=self.retention["retained_tensors"] + self.retention["written_tensors"],
            written_tensors=[], retained_payload_bytes=359235922432, newly_written_payload_bytes=0)
        adapter = deepcopy(self.adapter)
        adapter.update(retention_record=self.record("complete.json", retention), retained_copy_tensors=150,
            written_copy_tensors=0, retained_copy_BF16_bytes=351568363520, written_copy_BF16_bytes=0, maximum_source_read_bytes=0)
        gate.validate_adapter(adapter, self.tools, self.resume)
        adapter["maximum_source_read_bytes"] = 1
        with self.assertRaises(ValueError): gate.validate_adapter(adapter, self.tools, self.resume)


if __name__ == "__main__": unittest.main()
