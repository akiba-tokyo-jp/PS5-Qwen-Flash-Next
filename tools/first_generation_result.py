#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Independently validate downloaded first-generation records; never access a PS5.

A positive generation result is separate from ordinary-close/restoration evidence.
Missing, inconsistent or failed records never establish completion.
"""
import argparse
import json
import math
import struct
from pathlib import Path


def require(condition, message):
    if not condition:
        raise ValueError(message)


def integer(value, minimum=0, maximum=2**63 - 1):
    return type(value) is int and minimum <= value <= maximum


def number(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def read_record(path):
    def unique(items):
        result = {}
        for key, value in items:
            require(key not in result, "Duplicate native report key")
            result[key] = value
        return result
    require(path.is_file() and path.stat().st_size <= 2**20, "Native report is absent or exceeds its bound")
    data = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique)
    require(type(data) is dict, "Native report must be an object")
    return data


def validate(path, expected):
    path = Path(path)
    require(type(expected) is dict and expected.get("schema") == "ps5-qwen-first-generation-binding-v1",
        "Independent first-generation binding is required")
    for key, lower, upper in (("pid", 1, 2**31-1), ("files", 1, 256),
                               ("bytes", 359235922432, 512 * 2**30)):
        require(integer(expected.get(key), lower, upper), "Invalid independent identity or complete footprint")
    for key, length in (("run_id", 32), ("candidate_SELF_sha256", 64), ("model_receipt_sha256", 64)):
        value = expected.get(key)
        require(type(value) is str and len(value) == length and all(c in "0123456789abcdef" for c in value),
            "Invalid independent run or digest binding")
    require(not Path(str(path) + ".failure").exists() and not Path(str(path) + ".fatal").exists(),
        "A native failure/fatal record prevents positive admission")
    result = read_record(path)
    def record(suffix, schema, fields):
        data = result if not suffix else read_record(Path(str(path) + suffix))
        require(data.get("schema") == schema, "Native report schema differs")
        require(type(data.get("pid")) is int and data["pid"] == expected["pid"], "Native owner differs")
        for key in fields:
            require(data.get(key) == expected[key] and type(data.get(key)) is type(expected[key]),
                "Native run/provenance differs from independent binding")
        return data
    common = ("run_id", "candidate_SELF_sha256", "model_receipt_sha256")
    record("", "ps5-qwen-plan-validation-result-v1", common)
    start = record(".first.start", "ps5-qwen-first-generation-start-v1", common)
    intent = record(".first.intent", "ps5-qwen-first-generation-intent-v1", ("run_id",))
    integrity = record(".integrity", "ps5-qwen-model-integrity-v1", ())
    mapping = record(".mapping", "ps5-qwen-model-virtual-source-admission-v1", ())
    memory = record(".memory", "ps5-qwen-memory-admission-v1", ())
    source = record(".source", "ps5-qwen-bounded-source-admission-v1", ())
    def exact(data, values):
        for key, value in values.items():
            require(type(data.get(key)) is type(value) and data[key] == value, "Native phase outcome differs: " + key)
    exact(start, dict(model_loaded=False, Vulkan_initialized=False))
    exact(intent, dict(context_tokens=256, maximum_prompt_tokens=64, maximum_output_tokens=32,
        maximum_generation_seconds=3600, enable_thinking=False))
    prompt = intent.get("rendered_prompt")
    require(type(prompt) is str and 0 < len(prompt.encode("utf-8")) <= 16384 and "\0" not in prompt,
        "Bounded original-template request is absent")
    exact(integrity, dict(files_verified=expected["files"], mapped_file_bytes=expected["bytes"],
        verified_file_bytes=expected["bytes"], maximum_verification_seconds=7200,
        all_SHA256_matched=True, model_loaded=False, Vulkan_initialized=False))
    require(number(integrity.get("verification_elapsed_ms")) and integrity["verification_elapsed_ms"] <= 7200000,
        "Whole-model verification deadline was not met")
    if integrity.get("verification_mode") == "prior_native_SHA_and_unchanged_sealed_identity":
        exact(integrity, dict(payload_SHA_computed_in_this_run=False, metadata_validation_deadline_seconds=60))
        require(integrity["verification_elapsed_ms"] <= 60000 and
            number(integrity.get("prior_native_verification_elapsed_ms")) and
            0 < integrity["prior_native_verification_elapsed_ms"] <= 7200000,
            "Prior native SHA or current sealed identity validation exceeded its deadline")
        for key in ("prior_native_integrity_report_sha256", "sealed_identity_snapshot_sha256"):
            value = integrity.get(key)
            require(type(value) is str and len(value) == 64 and all(c in "0123456789abcdef" for c in value),
                "Reused native integrity evidence is not identified")
    exact(mapping, dict(all_SHA256_matched=True, original_footprint_matched=True, mapped_files=expected["files"],
        mapped_file_bytes=expected["bytes"], completed_unmaps=expected["files"], model_loaded=False,
        Vulkan_initialized=False, GPU_compute_calls=0, mapped_payload_reads=0, resident_set_qualified=False,
        file_backed_model_mmap_calls=0, source_virtual_protection="none",
        state="virtual_sources_completed_before_backend"))
    exact(memory, dict(model_loaded=False, resident_set_qualified=False))
    exact(source, dict(direct_read_preflight_passed=True, maximum_window_bytes=8 << 20,
        maximum_open_handles=8, mapped_source_upload_dereferences_enabled=False,
        CPU_matrix_fallback_enabled=False, maximum_CPU_workspace_bytes=16 << 20,
        bounded_CPU_rows_enabled=True, CPU_source_pointer_dereferences_enabled=False,
        model_loaded=False, Vulkan_initialized=False))
    exact(memory, dict(device_weights_bytes=8755105280, mapped_file_bytes=expected["bytes"],
        planned_resident_headroom_bytes=12110548480, CPU_budget_bytes=512 << 20,
        maximum_explicitly_addressed_CPU_model_page_bytes=160432128,
        maximum_CPU_heap_bytes=(512 << 20) - 160432128,
        maximum_postload_device_buffer_bytes=512 << 20,
        maximum_aggregate_postload_device_buffer_bytes=1792 << 20))
    require(integer(memory.get("driver_free_bytes"), 12110548480, 2**63-1) and
        integer(memory.get("Direct_largest_available_bytes"), 12110548480, 2**63-1) and
        integer(memory.get("OS_free_bytes"), 768 << 20, 2**63-1), "Fresh memory observations do not admit the bounded model")
    alignment = memory.get("device_buffer_alignment_bytes")
    limit = memory.get("device_buffer_batch_limit_bytes")
    require(integer(alignment, 1, 65536) and not alignment & (alignment-1) and
        integer(limit, 1, 2**31) and limit >= (1271398400 + alignment-1) // alignment * alignment,
        "Resident buffer alignment/limit is invalid")
    exact(result, dict(state="completed_waiting_for_ordinary_close", request_reset_completed=True,
        GPU_completion_and_retirement_passed=True, model_resources_released_after_completion=True,
        model_loaded=False, full_model_inference_executed=True, answer_quality_qualified=False,
        native_display_started=True, external_requests_accepted=2, arithmetic_smoke_passed=True,
        source_IO_completed=True,
        driver_revision="872cc1264ad8ba5d6b888b092968fa5858a38c58", profile="cumulative-idle",
        native_archive_sha256="b57fe26e969940d147be05c1ffae830503d4865877281dffe03af32328f49925"))
    require(integer(result.get("source_read_bytes"), 8755105280, 2**63-1) and
        integer(result.get("source_read_chunks"), 1, 2**63-1) and
        integer(result.get("maximum_source_read_bytes"), 1, 8 << 20), "Missing bounded completed source-I/O evidence")
    exact(result, dict(postload_device_live_bytes=0, untracked_libc_heap_fallbacks=0))
    require(integer(result.get("postload_device_peak_bytes"), 1, 1792 << 20) and
        integer(result.get("postload_device_allocations"), 1, 2**31-1) and
        integer(result.get("CPU_heap_peak_bytes"), 1, (512 << 20) - 160432128),
        "The completed device/CPU allocation peaks exceed their admitted budgets")
    ids, output, metrics = result.get("token_ids"), result.get("output_bytes"), result.get("metrics")
    require(type(ids) is list and len(ids) <= 32 and all(integer(x, 0, 2**31-1) for x in ids), "Invalid token IDs")
    require(type(output) is list and len(output) <= 65536 and all(integer(x, 0, 255) for x in output), "Invalid output bytes")
    require(type(metrics) is dict and integer(metrics.get("prompt_tokens"), 1, 64), "Invalid prompt count")
    require("TTFT_ms" in metrics and "decode_tokens_per_second" in metrics, "Explicit optional timing fields are required")
    require(type(metrics.get("generated_tokens")) is int and metrics["generated_tokens"] == len(ids), "Token count differs")
    require(number(metrics.get("total_ms")) and metrics["total_ms"] <= 3600000 and
        number(metrics.get("prefill_ms")) and metrics["prefill_ms"] <= metrics["total_ms"], "Invalid phase timing")
    reason = result.get("stop_reason")
    require((reason == "output_token_limit" and len(ids) == 32) or
            (reason == "end_of_generation" and len(ids) < 32), "Unproven generation termination")
    observed = sorted(path.parent.glob(path.name + ".first.token-*"))
    wanted = {Path(str(path) + ".first.token-" + str(i)) for i in range(1, len(ids) + 1)}
    require(set(observed) == wanted, "Missing or additional token records")
    reconstructed, times = [], []
    for index, token_id in enumerate(ids, 1):
        data = read_record(Path(str(path) + ".first.token-" + str(index)))
        exact(data, dict(schema="ps5-qwen-first-generation-token-v1", run_id=expected["run_id"], ordinal=index, token_id=token_id))
        piece = data.get("piece_bytes")
        require(type(piece) is list and all(integer(x, 0, 255) for x in piece), "Invalid persisted token bytes")
        reconstructed.extend(piece)
        elapsed = data.get("elapsed_ms")
        require(number(elapsed) and (not times or elapsed >= times[-1]) and elapsed <= metrics["total_ms"],
            "Invalid persisted token timing")
        times.append(elapsed)
    require(reconstructed == output, "Output differs from durable token records")
    require(type(result.get("text_generation_observed")) is bool and result["text_generation_observed"] == bool(output),
        "Text-generation claim differs from actual bytes")
    expected_ttft = times[0] if times else None
    ttft = metrics.get("TTFT_ms")
    require((ttft is None and expected_ttft is None) or
        (number(ttft) and expected_ttft is not None and abs(ttft - expected_ttft) < 1e-6), "TTFT differs")
    require(not times or times[0] >= metrics["prefill_ms"], "First token precedes prefill completion")
    expected_speed = (len(ids)-1) * 1000 / (times[-1]-times[0]) if len(times) >= 2 and times[-1] > times[0] else None
    speed = metrics.get("decode_tokens_per_second")
    require((speed is None and expected_speed is None) or
        (number(speed) and expected_speed is not None and math.isclose(speed, expected_speed, rel_tol=1e-9)), "Decode rate differs")
    raw = bytes(output)
    try:
        text, valid_utf8 = raw.decode("utf-8"), True
    except UnicodeDecodeError:
        text, valid_utf8 = raw.decode("utf-8", errors="replace"), False
    require(valid_utf8 and text.strip(" \t\r\n") == "4", "The original-model arithmetic smoke answer differs")
    first = record(".first.result", "ps5-qwen-first-request-result-v1", ("run_id",))
    exact(first, dict(model_loaded=True, request_reset_completed=True))
    for key in ("stop_reason", "token_ids", "output_bytes", "metrics"):
        require(first.get(key) == result[key], "First-request terminal record differs")
    ready = record(".demo.ready", "ps5-qwen-bounded-demo-ready-v1", ("run_id",))
    exact(ready, dict(maximum_requests=2, context_tokens=256, maximum_output_tokens=32,
        prompt="Count from 1 to 8, separated by commas. Reply with only the sequence.", listener_bind="0.0.0.0", model_loaded=True, native_display_started=True))
    cold = record(".demo.cache", "ps5-qwen-demo-cold-cache-admission-v1", ("run_id",))
    exact(cold, dict(context_recreated_after_positive_completion=True, expert_cache_initially_empty=True,
        model_reloaded=False, model_loaded=True, file_pages_and_pipelines_cold=False))
    demo = record(".demo.result", "ps5-qwen-bounded-demo-result-v1", ("run_id",))
    require(result.get("demonstration") == demo, "The demonstration result differs from its durable record")
    exact(demo, dict(external_requests_accepted=2, external_requests_completed=2,
        all_monitor_assets_requested=True, finish_acknowledgement_delivered=True, listener_stopped=True,
        model_loaded=True))
    require(integer(demo.get("status_observations"), 2, 2**31-1) and
        integer(demo.get("observed_clock_advance_ms"), 1000, 3*60*60*1000), "Missing passive monitor clock observations")
    require(type(demo.get("requests")) is list and len(demo["requests"]) == 2, "Two measured external requests are required")
    measured = []
    for ordinal in (1, 2):
        prefix = ".demo" + str(ordinal)
        request_id = expected["run_id"] + "-" + str(ordinal)
        intent = record(prefix + ".intent", "ps5-qwen-demo-request-intent-v1", ("run_id",))
        exact(intent, dict(id=request_id, ordinal=ordinal, context_tokens=256, maximum_prompt_tokens=64,
            maximum_output_tokens=32, maximum_generation_seconds=3600, enable_thinking=False,
            prompt="Count from 1 to 8, separated by commas. Reply with only the sequence."))
        rendered = intent.get("rendered_prompt")
        require(type(rendered) is str and 0 < len(rendered.encode("utf-8")) <= 16384 and "\0" not in rendered,
            "The original-template external request is absent")
        terminal = record(prefix + ".result", "ps5-qwen-demo-request-result-v1", ("run_id",))
        require(terminal == demo["requests"][ordinal - 1], "An external request terminal differs")
        exact(terminal, dict(id=request_id, ordinal=ordinal, request_reset_completed=True,
            GPU_completion_and_retirement_passed=True, model_loaded=True,
            cache_condition="empty expert cache" if ordinal == 1 else "retained expert cache"))
        token_ids, pieces, values = terminal.get("token_ids"), terminal.get("output_bytes"), terminal.get("metrics")
        require(type(token_ids) is list and 2 <= len(token_ids) <= 32 and all(integer(t, 0, 2**31-1) for t in token_ids),
            "The external token sequence is not measurable")
        require(type(pieces) is list and 0 < len(pieces) <= 65536 and all(integer(b, 0, 255) for b in pieces),
            "Invalid external output bytes")
        require(type(values) is dict and integer(values.get("prompt_tokens"), 1, 64) and
            type(values.get("generated_tokens")) is int and values["generated_tokens"] == len(token_ids),
            "Invalid external token counts")
        require(number(values.get("total_ms")) and values["total_ms"] <= 3600000 and
            number(values.get("prefill_ms")) and values["prefill_ms"] <= values["total_ms"], "Invalid external timings")
        stop = terminal.get("stop_reason")
        require((stop == "output_token_limit" and len(token_ids) == 32) or
            (stop == "end_of_generation" and len(token_ids) < 32), "Unproven external request completion")
        observed = set(path.parent.glob(path.name + prefix + ".token-*"))
        wanted = {Path(str(path) + prefix + ".token-" + str(i)) for i in range(1, len(token_ids) + 1)}
        require(observed == wanted, "Missing or extra external token records")
        reconstructed, stamps = [], []
        for i, token_id in enumerate(token_ids, 1):
            event = read_record(Path(str(path) + prefix + ".token-" + str(i)))
            exact(event, dict(id=request_id, type="token", state="generating", ordinal=i, token_id=token_id, error=0))
            piece, elapsed = event.get("piece_bytes"), event.get("elapsed_ms")
            require(type(piece) is list and all(integer(b, 0, 255) for b in piece), "Invalid external token bytes")
            require(number(elapsed) and (not stamps or elapsed >= stamps[-1]) and elapsed <= values["total_ms"],
                "External token timestamps are inconsistent")
            reconstructed.extend(piece); stamps.append(elapsed)
        require(reconstructed == pieces, "External output differs from durable token pieces")
        require(bytes(byte for byte in pieces if byte not in b" \t\r\n") == b"1,2,3,4,5,6,7,8",
            "The external response is an incomplete or incorrect counting sequence")
        require(number(values.get("ttft_ms")) and abs(values["ttft_ms"] - stamps[0]) < 1e-6 and
            stamps[0] >= values["prefill_ms"] and stamps[-1] > stamps[0], "External TTFT or decode interval differs")
        speed = (len(token_ids) - 1) * 1000 / (stamps[-1] - stamps[0])
        require(number(values.get("decode_tokens_per_second")) and
            math.isclose(values["decode_tokens_per_second"], speed, rel_tol=1e-9), "External decode rate differs")
        frame = record(prefix + ".display.json", "ps5-qwen-displayed-frame-v1", ("run_id",))
        exact(frame, dict(id=request_id, width=1920, height=1080, BMP_bytes=8294454,
            generated_tokens=len(token_ids), clock_calibrated=True, model_loaded=True,
            positive_VideoOut_completion=True, evidence="CPU raster after the matching completed VideoOut flip"))
        require(integer(frame.get("epoch_ms"), 946684800000, 4102444800000) and
            frame.get("TTFT_ms") == values["ttft_ms"] and frame.get("decode_tokens_per_second") == values["decode_tokens_per_second"],
            "The completed native frame does not contain the measured request/time")
        bitmap = Path(str(path) + prefix + ".display.bmp")
        require(bitmap.is_file() and bitmap.stat().st_size == 8294454, "The completed scanout-source bitmap is missing")
        with bitmap.open("rb") as image:
            header = image.read(54)
        require(header[:2] == b"BM" and struct.unpack_from("<I", header, 2)[0] == 8294454 and
            struct.unpack_from("<III", header, 10) == (54, 40, 1920) and
            struct.unpack_from("<IHH", header, 22) == (1080, 1, 32), "The completed scanout-source bitmap layout differs")
        measured.append(dict(id=request_id, text=bytes(pieces).decode("utf-8", errors="replace"), metrics=values))
    return dict(state="native_plan_requests_completed", stop_reason=reason, text=text,
        output_is_complete_UTF8=valid_utf8, metrics=metrics, answer_quality_qualified=False,
        external_requests=measured, native_display_started=True,
        ordinary_close_and_original_restoration_verified=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--binding", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(validate(args.result, read_record(args.binding)), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
