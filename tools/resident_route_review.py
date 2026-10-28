#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compare original expert selections across different native batch widths."""


def token_streams(report):
    if not (report.get("complete") is True and report.get("layers_per_process") == 48 and
            report.get("experts") == 512 and report.get("experts_per_token") == 10 and
            report.get("all_existing_downloads_and_synchronizations_returned") is True and
            report.get("additional_GPU_downloads") == 0):
        raise ValueError("Complete original native route capture required")
    records = report["records"]
    if not records or len(records) > 4608 or len(records) != 48 * report["process_calls"]:
        raise ValueError("Native process and route counts differ")
    streams = [[] for _ in range(48)]
    for start in range(0, len(records), 48):
        group = records[start:start + 48]
        if sorted(row["layer"] for row in group) != list(range(48)):
            raise ValueError("Each completed process must cover all original layers once")
        width = group[0]["tokens"]
        if type(width) is not int or not 1 <= width <= 4:
            raise ValueError("Original bounded native batch width required")
        for row in group:
            ids = row["ids"]
            if (row["tokens"] != width or len(ids) != 10 * width or
                    any(type(expert) is not int or not 0 <= expert < 512 for expert in ids)):
                raise ValueError("Native original expert geometry differs")
            streams[row["layer"]].extend(tuple(ids[i:i + 10]) for i in range(0, len(ids), 10))
    if sum(len(stream) * 10 for stream in streams) != report["selected_indices"]:
        raise ValueError("Selected expert accounting differs")
    return streams


def require_same_tokens(reference, actual, skipped_reference_tokens=0):
    if type(skipped_reference_tokens) is not int or skipped_reference_tokens < 0:
        raise ValueError("A nonnegative whole-token prefix is required")
    first, second = token_streams(reference), token_streams(actual)
    if any(a[skipped_reference_tokens:] != b for a, b in zip(first, second)):
        raise ValueError("Original per-token expert selections differ")
    return dict(layers=48, tokens_per_layer=len(second[0]),
                skipped_reference_tokens=skipped_reference_tokens,
                all_ordered_expert_indices_exact=True)
