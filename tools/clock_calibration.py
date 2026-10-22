#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Create an app-local offset from a guarded CPU observation and host interval.

The caller must already have admitted the observer's nonce, boot and unchanged
process guards. This tool reads local metadata only; it never contacts a console
or changes a system clock.
"""
import argparse
import json
from pathlib import Path
import re
from qwen_flash_next import json_write


def calibration(console_seconds, before_ms, after_ms, elapsed_ms):
    if any(type(value) is not int for value in (console_seconds, before_ms, after_ms, elapsed_ms)):
        raise ValueError("Clock observations require integer fields")
    interval = after_ms - before_ms
    if not 0 <= interval <= 8000 or elapsed_ms < 0 or abs(interval - elapsed_ms) > 250:
        raise ValueError("Host clock observation interval is too wide or discontinuous")
    lower, upper = 946684800000, 4102444800000
    console_ms = console_seconds * 1000
    if not lower <= console_ms <= upper or not lower <= before_ms <= after_ms <= upper:
        raise ValueError("Clock epoch is outside its supported range")
    utc_ms = (before_ms + after_ms) // 2
    if abs(utc_ms - console_ms) > 86400000:
        raise ValueError("Clock offset exceeds its application-only bound")
    return dict(schema="ps5-qwen-clock-offset-v1", console_epoch_ms=console_ms,
                utc_epoch_ms=utc_ms, uncertainty_ms=(interval + 1) // 2 + 1000)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--observer-log", type=Path, required=True)
    parser.add_argument("--host-interval", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.observer_log.stat().st_size > 131072 or args.host_interval.stat().st_size > 4096:
        raise ValueError("Clock observation metadata exceeds its bound")
    log = args.observer_log.read_text()
    matches = re.findall(r"^BEGIN [^\n]* unix_time=([0-9]+) [^\n]*CPU_only=1 ", log, re.M)
    if len(matches) != 1 or "\nEND success=1 " not in log:
        raise ValueError("One completed CPU observer is required")
    host = json.loads(args.host_interval.read_text())
    result = calibration(int(matches[0]), host["host_before_epoch_ms"],
                         host["host_after_epoch_ms"], host["host_elapsed_ms"])
    if args.out.exists():
        raise FileExistsError("Clock calibration must use a fresh output path")
    json_write(args.out, result)
    print(json.dumps(dict(clock_calibration_prepared=True,
                         uncertainty_ms=result["uncertainty_ms"], console_access=False)))


if __name__ == "__main__":
    main()
