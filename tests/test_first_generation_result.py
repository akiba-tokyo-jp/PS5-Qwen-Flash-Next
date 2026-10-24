#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Synthetic report fault injection; no files from a console or model are used."""
import copy
import json
import struct
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
            "": dict(schema="ps5-qwen-plan-validation-result-v1", **provenance,
                state="completed_waiting_for_ordinary_close", request_reset_completed=True,
                GPU_completion_and_retirement_passed=True, model_resources_released_after_completion=True,
                model_loaded=False, full_model_inference_executed=True, answer_quality_qualified=False,
                native_display_started=True, external_requests_accepted=2, arithmetic_smoke_passed=True,
                source_IO_completed=True, source_read_bytes=9000000000, source_read_chunks=1200,
                maximum_source_read_bytes=8 << 20,
                postload_device_live_bytes=0, postload_device_peak_bytes=1024 << 20,
                postload_device_allocations=16, CPU_heap_peak_bytes=128 << 20, untracked_libc_heap_fallbacks=0,
                driver_revision="872cc1264ad8ba5d6b888b092968fa5858a38c58", profile="cumulative-idle",
                native_archive_sha256="b57fe26e969940d147be05c1ffae830503d4865877281dffe03af32328f49925",
                token_ids=[10, 20], output_bytes=[52, 10], text_generation_observed=True,
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
            ".mapping": dict(schema="ps5-qwen-model-virtual-source-admission-v1", **owner,
                all_SHA256_matched=True, original_footprint_matched=True, mapped_files=76,
                mapped_file_bytes=self.binding["bytes"], completed_unmaps=76, model_loaded=False,
                Vulkan_initialized=False, GPU_compute_calls=0, mapped_payload_reads=0,
                resident_set_qualified=False, file_backed_model_mmap_calls=0,
                source_virtual_protection="none", state="virtual_sources_completed_before_backend"),
            ".memory": dict(schema="ps5-qwen-memory-admission-v1", **owner,
                model_loaded=False, resident_set_qualified=False, device_weights_bytes=8755105280,
                mapped_file_bytes=self.binding["bytes"], planned_resident_headroom_bytes=12110548480,
                CPU_budget_bytes=512 << 20, maximum_explicitly_addressed_CPU_model_page_bytes=160432128,
                maximum_CPU_heap_bytes=512 << 20, maximum_resident_CPU_model_source_bytes=0,
                CPU_heap_budget_includes_source_read_window=True,
                Flexible_reserve_bytes=256 << 20, kernel_extra_margin_bytes=4 << 20,
                kernel_vm0_free_pages=2890, kernel_vm0_minimum_pages=898, kernel_vm0_reserved_pages=206,
                maximum_postload_device_buffer_bytes=512 << 20, maximum_aggregate_postload_device_buffer_bytes=1792 << 20,
                driver_free_bytes=12201230336, Direct_largest_available_bytes=12201230336, Flexible_available_bytes=404750336,
                device_buffer_alignment_bytes=65536, device_buffer_batch_limit_bytes=2**31),
            ".source": dict(schema="ps5-qwen-bounded-source-admission-v1", **owner,
                direct_read_preflight_passed=True, maximum_window_bytes=8 << 20, maximum_open_handles=8,
                bounded_CPU_rows_enabled=True, CPU_source_pointer_dereferences_enabled=False,
                CPU_source_read_window_in_Direct_heap=True,
                mapped_source_upload_dereferences_enabled=False, CPU_matrix_fallback_enabled=False,
                maximum_CPU_workspace_bytes=16 << 20, model_loaded=False, Vulkan_initialized=False),
            ".first.token-1": dict(schema="ps5-qwen-first-generation-token-v1", run_id="a"*32,
                ordinal=1, token_id=10, piece_bytes=[52], elapsed_ms=100),
            ".first.token-2": dict(schema="ps5-qwen-first-generation-token-v1", run_id="a"*32,
                ordinal=2, token_id=20, piece_bytes=[10], elapsed_ms=120)}
        self.records[".first.result"] = dict(schema="ps5-qwen-first-request-result-v1", **owner,
            run_id="a"*32, model_loaded=True, request_reset_completed=True,
            **{key: copy.deepcopy(self.records[""][key]) for key in ("stop_reason", "token_ids", "output_bytes", "metrics")})
        self.records[".demo.ready"] = dict(schema="ps5-qwen-bounded-demo-ready-v1", **owner,
            run_id="a"*32, maximum_requests=2, context_tokens=256, maximum_output_tokens=32,
            prompt="Count from 1 to 8, separated by commas. Reply with only the sequence.", listener_bind="0.0.0.0", model_loaded=True, native_display_started=True)
        self.records[".demo.cache"] = dict(schema="ps5-qwen-demo-cold-cache-admission-v1", **owner,
            run_id="a"*32, context_recreated_after_positive_completion=True, expert_cache_initially_empty=True,
            model_reloaded=False, model_loaded=True, file_pages_and_pipelines_cold=False)
        demo = dict(schema="ps5-qwen-bounded-demo-result-v1", **owner, run_id="a"*32,
            external_requests_accepted=2, external_requests_completed=2, all_monitor_assets_requested=True,
            finish_acknowledgement_delivered=True, listener_stopped=True, model_loaded=True,
            status_observations=3, observed_clock_advance_ms=2000, requests=[])
        for ordinal in (1, 2):
            prefix = ".demo" + str(ordinal)
            request_id = "a"*32 + "-" + str(ordinal)
            self.records[prefix + ".intent"] = dict(schema="ps5-qwen-demo-request-intent-v1", **owner,
                run_id="a"*32, id=request_id, ordinal=ordinal, context_tokens=256, maximum_prompt_tokens=64,
                maximum_output_tokens=32, maximum_generation_seconds=3600, enable_thinking=False,
                prompt="Count from 1 to 8, separated by commas. Reply with only the sequence.", rendered_prompt="Synthetic original-template request")
            terminal = dict(schema="ps5-qwen-demo-request-result-v1", **owner, run_id="a"*32,
                id=request_id, ordinal=ordinal, request_reset_completed=True,
                cache_condition="empty expert cache" if ordinal == 1 else "retained expert cache",
                GPU_completion_and_retirement_passed=True, model_loaded=True,
                token_ids=[3, 4], output_bytes=list(b"1, 2, 3, 4, 5, 6, 7, 8"), stop_reason="end_of_generation",
                metrics=dict(prompt_tokens=10, generated_tokens=2, prefill_ms=90, total_ms=140,
                    ttft_ms=100, decode_tokens_per_second=50))
            self.records[prefix + ".result"] = terminal
            self.records[prefix + ".display.json"] = dict(schema="ps5-qwen-displayed-frame-v1", **owner,
                run_id="a"*32, id=request_id, width=1920, height=1080, BMP_bytes=8294454,
                generated_tokens=2, clock_calibrated=True, model_loaded=True, positive_VideoOut_completion=True,
                evidence="CPU raster after the matching completed VideoOut flip", epoch_ms=1792675000000,
                TTFT_ms=100, decode_tokens_per_second=50)
            demo["requests"].append(terminal)
            for index, piece in ((1, [49]), (2, list(b", 2, 3, 4, 5, 6, 7, 8"))):
                self.records[prefix + ".token-" + str(index)] = dict(id=request_id, type="token", state="generating",
                    ordinal=index, token_id=index + 2, error=0, piece_bytes=piece, elapsed_ms=80 + index*20)
        self.records[".demo.result"] = demo
        self.records[""]["demonstration"] = demo

    def save(self):
        for suffix, record in self.records.items():
            Path(str(self.result) + suffix).write_text(json.dumps(record), encoding="utf-8")
        for ordinal in (1, 2):
            image = Path(str(self.result) + ".demo" + str(ordinal) + ".display.bmp")
            if not image.exists():
                # A sparse synthetic container tests evidence bindings/layout,
                # without creating fake rendered or physical-display evidence.
                header = bytearray(54); header[:2] = b"BM"
                struct.pack_into("<I", header, 2, 8294454)
                struct.pack_into("<IIIIHH", header, 10, 54, 40, 1920, 1080, 1, 32)
                with image.open("xb") as stream: stream.write(header); stream.truncate(8294454)

    def test_complete_plan_records_reconstruct_exact_outputs_and_rates(self):
        self.save()
        result = validate(self.result, self.binding)
        self.assertEqual(result["text"], "4\n")
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
            (".mapping", "file_backed_model_mmap_calls", 1), (".mapping", "source_virtual_protection", "read"),
            (".source", "bounded_CPU_rows_enabled", False), (".source", "CPU_source_pointer_dereferences_enabled", True),
            (".memory", "device_buffer_alignment_bytes", 3), (".memory", "device_buffer_batch_limit_bytes", 2**30),
            (".first.intent", "enable_thinking", True), (".first.intent", "maximum_output_tokens", 33),
            (".first.token-1", "ordinal", 2), (".first.token-2", "run_id", "f"*32),
            (".first.token-2", "elapsed_ms", 99), (".first.token-2", "piece_bytes", [True])]
        changes += [(".source", "maximum_window_bytes", 16 << 20), ("", "source_IO_completed", False),
            ("", "maximum_source_read_bytes", (8 << 20) + 1), ("", "external_requests_accepted", 1),
            (".demo.result", "listener_stopped", False), (".demo.result", "observed_clock_advance_ms", 0),
            (".demo1.token-2", "elapsed_ms", 99), (".demo2.intent", "maximum_output_tokens", 256)]
        changes += [(".demo1.display.json", "generated_tokens", 1),
            (".demo2.display.json", "positive_VideoOut_completion", False),
            (".demo2.display.json", "decode_tokens_per_second", 51)]
        changes += [("", "postload_device_live_bytes", 1), ("", "postload_device_peak_bytes", (1792 << 20) + 1),
            ("", "CPU_heap_peak_bytes", (512 << 20)+1), ("", "untracked_libc_heap_fallbacks", 1),
            (".memory", "driver_free_bytes", 12110548479), (".memory", "Flexible_available_bytes", (264 << 20)-1),
            (".memory", "maximum_resident_CPU_model_source_bytes", 16384),
            (".memory", "CPU_heap_budget_includes_source_read_window", False),
            (".source", "CPU_source_read_window_in_Direct_heap", False),
            (".memory", "kernel_vm0_free_pages", 1153)]
        original = copy.deepcopy(self.records)
        for suffix, key, value in changes:
            with self.subTest(suffix=suffix, key=key):
                self.records = copy.deepcopy(original)
                self.records[suffix][key] = value
                self.save()
                with self.assertRaises(ValueError):
                    validate(self.result, self.binding)

    def test_prior_native_integrity_requires_explicit_mode_deadline_and_evidence(self):
        integrity = self.records[".integrity"]
        integrity.update(verification_mode="prior_native_SHA_and_unchanged_sealed_identity",
            payload_SHA_computed_in_this_run=False, metadata_validation_deadline_seconds=60,
            verification_elapsed_ms=500, prior_native_verification_elapsed_ms=5370082,
            prior_native_integrity_report_sha256="d"*64, sealed_identity_snapshot_sha256="e"*64)
        self.save()
        validate(self.result, self.binding)
        original = copy.deepcopy(self.records)
        for key, value in (("payload_SHA_computed_in_this_run", True),
            ("metadata_validation_deadline_seconds", 7200), ("verification_elapsed_ms", 60001),
            ("prior_native_verification_elapsed_ms", 7200001),
            ("prior_native_integrity_report_sha256", "invalid"), ("sealed_identity_snapshot_sha256", None)):
            with self.subTest(key=key):
                self.records = copy.deepcopy(original)
                self.records[".integrity"][key] = value
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

    def test_incomplete_smoke_answer_is_not_admitted(self):
        self.records[""]["output_bytes"] = [0xe3, 0x81]
        self.records[".first.token-2"]["piece_bytes"] = []
        self.save()
        with self.assertRaises(ValueError):
            validate(self.result, self.binding)

    def test_duplicate_json_key_is_rejected(self):
        self.save()
        self.result.write_text('{"schema":"a","schema":"b"}')
        with self.assertRaises(ValueError):
            validate(self.result, self.binding)

    def test_measured_416MiB_heap_remains_inside_original_512MiB_CPU_budget(self):
        self.records[""]["CPU_heap_peak_bytes"] = 436273152
        self.records[".memory"]["Flexible_available_bytes"] = 404750336
        self.save()
        validate(self.result, self.binding)

    def test_original_CPU_budget_boundary_is_inclusive(self):
        self.records[""]["CPU_heap_peak_bytes"] = 512 << 20
        self.save()
        validate(self.result, self.binding)

    def test_self_consistent_but_incomplete_external_answer_is_rejected(self):
        terminal = self.records[".demo1.result"]
        terminal["output_bytes"] = list(b"1, 2, 3")
        self.records[".demo1.token-2"]["piece_bytes"] = list(b", 2, 3")
        self.save()
        with self.assertRaisesRegex(ValueError, "counting sequence"):
            validate(self.result, self.binding)


if __name__ == "__main__":
    unittest.main()
