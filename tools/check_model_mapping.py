#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check the real CPU mapping policy and compile its PS5 syscall provider."""
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
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=False)
    host = a.workspace / "toolchain/msys-clang64/clang64/bin"
    target = a.workspace / "toolchain/llvm-mingw-20261006-ucrt-x86_64/bin"
    sdk = a.workspace / "toolchain/ps5-sdk-radv/ps5-payload-sdk"
    env = dict(os.environ, PATH=str(host) + os.pathsep + os.environ.get("PATH", ""))
    exe = a.out / "model-mapping.exe"
    obj = a.out / "model-mapping-ps5.o"
    commands = [
        ("host_compile", [host / "clang++.exe", "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror",
            "-I", ROOT / "native/app", ROOT / "tests/model_mapping.cpp", "-o", exe]),
        ("ownership_failures", [exe]),
        ("PS5_provider_compile", [target / "clang++.exe", "--no-default-config", "--target=x86_64-sie-ps5",
            "-fno-stack-protector", "-fno-plt", "-femulated-tls", "-fPIC", "-std=c++17", "-O1",
            "-Wall", "-Wextra", "-Werror", "-fexceptions", "-fcxx-exceptions", "-frtti", "-nostdinc++",
            "-isystem", sdk / "target/include/c++/v1", "-isystem", sdk / "target/include",
            "-c", ROOT / "native/app/model_mapping.cpp", "-o", obj])]
    for label, command in commands:
        result = subprocess.run(list(map(str, command)), env=env, capture_output=True, timeout=120)
        (a.out / (label + ".private.log")).write_bytes(result.stdout + result.stderr)
        if result.returncode:
            raise RuntimeError(label + " failed: " + result.stderr.decode("utf-8", "replace"))
        print(label + " passed", flush=True)
    json_write(a.out / "receipt.private.json", dict(native_provider_object_SHA256=hashlib.sha256(obj.read_bytes()).hexdigest(),
        mapping_header_SHA256=hashlib.sha256((ROOT / "native/app/model_mapping.h").read_bytes()).hexdigest(),
        host_ownership_cases="passed", console_access=False, model_loaded=False, GPU_calls=0,
        physical_model_mapping_admitted=False))


if __name__ == "__main__":
    main()
