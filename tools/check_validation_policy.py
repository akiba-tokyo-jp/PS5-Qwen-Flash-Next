#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check the actual bounded native fixture gate without a console or GPU."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
from qwen_flash_next import json_write

ROOT = Path(__file__).resolve().parents[1]

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--workspace", type=Path, required=True)
    p.add_argument("--cache", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=False)
    lock = json.loads((ROOT / "native/qwen_flash_next/dependencies.lock.json").read_text())
    vendor = a.cache / "upstream" / ("llama.cpp-" + lock["llama_cpp"]["revision"]) / "vendor"
    host = a.workspace / "toolchain/msys-clang64/clang64/bin"
    env = dict(os.environ, PATH=str(host) + os.pathsep + os.environ.get("PATH", ""))
    exe = a.out / "validation-policy.exe"
    command = [str(host / "clang++.exe"), "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror",
               "-I", str(ROOT / "native/app"), "-I", str(vendor),
               str(ROOT / "tests/validation_policy.cpp"), "-o", str(exe)]
    for label, args, timeout in (("compile", command, 120), ("run", [str(exe)], 20)):
        result = subprocess.run(args, env=env, capture_output=True, timeout=timeout)
        (a.out / (label + ".private.log")).write_bytes(result.stdout + result.stderr)
        if result.returncode:
            raise RuntimeError("Native validation policy " + label + " failed")
    json_write(a.out / "receipt.private.json", {"native_validation_policy": "passed",
        "native_header_sha256": hashlib.sha256((ROOT / "native/app/validation_policy.h").read_bytes()).hexdigest(),
        "full_inference_enabled": False, "console_access": False, "GPU_calls": 0, "CI": False})
    print(result.stdout.decode(), end="")

if __name__ == "__main__":
    main()
