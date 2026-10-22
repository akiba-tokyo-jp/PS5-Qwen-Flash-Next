#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Wait for the existing acquisition, then perform host-only BF16 conversion.

This is an ordinary bounded batch command. It never launches console software,
loads a learned model for inference, or starts another download writer.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import time


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cache", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--state", type=Path, required=True, help="Fresh host-only status file")
    p.add_argument("--wait-seconds", type=int, default=43200)
    p.add_argument("--conversion-timeout-seconds", type=int, default=21600)
    a = p.parse_args()
    if not 0 <= a.wait_seconds <= 86400 or not 1 <= a.conversion_timeout_seconds <= 86400:
        p.error("Invalid preparation deadline")
    a.state.parent.mkdir(parents=True, exist_ok=True)
    with a.state.open("x", encoding="utf-8") as stream:
        json.dump({"phase": "starting", "pid": os.getpid()}, stream)
    started = time.monotonic()
    def status(phase, **fields):
        value = {"schema": "ps5-qwen-model-preparation-v1", "phase": phase, "pid": os.getpid(),
                 "updated_at": datetime.now(timezone.utc).isoformat(), "elapsed_seconds": time.monotonic()-started,
                 "console_access": False, "learned_inference_performed": False, **fields}
        temporary = a.state.with_name(a.state.name + ".next")
        temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, a.state)
    try:
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
        status("completed", converted_files=len(receipt["files"]), output=str(a.out))
    except BaseException as error:
        status("failed", error_type=type(error).__name__)
        raise


if __name__ == "__main__":
    main()
