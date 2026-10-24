#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Cross-check the complete original model plan with native memory admission."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

from qwen_flash_next import json_write

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        parser.error("A fresh host verification directory is required")
    args.out.mkdir(parents=True)
    lock = json.loads((ROOT / "native/qwen_flash_next/dependencies.lock.json").read_text())
    upstream = args.cache / "upstream" / ("llama.cpp-" + lock["llama_cpp"]["revision"])
    host = args.workspace / "toolchain/msys-clang64/clang64/bin"
    env = dict(os.environ, PATH=str(host) + os.pathsep + os.environ.get("PATH", ""))
    exe = args.out / "model-footprint.exe"
    command = [str(host / "clang++.exe"), "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror",
               "-I", str(ROOT / "native/app"), "-I", str(upstream / "vendor"),
               str(ROOT / "tests/model_footprint.cpp"), "-o", str(exe)]
    compiled = subprocess.run(command, env=env, capture_output=True, timeout=120)
    (args.out / "compile.private.log").write_bytes(compiled.stdout + compiled.stderr)
    if compiled.returncode:
        raise RuntimeError("Host footprint verifier compilation failed")
    original = args.plan.read_bytes()
    run = subprocess.run([str(exe), str(args.plan)], env=env, capture_output=True, timeout=60)
    (args.out / "run.private.log").write_bytes(run.stdout + run.stderr)
    if run.returncode or args.plan.read_bytes() != original:
        raise RuntimeError("Native footprint verification failed or its plan changed")
    json_write(args.out / "receipt.private.json", {"complete_model_native_policy_match": True,
        "plan_sha256": hashlib.sha256(original).hexdigest(), "console_access": False,
        "physical_memory_admitted": False, "learned_inference_performed": False})
    print(run.stdout.decode("utf-8", "replace"), end="")


if __name__ == "__main__":
    main()
