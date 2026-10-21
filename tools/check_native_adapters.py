#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Host API-stub checks for the actual native Vulkan/socket adapters."""
import argparse
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--workspace", type=Path, required=True)
    p.add_argument("--cache", type=Path, required=True)
    a = p.parse_args()
    host = a.workspace / "toolchain/msys-clang64/clang64/bin"
    out = a.cache / "build/native-adapter-checks"
    out.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy(); env["PATH"] = str(host) + os.pathsep + env.get("PATH", "")
    receipt = {"console_access": False, "driver_loaded": False, "model_loaded": False, "steps": []}
    for name, include in (("vulkan_bridge", a.workspace / "toolchain/Vulkan-Headers/include"), ("native_socket", ROOT / "tests/socket_stubs")):
        exe = out / (name + ".exe")
        command = [str(host / "clang++.exe"), "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror", "-I", str(include),
                   str(ROOT / "native/app" / (name + ".cpp")), str(ROOT / "tests" / (name + ".cpp")), "-o", str(exe)]
        for stage, cmd in (("compile", command), ("api_stubs", [str(exe)])):
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            (out / (name + "-" + stage + ".private.log")).write_text(result.stdout + result.stderr, encoding="utf-8")
            receipt["steps"].append({"name": name + "_" + stage, "returncode": result.returncode})
            (out / "receipt.private.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
            if result.returncode: raise SystemExit(result.stdout + result.stderr)
            print(name + " " + stage + " passed: " + result.stdout.strip(), flush=True)


if __name__ == "__main__":
    main()
