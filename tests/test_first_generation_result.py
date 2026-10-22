#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Synthetic report fault injection; no files from a console or model are used."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from first_generation_result import validate


class FirstGenerationRecords(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).resolve().parents[1] / ".test-tmp"
        root.mkdir(exist_ok=True)
        self.directory = tempfile.TemporaryDirectory(dir=root)
        self.addCleanup(self.directory.cleanup)
        self.result = Path(self.directory.name) / "result.json"
        self.binding = dict(schema="ps5-qwen-first-generation-binding-v1", pid=1234, files=76,
            bytes=359235922432 + 1000000, run_id="a"*32, candidate_SELF_sha256="b"*64, model_receipt_sha256="c"*64)
        owner = dict(pid=1234)
        provenance = {key: self.binding[key] for key in ("pid", "run_id", "candidate_SELF_sha256", "model_receipt_sha256")}
        self.records = {
            "": dict(schema="ps5-qwen-first-generation-result-v1", **provenance,
                state="completed_waiting_for_ordinary_close", request_reset_completed=True,
                GPU_completion_and_retirement_passed=True, model_resources_released_after_completion=True,
                model_loaded=False, full_model_inference_executed=True, answer_quality_qualified=False,
                native_display_started=False, external_requests_accepted=0,
                driver_revision="872cc1264ad8ba5d6b888b092968fa5858a38c58", profile="cumulative-idle",
                native_archive_sha256="b57fe26e969940d147be05c1ffae830503d4865877281dffe03af32328f49925",
                token_ids=[10, 20], output_bytes=[0xe3, 0x81, 0x82], text_generation_observed=True,
                stop_reason="end_of_generation", metrics=dict(prompt_tokens=10, generated_tokens=2,
                    prefill_ms=90, total_ms=140, TTFT_ms=100, decode_tokens_per_second=50)),
            ".first.start": dict(schema="ps5-qwen-first-generation-start-v1", **provenance,
                model_loaded=False, Vulkan_initialized=False),
            ".first.intent": dict(schema="ps5-qwen-first-generation-intent-v1", **owner, run_id="a"*32,
                context_tokens=256, maximum_prompt_tokens=64, maximum_output_tokens=32,
                maximum_generation_seconds=3600, enable_thinking=False, rendered_prompt="Synthetic original-template prompt"),
            ".integrity": dict(schema="ps5-qwen-model-integrity-v1", **owner, files_verified=76,
                mapped_file_bytes=self.binding["bytes"], verified_file_bytes=self.binding["bytes"],
                maximum_verification_seconds=7200, verification_elapsed_ms=2000000,
                all_SHA256_matched=True, model_loaded=False, Vulkan_initialized=False),
            ".mapping": dict(schema="ps5-qwen-model-mapping-admission-v1", **owner,
                all_SHA256_matched=True, original_footprint_matched=True, mapped_files=76,
                mapped_file_bytes=self.binding["bytes"], completed_unmaps=76, model_loaded=False,
                Vulkan_initialized=False, GPU_compute_calls=0, mapped_payload_reads=0,
                resident_set_qualified=False, state="mapping_completed_before_backend"),
            ".memory": dict(schema="ps5-qwen-memory-admission-v1", **owner,
                model_loaded=False, resident_set_qualified=False, device_weights_bytes=8755105280,
                mapped_file_bytes=self.binding["bytes"], planned_resident_headroom_bytes=11976330752,
                device_buffer_alignment_bytes=65536, device_buffer_batch_limit_bytes=2**31),
            ".first.token-1": dict(schema="ps5-qwen-first-generation-token-v1", run_id="a"*32,
                ordinal=1, token_id=10, piece_bytes=[0xe3, 0x81], elapsed_ms=100),
            ".first.token-2": dict(schema="ps5-qwen-first-generation-token-v1", run_id="a"*32,
                ordinal=2, token_id=20, piece_bytes=[0x82], elapsed_ms=120)}

    def save(self):
        for suffix, record in self.records.items():
            Path(str(self.result) + suffix).write_text(json.dumps(record), encoding="utf-8")

    def test_complete_records_reconstruct_exact_split_utf8_and_rate(self):
        self.save()
        result = validate(self.result, self.binding)
        self.assertEqual(result["text"], "あ")
        self.assertEqual(result["metrics"]["decode_tokens_per_second"], 50)
        self.assertFalse(result["answer_quality_qualified"])
        self.assertFalse(result["ordinary_close_and_original_restoration_verified"])

    def test_inconsistent_gate_owner_provenance_bytes_count_or_timing_rejected(self):
        changes = [("", "pid", 999), ("", "run_id", "d"*32), ("", "model_receipt_sha256", "e"*64),
            ("", "GPU_completion_and_retirement_passed", 1), ("", "request_reset_completed", False),
            ("", "stop_reason", "output_token_limit"), ("", "text_generation_observed", False),
            ("", "output_bytes", [1, 2, 3]), ("", "token_ids", [True, 20]),
            (".integrity", "all_SHA256_matched", False), (".integrity", "verified_file_bytes", 10),
            (".integrity", "verification_elapsed_ms", 7200001), (".mapping", "completed_unmaps", 75),
            (".mapping", "mapped_payload_reads", 1), (".mapping", "state", "completed_waiting_for_ordinary_close"),
            (".memory", "device_buffer_alignment_bytes", 3), (".memory", "device_buffer_batch_limit_bytes", 2**30),
            (".first.intent", "enable_thinking", True), (".first.intent", "maximum_output_tokens", 33),
            (".first.token-1", "ordinal", 2), (".first.token-2", "run_id", "f"*32),
            (".first.token-2", "elapsed_ms", 99), (".first.token-2", "piece_bytes", [True])]
        original = copy.deepcopy(self.records)
        for suffix, key, value in changes:
            with self.subTest(suffix=suffix, key=key):
                self.records = copy.deepcopy(original)
                self.records[suffix][key] = value
                self.save()
                with self.assertRaises(ValueError):
                    validate(self.result, self.binding)
        for key, value in (("TTFT_ms", 99), ("decode_tokens_per_second", 51),
                           ("generated_tokens", True), ("total_ms", float("nan"))):
            with self.subTest(metric=key):
                self.records = copy.deepcopy(original)
                self.records[""]["metrics"][key] = value
                self.save()
                with self.assertRaises(ValueError):
                    validate(self.result, self.binding)

    def test_missing_extra_or_failure_records_prevent_completion(self):
        self.save()
        missing = Path(str(self.result) + ".first.token-2")
        missing.unlink()
        with self.assertRaises(ValueError):
            validate(self.result, self.binding)
        self.save()
        extra = Path(str(self.result) + ".first.token-3")
        extra.write_text("{}")
        with self.assertRaises(ValueError):
            validate(self.result, self.binding)
        extra.unlink()
        Path(str(self.result) + ".failure").write_text("{}")
        with self.assertRaises(ValueError):
            validate(self.result, self.binding)

    def test_partial_utf8_is_preserved_as_partial_output(self):
        self.records[""]["output_bytes"] = [0xe3, 0x81]
        self.records[".first.token-2"]["piece_bytes"] = []
        self.save()
        result = validate(self.result, self.binding)
        self.assertFalse(result["output_is_complete_UTF8"])
        self.assertFalse(result["answer_quality_qualified"])

    def test_duplicate_json_key_is_rejected(self):
        self.save()
        self.result.write_text('{"schema":"a","schema":"b"}')
        with self.assertRaises(ValueError):
            validate(self.result, self.binding)


if __name__ == "__main__":
    unittest.main()
