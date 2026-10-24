#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise the bounded indexed MoE graph and compile it for the PS5 ABI."""
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
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    lock = json.loads((ROOT / "native/qwen_flash_next/dependencies.lock.json").read_text())
    upstream = args.cache / "upstream" / ("llama.cpp-" + lock["llama_cpp"]["revision"])
    host = args.workspace / "toolchain/msys-clang64/clang64/bin"
    target = args.workspace / "toolchain/llvm-mingw-20261006-ucrt-x86_64/bin"
    sdk = args.workspace / "toolchain/ps5-sdk-radv/ps5-payload-sdk"
    env = dict(os.environ, PATH=str(host) + os.pathsep + os.environ.get("PATH", ""))
    source = ROOT / "native/app/moe_admission.cpp"
    header = source.with_suffix(".h")
    test = ROOT / "tests/moe_admission.cpp"
    exe, obj = args.out / "moe-admission.exe", args.out / "moe-admission-ps5.o"
    commands = [
        ("host_compile", [host / "clang++.exe", "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror",
            "-I", ROOT / "native/app", "-I", ROOT / "tests/gpu_admission_stubs", source, test, "-o", exe]),
        ("shape_numeric_and_ownership", [exe, args.out / "synthetic-moe.bf16"]),
        ("PS5_compile", [target / "clang++.exe", "--no-default-config", "--target=x86_64-sie-ps5",
            "-fno-stack-protector", "-fno-plt", "-femulated-tls", "-fPIC", "-std=c++17", "-O1",
            "-Wall", "-Wextra", "-Werror", "-fexceptions", "-fcxx-exceptions", "-frtti", "-nostdinc++",
            "-isystem", sdk / "target/include/c++/v1", "-isystem", sdk / "target/include",
            "-I", upstream / "ggml/include", "-c", source, "-o", obj])]
    inputs = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in (source, header, test)}
    for label, command in commands:
        result = subprocess.run(list(map(str, command)), env=env, capture_output=True, timeout=120)
        (args.out / (label + ".private.log")).write_bytes(result.stdout + result.stderr)
        if result.returncode:
            raise RuntimeError(label + " failed: " + result.stderr.decode("utf-8", "replace"))
        print(label + " passed", flush=True)
    if any(hashlib.sha256(Path(path).read_bytes()).hexdigest() != digest for path, digest in inputs.items()):
        raise RuntimeError("MoE check inputs changed")
    json_write(args.out / "receipt.private.json", dict(inputs=inputs, host_API_stubs="passed",
        PS5_object_compiled=True, graph_compute_calls=1, experts=512, selected_experts=10,
        fixture_bytes=41943040, maximum_upload_chunk_bytes=8 << 20, fixed_NRMSE_limit=0.01,
        console_access=False, GPU_calls=0, full_model_inference=False))


if __name__ == "__main__":
    main()
