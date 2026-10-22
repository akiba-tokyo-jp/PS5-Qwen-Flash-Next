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
    p.add_argument("--out", type=Path, help="Fresh focused-check directory")
    p.add_argument("--only", choices=["raster", "display"])
    a = p.parse_args()
    lock = json.loads((ROOT / "native/qwen_flash_next/dependencies.lock.json").read_text(encoding="utf-8"))
    upstream = a.cache / "upstream" / ("llama.cpp-" + lock["llama_cpp"]["revision"])
    out = a.out.resolve() if a.out else a.cache / "build/monitor-check"
    out.mkdir(parents=True, exist_ok=a.out is None)
    host = a.workspace / "toolchain/msys-clang64/clang64/bin"
    env = os.environ.copy(); env["PATH"] = str(host) + os.pathsep + env.get("PATH", "")
    exe = out / "monitor-tests.exe"
    command = [str(host / "clang++.exe"), "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror",
               "-I", str(ROOT / "native/app"), "-I", str(upstream / "vendor"),
               *[str(ROOT / path) for path in ("native/app/monitor_raster.cpp", "native/app/startup.cpp", "tests/monitor.cpp")],
               "-o", str(exe)]
    for name, cmd in (("compile", command), ("native_raster_startup_and_tiles", [str(exe), str(out / "native-monitor.ppm")])):
        if a.only == "display": continue
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        (out / (name + ".private.log")).write_text(result.stdout + result.stderr, encoding="utf-8")
        if result.returncode: raise SystemExit(result.stdout + result.stderr)
        print(name + " passed: " + result.stdout.strip(), flush=True)
    display_exe = out / "display-tests.exe"
    display_command = [str(host / "clang++.exe"), "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror",
        "-I", str(ROOT / "tests/display_stubs"), "-I", str(ROOT / "native/app"),
        *[str(ROOT / path) for path in ("native/app/native_display.cpp", "native/app/monitor_raster.cpp", "tests/native_display.cpp")],
        "-o", str(display_exe)]
    for name, cmd in (("display_compile", display_command), ("display_owner_api_stubs", [str(display_exe), str(out / "completed-frame.bmp")])):
        if a.only == "raster": continue
        result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=60)
        (out / (name + ".private.log")).write_text(result.stdout + result.stderr, encoding="utf-8")
        if result.returncode: raise SystemExit(result.stdout + result.stderr)
        print(name + " passed: " + result.stdout.strip(), flush=True)
    from PIL import Image
    if a.only != "display":
        with Image.open(out / "native-monitor.ppm") as frame: frame.save(out / "native-monitor.png")
    if a.only != "raster":
        with Image.open(out / "completed-frame.bmp") as frame:
            if frame.size != (1920, 1080): raise ValueError("Completed scanout-source dimensions differ")
            frame.save(out / "completed-frame.png")
    (out / "receipt.private.json").write_text(json.dumps({"console_access": False, "model_loaded": False,
        "all_tile_addresses_unique": a.only != "display", "native_raster_and_startup_checked": a.only != "display",
        "display_owner_api_stubs_checked": a.only != "raster", "selected_checks": a.only or "all",
        "completed_scanout_source_capture_checked": a.only != "raster"}) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
