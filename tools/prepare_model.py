#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Resume or wait for acquisition, then perform host-only BF16 conversion.

This is an ordinary bounded batch command. It never launches console software,
loads a learned model for inference, or allows duplicate download writers.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import time
from qwen_flash_next import atomic_replace


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cache", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--state", type=Path, required=True, help="Fresh host-only status file")
    p.add_argument("--wait-seconds", type=int, default=43200)
    p.add_argument("--acquire", action="store_true", help="Resume verified acquisition before conversion")
    p.add_argument("--jobs", type=int, default=4)
    p.add_argument("--download-range-mib", type=int, choices=(8, 16, 32, 64), default=32)
    p.add_argument("--conversion-timeout-seconds", type=int, default=21600)
    a = p.parse_args()
    if not 0 <= a.wait_seconds <= 86400 or not 1 <= a.conversion_timeout_seconds <= 86400:
        p.error("Invalid preparation deadline")
    from qwen_flash_next import writer_lease
    with writer_lease(a.cache / "model-preparation.lock.private"):
        run(a)


def run(a):
    a.state.parent.mkdir(parents=True, exist_ok=True)
    with a.state.open("x", encoding="utf-8") as stream:
        json.dump({"phase": "starting", "pid": os.getpid()}, stream)
    started = time.monotonic()
    def status(phase, **fields):
        value = {"schema": "ps5-qwen-model-preparation-v1", "phase": phase, "pid": os.getpid(),
                 "updated_at": datetime.now(timezone.utc).isoformat(), "elapsed_seconds": time.monotonic()-started,
                 "console_access": False, "learned_inference_performed": False, **fields}
        temporary = a.state.with_name(a.state.name + ".next")
        with temporary.open("w", encoding="utf-8") as stream:
            stream.write(json.dumps(value, indent=2) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        atomic_replace(temporary, a.state)
    try:
        if a.acquire:
            if not 1 <= a.jobs <= 8 or a.wait_seconds < 1:
                raise ValueError("Invalid bounded acquisition settings")
            status("acquisition_started", deadline_seconds=a.wait_seconds)
            import qwen_flash_next
            # Every original file is hashed before converter execution below.
            # Avoid concurrent rereads of retained files on the acquisition disk.
            qwen_flash_next.download(a.cache, a.jobs, a.wait_seconds, verify_existing=False,
                                     range_bytes=a.download_range_mib << 20)
        manifest = json.loads((a.cache / "metadata/checkpoint.json").read_text())
        while True:
            ready = sum((a.cache / "model" / row["name"]).is_file() and
                        (a.cache / "model" / row["name"]).stat().st_size == row["bytes"] for row in manifest["files"])
            status("waiting_for_original_shards", available=ready, total=len(manifest["files"]), deadline_seconds=a.wait_seconds)
            if ready == len(manifest["files"]): break
            remaining = a.wait_seconds - (time.monotonic() - started)
            if remaining <= 0: raise TimeoutError("Original checkpoint acquisition did not complete before the host deadline")
            time.sleep(min(30, remaining))
        status("conversion_started", output=str(a.out))
        import convert_model
        sys.argv = ["convert_model.py", "--cache", str(a.cache), "--out", str(a.out),
                    "--timeout-seconds", str(a.conversion_timeout_seconds)]
        convert_model.main()
        receipt = json.loads((a.out / "model-receipt.json").read_text())
        if not receipt["original_shards_verified"] or receipt["outtype"] != "bf16":
            raise ValueError("BF16 preparation did not produce the expected receipt")
        audit = receipt.get("conversion_audit", {})
        if not all(audit.get(key) for key in ("complete_tensor_set", "exact_shapes_and_precision",
                                               "exact_PLE_integer_constants", "PLE_payload_bytes_verified",
                                               "expert_payload_bytes_verified", "complete_converted_tensor_payload_verified")):
            raise ValueError("BF16 preparation is missing the complete host conversion audit")
        status("completed", converted_files=len(receipt["files"]), output=str(a.out))
    except BaseException as error:
        status("failed", error_type=type(error).__name__)
        raise


if __name__ == "__main__":
    main()
