#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Review closed native matched cohorts without running a model or console call."""
import argparse
import hashlib
import json
import math
import statistics
import struct
from pathlib import Path


def load(path):
    return json.loads(Path(path).read_text())


def capture(path):
    path = Path(path)
    return dict(path=str(path), bytes=path.stat().st_size,
                sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def paired(control, candidate, higher_is_better):
    if len(control) != 2 or len(candidate) != 2:
        raise ValueError("Two observations in each ABBA role are required")
    if not all(math.isfinite(v) and v > 0 for v in control + candidate):
        raise ValueError("Every timing or speed must be finite and positive")
    ratios = [b / a if higher_is_better else a / b
              for a, b in zip(control, candidate)]
    separated = min(candidate) > max(control) if higher_is_better else max(candidate) < min(control)
    return dict(control=control, candidate=candidate,
                reverse_pair_ratios=ratios,
                mean_ratio=statistics.mean(candidate) / statistics.mean(control)
                if higher_is_better else statistics.mean(control) / statistics.mean(candidate),
                observed_control_range=max(control) - min(control),
                both_orders_faster=all(v > 1 for v in ratios),
                candidate_range_clear_of_observed_control_range=separated,
                reproducible_in_this_finite_cohort=all(v > 1 for v in ratios) and separated)


def metric(row, key):
    return row.get("metrics", row)[key]


def closed_case(cache, number, request_count):
    case = cache / f"hardware-first-generation-{number}"
    restored = load(case / "restored-complete.private.json")
    report = load(case / "native-model-terminal.private.json")
    binding = load(case / "case-inputs.private.json")["binding"]
    if not (restored["completed"] and restored["CPU_title_normally_closed"] and
            restored["full_native_readback_SHA256_identity_EOF_verified"] and
            report["completed"] and report["run_id"] == binding["run_id"] and
            report["candidate_SELF_sha256"] == binding["candidate_SELF_sha256"] and
            report["model_receipt_sha256"] == binding["model_receipt_sha256"] and
            report["all_model_source_device_owners_positively_retired"] and
            report["device_ledger_live_bytes"] == 0 and len(report["requests"]) == request_count):
        raise ValueError("A fully bound, retired and restored native cohort is required")
    reference = report["requests"][0]
    for ordinal, row in enumerate(report["requests"]):
        if not (row["ordinal"] == ordinal and row["request_reset_completed"] and
                row["token_ids"] == reference["token_ids"] and row["output_bytes"] == reference["output_bytes"]):
            raise ValueError("Native original tokens/bytes or request reset differ")
    return case, report


def arms(rows, controls, candidates):
    return dict(decode=paired([metric(rows[i], "decode_tokens_per_second") for i in controls],
                              [metric(rows[i], "decode_tokens_per_second") for i in candidates], True),
                total=paired([metric(rows[i], "total_ms") for i in controls],
                             [metric(rows[i], "total_ms") for i in candidates], False),
                prefill=paired([metric(rows[i], "prefill_ms") for i in controls],
                               [metric(rows[i], "prefill_ms") for i in candidates], False))


def review_combined(cache, number):
    case, report = closed_case(cache, number, 10)
    if report["total_requests"] != 19 or not report["forced_rejection_and_full_F32_restore_passed"]:
        raise ValueError("Complete combined cohort and forced rejection proof required")
    rows = report["requests"]
    rejection = rows[9]
    if not (rejection["speculation"]["attempts"] == rejection["speculation"]["rejected"] == 1 and
            rejection["speculation"]["accepted"] == 0 and rejection["full_F32_logit_rows_compared"] == 23):
        raise ValueError("The controlled rejected continuation did not fully complete")
    prediction = arms(rows, (1, 4), (2, 3))
    speculation = arms(rows, (5, 8), (6, 7))
    prefix = report["prefix_requests"]
    if len(prefix) != 9:
        raise ValueError("All nine native prefix requests required")
    for ordinal, row in enumerate(prefix):
        if (row["token_ids"] != rows[0]["token_ids"] or row["output_bytes"] != rows[0]["output_bytes"] or
                not row["request_reset_completed"] or (ordinal and row["full_F32_logit_rows_compared"] != 23)):
            raise ValueError("Prefix original continuation differs")
    prefix_pair = paired([sum(metric(prefix[i], "total_ms") for i in pair) for pair in ((1, 2), (7, 8))],
                         [sum(metric(prefix[i], "total_ms") for i in pair) for pair in ((3, 4), (5, 6))], False)
    prefix_second = arms(prefix, (2, 8), (4, 6))
    return dict(case=number, native_requests=19, prediction=prediction, speculation=speculation,
                prediction_counters=[rows[i]["predictive"] for i in (2, 3)],
                speculation_counters=[rows[i]["speculation"] for i in (6, 7)],
                forced_rejection=rejection["speculation"],
                forced_rejection_F32_rows=23,
                maximum_rejection_F32_error=rejection["maximum_absolute_logit_error"],
                prefix_pair_total=prefix_pair, prefix_second=prefix_second,
                native_evidence=capture(case / "native-model-terminal.private.json"))


def review_cache(cache, numbers):
    if len(numbers) != 4:
        raise ValueError("The complete A53/B128/B128/A53 cohort is required")
    cases = [closed_case(cache, n, 3) for n in numbers]
    first_case, first = cases[0]
    first_manifest = load(first_case / "native-warmup-F32.private.json")
    first_routes = load(first_case / "native-arm0.routes.private.json")["records"]
    maximum_error = 0.0
    for index, (case, report) in enumerate(cases):
        slots = 53 if index in (0, 3) else 128
        if report["active_cache_slots"] != slots:
            raise ValueError("Native cache ABBA geometry differs")
        manifest = load(case / "native-warmup-F32.private.json")
        if manifest["rows"] != 23 or manifest["columns"] != first_manifest["columns"]:
            raise ValueError("Cross-cache F32 geometry differs")
        for ordinal in range(3):
            routes = load(case / f"native-arm{ordinal}.routes.private.json")
            if not routes["complete"] or routes["records"] != first_routes:
                raise ValueError("Cross-cache original expert selections differ")
            row = report["requests"][ordinal]
            if row["token_ids"] != first["requests"][0]["token_ids"] or row["output_bytes"] != first["requests"][0]["output_bytes"]:
                raise ValueError("Cross-cache original tokens/bytes differ")
        for ordinal in range(23):
            reference = (first_case / f"native-warmup-F32-row-{ordinal}.private.f32").read_bytes()
            actual = (case / f"native-warmup-F32-row-{ordinal}.private.f32").read_bytes()
            if len(actual) != len(reference) or len(actual) != manifest["columns"] * 4:
                raise ValueError("Incomplete cross-cache F32 row")
            for (a,), (b,) in zip(struct.iter_unpack("<f", actual), struct.iter_unpack("<f", reference)):
                error = abs(a - b)
                if not math.isfinite(a) or not math.isfinite(b) or error > 1e-5 + 1e-5 * abs(b):
                    raise ValueError("Cross-cache full F32 reference differs")
                maximum_error = max(maximum_error, error)
    def means(key):
        return [statistics.mean(metric(r["requests"][i], key) for i in (1, 2)) for _, r in cases]
    speeds, totals = means("decode_tokens_per_second"), means("total_ms")
    return dict(cases=numbers, native_requests=12, cross_cache_F32_rows=92,
                maximum_absolute_F32_error=maximum_error, all_expert_selections_exact=True,
                decode=paired([speeds[i] for i in (0, 3)], [speeds[i] for i in (1, 2)], True),
                total=paired([totals[i] for i in (0, 3)], [totals[i] for i in (1, 2)], False),
                native_evidence=[capture(c / "native-model-terminal.private.json") for c, _ in cases])


def review_refill(cache, number):
    case, report = closed_case(cache, number, 5)
    for ordinal, row in enumerate(report["requests"]):
        stats = row["six_demand"]
        enabled = ordinal in (2, 3)
        if not (stats["enabled"] == enabled and (stats["batches"] > 0) == enabled and
                stats["reads"] == 6 * stats["batches"] and stats["logical_bytes"] == stats["reads"] * 3276800):
            raise ValueError("Actual-model six-demand batch/read/byte conservation differs")
    return dict(case=number, native_requests=5, comparison=arms(report["requests"], (1, 4), (2, 3)),
                six_demand=[r["six_demand"] for r in report["requests"]],
                native_evidence=capture(case / "native-model-terminal.private.json"))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cache", type=Path, required=True)
    p.add_argument("--kind", choices=("combined", "cache", "refill"), required=True)
    p.add_argument("--cases", type=int, nargs="+", required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    if a.kind == "cache":
        result = review_cache(a.cache, a.cases)
    else:
        if len(a.cases) != 1:
            raise ValueError("Exactly one native lifetime required")
        result = (review_combined if a.kind == "combined" else review_refill)(a.cache, a.cases[0])
    result.update(schema="ps5-qwen-closed-resident-review-v1", kind=a.kind,
                  only_completed_native_evidence_used=True, finite_repetitions_not_universal_bound=True,
                  console_calls=0, host_model_inference=False, production_adopted=False)
    with a.out.open("x", encoding="utf-8", newline="\n") as file:
        json.dump(result, file, indent=2)
        file.write("\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
