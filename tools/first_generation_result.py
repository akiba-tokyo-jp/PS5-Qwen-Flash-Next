#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Independently validate downloaded first-generation records; never access a PS5.

A positive generation result is separate from ordinary-close/restoration evidence.
Missing, inconsistent or failed records never establish completion.
"""
import argparse
import json
import math
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
    record("", "ps5-qwen-first-generation-result-v1", common)
    start = record(".first.start", "ps5-qwen-first-generation-start-v1", common)
    intent = record(".first.intent", "ps5-qwen-first-generation-intent-v1", ("run_id",))
    integrity = record(".integrity", "ps5-qwen-model-integrity-v1", ())
    mapping = record(".mapping", "ps5-qwen-model-mapping-admission-v1", ())
    memory = record(".memory", "ps5-qwen-memory-admission-v1", ())
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
    exact(mapping, dict(all_SHA256_matched=True, original_footprint_matched=True, mapped_files=expected["files"],
        mapped_file_bytes=expected["bytes"], completed_unmaps=expected["files"], model_loaded=False,
        Vulkan_initialized=False, GPU_compute_calls=0, mapped_payload_reads=0, resident_set_qualified=False,
        state="mapping_completed_before_backend"))
    exact(memory, dict(model_loaded=False, resident_set_qualified=False))
    exact(memory, dict(device_weights_bytes=8755105280, mapped_file_bytes=expected["bytes"],
        planned_resident_headroom_bytes=11976330752))
    alignment = memory.get("device_buffer_alignment_bytes")
    limit = memory.get("device_buffer_batch_limit_bytes")
    require(integer(alignment, 1, 65536) and not alignment & (alignment-1) and
        integer(limit, 1, 2**31) and limit >= (1271398400 + alignment-1) // alignment * alignment,
        "Resident buffer alignment/limit is invalid")
    exact(result, dict(state="completed_waiting_for_ordinary_close", request_reset_completed=True,
        GPU_completion_and_retirement_passed=True, model_resources_released_after_completion=True,
        model_loaded=False, full_model_inference_executed=True, answer_quality_qualified=False,
        native_display_started=False, external_requests_accepted=0,
        driver_revision="872cc1264ad8ba5d6b888b092968fa5858a38c58", profile="cumulative-idle",
        native_archive_sha256="b57fe26e969940d147be05c1ffae830503d4865877281dffe03af32328f49925"))
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
    return dict(state="generation_completed", stop_reason=reason, text=text,
        output_is_complete_UTF8=valid_utf8, metrics=metrics, answer_quality_qualified=False,
        ordinary_close_and_original_restoration_verified=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--binding", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(validate(args.result, read_record(args.binding)), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
