#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Test the real native raster and startup parser without a console or model."""
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
    lock = json.loads((ROOT / "native/qwen_flash_next/dependencies.lock.json").read_text(encoding="utf-8"))
    upstream = a.cache / "upstream" / ("llama.cpp-" + lock["llama_cpp"]["revision"])
    out = a.cache / "build/monitor-check"
    out.mkdir(parents=True, exist_ok=True)
    host = a.workspace / "toolchain/msys-clang64/clang64/bin"
    env = os.environ.copy(); env["PATH"] = str(host) + os.pathsep + env.get("PATH", "")
    exe = out / "monitor-tests.exe"
    command = [str(host / "clang++.exe"), "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror",
               "-I", str(ROOT / "native/app"), "-I", str(upstream / "vendor"),
               *[str(ROOT / path) for path in ("native/app/monitor_raster.cpp", "native/app/startup.cpp", "tests/monitor.cpp")],
               "-o", str(exe)]
    for name, cmd in (("compile", command), ("native_raster_startup_and_tiles", [str(exe), str(out / "native-monitor.ppm")])):
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        (out / (name + ".private.log")).write_text(result.stdout + result.stderr, encoding="utf-8")
        if result.returncode: raise SystemExit(result.stdout + result.stderr)
        print(name + " passed: " + result.stdout.strip(), flush=True)
    display_exe = out / "display-tests.exe"
    display_command = [str(host / "clang++.exe"), "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror",
        "-I", str(ROOT / "tests/display_stubs"), "-I", str(ROOT / "native/app"),
        *[str(ROOT / path) for path in ("native/app/native_display.cpp", "native/app/monitor_raster.cpp", "tests/native_display.cpp")],
        "-o", str(display_exe)]
    for name, cmd in (("display_compile", display_command), ("display_owner_api_stubs", [str(display_exe)])):
        result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=60)
        (out / (name + ".private.log")).write_text(result.stdout + result.stderr, encoding="utf-8")
        if result.returncode: raise SystemExit(result.stdout + result.stderr)
        print(name + " passed: " + result.stdout.strip(), flush=True)
    from PIL import Image
    with Image.open(out / "native-monitor.ppm") as frame: frame.save(out / "native-monitor.png")
    (out / "receipt.private.json").write_text(json.dumps({"console_access": False, "model_loaded": False,
        "all_tile_addresses_unique": True, "native_raster_and_startup_checked": True,
        "display_owner_api_stubs_checked": True}) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
