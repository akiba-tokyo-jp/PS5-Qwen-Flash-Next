#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Separate request and byte-volume effects using completed PS5 evidence only."""
from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from pathlib import Path


SELF = "80c28a95e993458c54b5fbf73fe59accde17dd8302dd49a9aeecf367e617739c"
MIB = 1 << 20


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def fingerprint(path):
    return {"bytes": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def affine(points):
    """Return a descriptive fit, not a physical SSD service-time measurement."""
    xbar = statistics.mean(x for x, _ in points)
    ybar = statistics.mean(y for _, y in points)
    slope = sum((x-xbar)*(y-ybar) for x, y in points) / sum((x-xbar)**2 for x, _ in points)
    intercept = ybar-slope*xbar
    ss_total = sum((y-ybar)**2 for _, y in points)
    ss_error = sum((y-(intercept+slope*x))**2 for x, y in points)
    require(slope > 0 and intercept > 0, "A positive descriptive size/time fit is required")
    return dict(fixed_ms=intercept, ms_per_MiB=slope, r_squared=1-ss_error/ss_total,
                effective_size_dependent_GB_s=MIB/(slope*1e6))


def analyze(data, repository):
    source = data/"source-schedule-probe-436"
    log = source/"probe-result.private.log"
    completion = load(source/"complete.private.json")
    require(all(completion.get(k) is True for k in (
        "CPU_probe_terminal_success", "same_boot_services", "reservation_unchanged",
        "original_SELF_never_modified")), "The preserved CPU cohort must have positively completed")
    require(completion["native_owners"] == completion["GPU_calls"] == completion["title_launches"] == 0,
            "Unexpected CPU-cohort scope")
    require(fingerprint(log) == {k: completion["raw_result"][k] for k in ("bytes", "sha256")},
            "The preserved raw CPU evidence changed")
    manifest = load(data/"build/source-schedule-probe-435/manifest.private.json")
    recipes = manifest["boundary_cases"]
    require(recipes[1] == [0, 0, 64*MIB, 0, 3, 4*MIB, 4*MIB] and
            recipes[2] == [0, 0, 64*MIB, 0, 3, 8*MIB, 8*MIB] and
            recipes[5] == [0, 0, 100*MIB, 0, 3, 6569984, 16384],
            "Size controls must retain the original descriptor, offsets, strides and serial strategy")
    rows = [dict((k, int(v)) for k, v in (part.split("=", 1) for part in line.split()[1:]))
            for line in log.read_text(encoding="ascii").splitlines() if line.startswith("PAIR ")]
    require(len(rows) == 768 and len({(r["round"], r["mode"], r["pair"]) for r in rows}) == 768,
            "Expected the original three complete 16-mode/16-pair rounds")
    published = load(repository/"docs/source-schedule-cpu-20261024.json")
    selected = {}
    for mode in (1, 2, 4, 5):
        group = [r for r in rows if r["mode"] == mode]
        require(len(group) == 48 and all(r["parallel"] == 0 and r["e0"] == r["e1"] == 0 for r in group),
                "The size/count controls must be serial and completed")
        record = published["modes"][mode]
        require(all(r["bytes"] == record["bytes_per_pair"] and r["calls"] == record["physical_read_calls"]
                    for r in group), "Control byte/count scope changed")
        mean = statistics.mean(r["wall_ns"] for r in group)/1e6
        require(abs(mean-record["mean_ms"]) < 1e-10, "Raw and published controls disagree")
        selected[mode] = dict(name=record["name"], observations=len(group), bytes=record["bytes_per_pair"],
                              calls=record["physical_read_calls"], mean_ms=mean,
                              round_mean_ms=[statistics.mean(r["wall_ns"] for r in group if r["round"] == i)/1e6
                                             for i in range(3)])
    fit = affine([(selected[i]["bytes"]/MIB, selected[i]["mean_ms"]) for i in (1, 5, 2)])
    fits = [affine([(selected[i]["bytes"]/MIB, selected[i]["round_mean_ms"][j]) for i in (1, 5, 2)])
            for j in range(3)]
    fit["round_fixed_ms"] = [f["fixed_ms"] for f in fits]
    fit["round_ms_per_MiB"] = [f["ms_per_MiB"] for f in fits]
    fit["estimated_size_dependent_fraction_at_4_MiB"] = 1-fit["fixed_ms"]/selected[1]["mean_ms"]
    fit["estimated_size_dependent_fraction_at_8_MiB"] = 1-fit["fixed_ms"]/selected[2]["mean_ms"]
    fit["scope"] = "Descriptive three-size serial CPU-helper fit; not a production latency decomposition"

    # Mode 1's first 16 extents cover exactly the same file bytes as mode 2's
    # first eight extents. Match addresses, not just nominal byte totals.
    exact_rounds = []
    for index in range(3):
        r4 = {r["pair"]: r for r in rows if r["mode"] == 1 and r["round"] == index}
        r8 = {r["pair"]: r for r in rows if r["mode"] == 2 and r["round"] == index}
        require(set(r4) == set(r8) == set(range(16)), "All original extent indexes are required")
        pairs = []
        for pair in range(8):
            start = recipes[2][2]+pair*recipes[2][6]
            require(start == recipes[1][2]+2*pair*recipes[1][6] and
                    start+4*MIB == recipes[1][2]+(2*pair+1)*recipes[1][6],
                    "The two four-MiB reads must exactly tile the one eight-MiB read")
            split_ms = (r4[2*pair]["wall_ns"]+r4[2*pair+1]["wall_ns"])/1e6
            whole_ms = r8[pair]["wall_ns"]/1e6
            pairs.append((split_ms, whole_ms))
        split_ms, whole_ms = (statistics.mean(p[i] for p in pairs) for i in (0, 1))
        fixed_ms = split_ms-whole_ms
        require(0 < fixed_ms < whole_ms, "Matched extents must support a positive secondary request cost")
        exact_rounds.append(dict(round=index, identical_extent_pairs=8, bytes_per_extent=8*MIB,
            two_4_MiB_calls_ms=split_ms, one_8_MiB_call_ms=whole_ms,
            elapsed_reduction_fraction=1-whole_ms/split_ms,
            affine_per_request_ms=fixed_ms,
            affine_size_dependent_fraction_at_4_MiB=1-2*fixed_ms/split_ms,
            affine_size_dependent_fraction_at_8_MiB=1-fixed_ms/whole_ms))

    case = data/"hardware-first-generation-7080"
    terminal = load(case/"native-model-terminal.private.json")
    require(terminal["candidate_SELF_sha256"] == SELF and terminal["GPU_completion_and_retirement_passed"] and
            terminal["model_resources_released_after_completion"] and terminal["source_IO_completed"] and
            terminal["source_pipeline_worker_stopped"] and terminal["model_loaded"] is False,
            "Expected the positively retired selected normal application")
    deployment = load(data/"qualified-cache134-production-7420/production-complete.private.json")
    require(deployment["production_SELF"]["sha256"] == SELF and deployment["production_deployment_completed"] and
            deployment["production_SELF_full_readback_verified"] and deployment["installed_configuration_full_readback_verified"],
            "The analyzed SELF must match the verified production placement")
    monitor = load(case/"native-plan-observation/native-result.private.json.cache128-monitor")
    require(monitor["active_cache_slots"] == 134 and monitor["adaptive_profile_selected"] is False and
            monitor["all_model_source_device_owners_retired"] and monitor["completed"],
            "Expected the qualified normal 134-slot profile, not the adaptive diagnostic")
    observations = []
    for request in (1, 2):
        prefix = case/"native-plan-observation"/"native-result.private.json"
        tokens = [load(Path(str(prefix)+f".demo{request}.token-{i}")) for i in range(1, 23)]
        require(all(t["ordinal"] == i and t["metrics"]["generated_tokens"] == i and t["error"] == 0
                    and t["id"] == tokens[0]["id"] for i, t in enumerate(tokens, 1)),
                "All ordered, successful token records are required")
        expected = terminal["demonstration"]["requests"][request-1]
        require([t["token_id"] for t in tokens] == expected["token_ids"], "Token stream differs from completed plan")
        for before, after in zip(tokens, tokens[1:]):
            require(after["elapsed_ms"] >= before["elapsed_ms"] and
                    all(after["completed_performance"][k] >= v for k, v in before["completed_performance"].items()),
                    "Cumulative counters or token time reversed")
        first, last = tokens[0], tokens[-1]
        delta = {k: last["completed_performance"][k]-v for k, v in first["completed_performance"].items()}
        require(0 < delta["source_read_ns"] < delta["process_ns"] and delta["source_physical_read_calls"] > 0,
                "Source waiting must remain nested in process wall time")
        performance = load(Path(str(prefix)+f".demo{request}.performance"))
        require(performance["source_read_ns_is_producer_wait_time"] and performance["worker_times_overlap_consumers"],
                "Overlapping read counters must not be interpreted as additive device time")
        actual_s = (last["elapsed_ms"]-first["elapsed_ms"])/1000
        observations.append(dict(request=request, accepted_decode_transitions=21,
            causal_width_two_enabled=request == 2, prefill_excluded=True, final_EOS_work_excluded=True,
            decode_tok_s=21/actual_s, elapsed_s=actual_s, process_s=delta["process_ns"]/1e9,
            source_wait_s=delta["source_read_ns"]/1e9,
            source_wait_fraction_of_process=delta["source_read_ns"]/delta["process_ns"],
            physical_read_bytes=delta["source_physical_read_bytes"],
            physical_read_calls=delta["source_physical_read_calls"],
            physical_GB_per_accepted_token=delta["source_physical_read_bytes"]/21/1e9,
            physical_calls_per_accepted_token=delta["source_physical_read_calls"]/21,
            mean_physical_request_MiB=delta["source_physical_read_bytes"]/delta["source_physical_read_calls"]/MIB,
            effective_physical_GB_per_source_wait_s=delta["source_physical_read_bytes"]/delta["source_read_ns"] ))
    return dict(schema="ps5-qwen-read-latency-attribution-v1", date="2026-10-29",
        method="Reanalysis of completed physical measurements; no new console operation",
        new_console_operations=0, production_changed=False, quantization=False, CI_runs=0,
        selected_production_SELF_SHA256=SELF,
        evidence_cases=dict(size_and_request_controls=436, normal_application=7080, production_placement=7420),
        single_request_controls=[selected[i] for i in (1, 5, 2)],
        exact_extent_request_count_control=dict(identical_files_and_byte_ranges=True,
            rounds=exact_rounds, total_identical_extent_pairs=24,
            comparison="Two 4-MiB serial calls versus one 8-MiB call at exactly the same source range",
            affine_assumption="T = N * fixed_request_cost + bytes * size_cost; descriptive, not device-only service time"),
        auxiliary_different_extent_comparison=dict(two_calls=selected[4], one_call=selected[5],
            elapsed_reduction_fraction=1-selected[5]["mean_ms"]/selected[4]["mean_ms"],
            byte_reduction_fraction=1-selected[5]["bytes"]/selected[4]["bytes"],
            identical_byte_ranges=False, pure_request_count_intervention=False),
        descriptive_size_time_fit=fit, current_production_decode=observations,
        conclusion="Byte-volume-dependent source delivery is the dominant supported explanation; fixed per-request overhead is secondary",
        limitations=["No isolated SSD controller or NAND service time was measured",
            "Byte-proportional filesystem, DMA and kernel work are included in the size-dependent term",
            "Serial helper controls use preserved historical extents; their fixed term is not a current application percentage",
            "Two application requests establish this fixed counting-workload scope, not all reasoning workloads",
            "Worker times overlap; do not add them or divide producer wait by physical calls as device latency"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.data_root, Path(__file__).resolve().parents[1])
    args.output.write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"completed": True, "new_console_operations": 0,
        "fixed_ms": result["descriptive_size_time_fit"]["fixed_ms"],
        "ms_per_MiB": result["descriptive_size_time_fit"]["ms_per_MiB"],
        "decode": result["current_production_decode"]}, indent=2))


if __name__ == "__main__":
    main()
