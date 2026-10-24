#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check actual bounded operation control and compile it for the PS5 ABI."""
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
    a = p.parse_args(); a.out.mkdir(parents=True, exist_ok=False)
    lock = json.loads((ROOT / "native/qwen_flash_next/dependencies.lock.json").read_text())
    upstream = a.cache / "upstream" / ("llama.cpp-" + lock["llama_cpp"]["revision"])
    host = a.workspace / "toolchain/msys-clang64/clang64/bin"
    target = a.workspace / "toolchain/llvm-mingw-20261006-ucrt-x86_64/bin"
    sdk = a.workspace / "toolchain/ps5-sdk-radv/ps5-payload-sdk"
    env = dict(os.environ, PATH=str(host) + os.pathsep + os.environ.get("PATH", ""))
    exe = a.out / "operator-admission.exe"; obj = a.out / "operator-admission-ps5.o"
    source = ROOT / "native/app/operator_admission.cpp"
    commands = [("host_compile", [host / "clang++.exe", "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror",
        "-I", ROOT / "native/app", "-I", ROOT / "tests/gpu_admission_stubs", source,
        ROOT / "tests/operator_admission.cpp", "-o", exe]),
        ("ownership_and_numeric_refusals", [exe, a.out / "synthetic-fixture.bf16"]),
        ("PS5_compile", [target / "clang++.exe", "--no-default-config", "--target=x86_64-sie-ps5",
        "-fno-stack-protector", "-fno-plt", "-femulated-tls", "-fPIC", "-std=c++17", "-O1",
        "-Wall", "-Wextra", "-Werror", "-fexceptions", "-fcxx-exceptions", "-frtti", "-nostdinc++",
        "-isystem", sdk / "target/include/c++/v1", "-isystem", sdk / "target/include",
        "-I", upstream / "ggml/include", "-c", source, "-o", obj])]
    for label, command in commands:
        result = subprocess.run(list(map(str, command)), env=env, capture_output=True, timeout=120)
        (a.out / (label + ".private.log")).write_bytes(result.stdout + result.stderr)
        if result.returncode: raise RuntimeError(label + " failed: " + result.stderr.decode("utf-8", "replace"))
        print(label + " passed", flush=True)
    json_write(a.out / "receipt.private.json", dict(source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        host_API_stubs="passed", PS5_object_compiled=True, fixture_is_synthetic=True,
        fixed_NRMSE_limit=0.01, graph_compute_calls=1, console_access=False,
        learned_inference_performed=False, physical_operator_admission=False))


if __name__ == "__main__": main()
