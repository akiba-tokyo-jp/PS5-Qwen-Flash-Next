# SPDX-License-Identifier: MIT
"""Receipt prerequisites for offline planning; no model payload or console I/O."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import plan_model_transfer as planner


class TransferPlan(unittest.TestCase):
    def setUp(self):
        tools = {name: planner.sha(planner.ROOT / "tools" / name) for name in planner.PREPARATION_TOOLS}
        self.receipt = dict(schema="ps5-qwen-bf16-conversion-v2", files=[{}], preparation_tool_sources=tools,
            conversion_adapter=dict(schema="ps5-qwen-bounded-copy-adapter-v1",
                adapter_sha256=tools["bounded_conversion.py"], pinned_sources_modified=False,
                complete_planned_copies_streamed=True, chunk_limit_bytes=8 << 20,
                maximum_source_read_bytes=8 << 20, streamed_tensors=150,
                streamed_BF16_bytes=351568363520, console_access=False, learned_inference_performed=False))
        self.status = dict(schema="ps5-qwen-conversion-status-v1", phase="completed", receipt="model-receipt.json",
            verified=1, total=1, console_access=False, learned_inference_performed=False)

    def test_preparation_prerequisite_only_accepts_complete_provenance(self):
        planner.preparation_gate(self.receipt, self.status)
        # This is only the first gate: the compiled native gate still rejects
        # these deliberately incomplete metadata objects before any real plan.

    def test_all_incomplete_phases_reject(self):
        for phase in ["verifying_original_shards", "converting", "auditing_converted_metadata", "hashing_converted_files", "failed"]:
            with self.assertRaises(ValueError):
                planner.preparation_gate(self.receipt, dict(self.status, phase=phase))

    def test_marked_metadata_fixture_rejects(self):
        with self.assertRaises(ValueError):
            planner.preparation_gate(dict(self.receipt, test_fixture_only=True), self.status)

    def test_incomplete_final_file_hashes_reject(self):
        with self.assertRaises(ValueError): planner.preparation_gate(self.receipt, dict(self.status, verified=0))

    def test_frozen_source_change_rejects(self):
        receipt = deepcopy(self.receipt); receipt["preparation_tool_sources"]["bounded_conversion.py"] = "0" * 64
        with self.assertRaises(ValueError): planner.preparation_gate(receipt, self.status)

    def test_adapter_incomplete_or_wrong_precision_provenance_rejects(self):
        for key, value in [("complete_planned_copies_streamed", False), ("streamed_tensors", 149),
                ("streamed_BF16_bytes", 351568363519), ("pinned_sources_modified", True),
                ("chunk_limit_bytes", 16 << 20), ("maximum_source_read_bytes", 0),
                ("maximum_source_read_bytes", (8 << 20) + 1), ("console_access", True)]:
            receipt = deepcopy(self.receipt); receipt["conversion_adapter"][key] = value
            with self.assertRaises(ValueError): planner.preparation_gate(receipt, self.status)


if __name__ == "__main__": unittest.main()
