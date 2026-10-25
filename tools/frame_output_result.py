#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Validate the finite CPU-only frame comparison; no console operations."""
import re


def parse(raw, nonce):
    if not isinstance(raw, bytes) or not 0 < len(raw) <= 1 << 20:
        raise ValueError("A bounded completed frame journal is required")
    lines = raw.decode("ascii").splitlines()
    if [x for x in lines if x.startswith("BEGIN ")] != [
        f"BEGIN nonce={nonce} frame_evidence_only=1 window_bytes=1048576 GPU_calls=0 title_launches=0"
    ]:
        raise ValueError("Frame probe scope differs")
    if [x for x in lines if x.startswith("END ")] != [
        f"END success=1 nonce={nonce} Direct_released=1 GPU_calls=0 title_launches=0 model_payload_reads=0 automatic_retry=0"
    ] or any(x.startswith("RETAIN ") for x in lines):
        raise ValueError("Frame probe completion is unqualified")
    for operation in ("ALLOC", "MAP", "UNMAP", "RELEASE"):
        before = "FRAME_" + operation + "_BEFORE"
        after = "FRAME_" + operation + "_RETURNED rc=0"
        if lines.count(before) != 1 or lines.count(after) != 1 or lines.index(before) >= lines.index(after):
            raise ValueError("Direct lifetime lacks positive completion")
    stages = [x.removeprefix("FRAME_STAGE ") for x in lines if x.startswith("FRAME_STAGE ")]
    expected = []
    for _ in range(4):
        for operation, count in (("capture_prepare", 1), ("capture_write", 8),
                                 ("capture_fsync", 1), ("capture_trim", 1),
                                 ("capture_final_identity", 1), ("capture_close", 1),
                                 ("verify_open", 1), ("verify_read", 8),
                                 ("verify_EOF", 1), ("verify_close", 1)):
            for _ in range(count):
                expected.extend(("frame_" + operation + "_before_native_call",
                                 "frame_" + operation + "_native_call_returned"))
    if stages != expected:
        raise ValueError("A frame operation is missing, duplicated or unfinished")
    rows = []
    for line in lines:
        if not line.startswith("FRAME_CASE_COMPLETE "):
            continue
        match = re.fullmatch(
            r"FRAME_CASE_COMPLETE round=(\d+) mode=(\d+) index=(\d+) bytes=8294454 writes=8 SHA256_exact=1 "
            r"free_before=(\d+) free_after_write=(\d+) free_after_verify=(\d+)", line)
        if not match:
            raise ValueError("Frame bytes, hash or scope differs")
        r, mode, index, before, written, verified = map(int, match.groups())
        if min(before, written, verified) < 1154:
            raise ValueError("Frame probe exhausted the original observed reserve")
        rows.append(dict(round=r, mode=mode, index=index, free_before=before,
                         free_after_write=written, free_after_verify=verified,
                         write_free_page_change=written-before,
                         verify_free_page_change=verified-written))
    if [(x["round"], x["mode"], x["index"]) for x in rows] != [(0,0,0), (0,1,1), (1,1,2), (1,0,3)]:
        raise ValueError("Frame AB/BA samples differ")
    for x in rows:
        prefix = f"round={x['round']} mode={x['mode']} index={x['index']} free="
        if lines.count("FRAME_CASE_BEFORE " + prefix + str(x["free_before"])) != 1 or \
           lines.count("FRAME_CASE_WRITTEN " + prefix + str(x["free_after_write"])) != 1:
            raise ValueError("Frame boundary observations differ")
    return dict(schema="ps5-qwen-frame-output-CPU-result-v1", completed=True, cases=rows,
                all_frame_SHA256_exact=True, frame_bytes=8294454, scratch_bytes=1048576,
                Direct_released=True, GPU_calls=0, title_launches=0,
                whole_model_speed_qualified=False, production_adopted=False)
