#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Manually test application control flow on the host with a fake engine.

Also compile the same application source to a PS5 object without linking the
driver, creating a release, loading model weights, or accessing a console.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--workspace", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    workspace, out = a.workspace.resolve(), a.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    host = workspace / "toolchain/msys-clang64/clang64/bin"
    target = workspace / "toolchain/llvm-mingw-20261006-ucrt-x86_64/bin"
    sdk = workspace / "toolchain/ps5-sdk-radv/ps5-payload-sdk"
    source = ROOT / "native/app/session.cpp"
    tests = ROOT / "tests/app_session.cpp"
    env = os.environ.copy()
    env["PATH"] = str(host) + os.pathsep + env.get("PATH", "")
    executable = out / "app-session-tests.exe"
    obj = out / "session-ps5.o"
    commands = [
        [host / "clang++.exe", "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror", "-I", source.parent,
         source, tests, "-o", executable],
        [executable],
        [target / "clang++.exe", "--no-default-config", "--target=x86_64-sie-ps5", "-fno-stack-protector",
         "-fno-plt", "-femulated-tls", "-fPIC", "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror",
         "-fexceptions", "-fcxx-exceptions", "-frtti",
         "-nostdinc++", "-isystem", sdk / "target/include/c++/v1", "-isystem", sdk / "target/include",
         "-c", source, "-o", obj]]
    receipt = {"schema": "ps5-qwen-application-check-v1", "console_access": False,
               "driver_linked": False, "model_loaded": False, "learned_host_inference": False,
               "source_sha256": sha(source), "header_sha256": sha(source.with_suffix(".h")),
               "tests_sha256": sha(tests), "steps": []}
    for name, command in zip(("host_compile", "fake_backend_scenarios", "ps5_object_compile"), commands):
        result = subprocess.run(list(map(str, command)), env=env, capture_output=True, text=True)
        (out / (name + ".private.log")).write_text(result.stdout + result.stderr, encoding="utf-8")
        receipt["steps"].append({"name": name, "returncode": result.returncode})
        (out / "receipt.private.json").write_text(json.dumps(receipt, indent=2) + "\n")
        if result.returncode:
            raise SystemExit(result.stdout + result.stderr or f"{name} failed: {result.returncode}")
        print(name + " passed", flush=True)
    receipt["ps5_object_sha256"] = sha(obj)
    (out / "receipt.private.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print("Application checks complete; console access and release remain disabled")


if __name__ == "__main__":
    main()
