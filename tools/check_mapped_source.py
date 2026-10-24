#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check bounded model-source reads with fake I/O and compile the PS5 provider."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
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
    app = ROOT / "native/app"
    exe = a.out / "mapped-source.exe"
    obj = a.out / "mapped-source-ps5.o"
    checks = [("control_compile", [host / "clang++.exe", "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror",
        "-I", app, ROOT / "tests/mapped_source.cpp", "-o", exe]), ("control_failures", [exe]),
        ("PS5_provider", [target / "clang++.exe", "--no-default-config", "--target=x86_64-sie-ps5",
            "-fno-stack-protector", "-fno-plt", "-femulated-tls", "-fPIC", "-std=c++17", "-O1", "-fexceptions",
            "-fcxx-exceptions", "-frtti", "-nostdinc++", "-isystem", sdk / "target/include/c++/v1",
            "-isystem", sdk / "target/include", "-I", app, "-c", app / "mapped_source.cpp", "-o", obj])]
    receipt = dict(schema="ps5-qwen-mapped-source-check-v1", console_access=False, learned_host_inference=False, steps=[])
    for label, command in checks:
        result = subprocess.run(list(map(str, command)), env=env, capture_output=True, timeout=180)
        (a.out / (label + ".private.log")).write_bytes(result.stdout + result.stderr)
        receipt["steps"].append(dict(name=label, returncode=result.returncode))
        (a.out / "receipt.private.json").write_text(json.dumps(receipt, indent=2) + "\n")
        if result.returncode:
            raise RuntimeError(label + ": " + result.stderr.decode("utf-8", "replace")[:4000])
        print(label + " passed", flush=True)
    receipt["provider_object_sha256"] = hashlib.sha256(obj.read_bytes()).hexdigest()
    receipt["inputs"] = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (app / "mapped_source.h", app / "mapped_source.cpp", app / "mapped_source_bridge.h", app / "profile_clock.h",
                     app / "device_buffer_budget.h", ROOT / "tests/mapped_source.cpp")}
    (a.out / "receipt.private.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
