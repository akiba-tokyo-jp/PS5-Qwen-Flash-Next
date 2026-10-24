#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check the actual patched cache planner and cross-compile patched engine objects.

Uses an isolated copy from the pinned archive. No shared engine source, driver,
model, console or release is touched. Host fixtures contain raw BF16 bits only.
"""
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def windows_arguments(command):
    shell = ctypes.windll.shell32
    shell.CommandLineToArgvW.argtypes = [ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_int)]
    shell.CommandLineToArgvW.restype = ctypes.POINTER(ctypes.c_wchar_p)
    count = ctypes.c_int()
    result = shell.CommandLineToArgvW(command, ctypes.byref(count))
    if not result:
        raise ValueError("Cannot parse compiler command")
    arguments = [result[i] for i in range(count.value)]
    ctypes.windll.kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    ctypes.windll.kernel32.LocalFree(ctypes.cast(result, ctypes.c_void_p))
    return arguments


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--workspace", type=Path, required=True)
    p.add_argument("--cache", type=Path, required=True)
    a = p.parse_args()
    lock = json.loads((ROOT / "native/qwen_flash_next/dependencies.lock.json").read_text())
    archive = a.cache / ("llama-" + lock["llama_cpp"]["revision"] + ".zip")
    with archive.open("rb") as stream:
        if hashlib.file_digest(stream, "sha256").hexdigest() != lock["llama_cpp"]["archive_sha256"]:
            raise ValueError("Pinned archive mismatch")
    out = a.cache / "build/expert-policy-check"
    src = out / "src"
    src.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as source:
        for name in ("llama-moe-cache.cpp", "llama-model.cpp"):
            matches = [path for path in source.namelist() if path.endswith("/src/" + name)]
            if len(matches) != 1:
                raise ValueError("Ambiguous engine source")
            (src / name).write_bytes(source.read(matches[0]))
    patches = []
    for name in ("0002-application-opt-in-no-mmap-prefetch.patch", "0003-adaptive-expert-policy-and-counters.patch"):
        patch = ROOT / "patches/llama" / name
        subprocess.run(["git", "apply", "--check", str(patch)], cwd=out, check=True)
        subprocess.run(["git", "apply", str(patch)], cwd=out, check=True)
        patches.append({"name": name, "sha256": hashlib.sha256(patch.read_bytes()).hexdigest()})
    header = ROOT / "native/app/expert_policy.h"
    (src / "llama-app-expert-policy.h").write_bytes(header.read_bytes())
    patched = (src / "llama-moe-cache.cpp").read_text()
    planner = patched[patched.index("struct moe_cache_slru {"):patched.index("// gate, up, down or gate_up, down")]
    (out / "engine-plan-under-test.h").write_text(planner)
    host = a.workspace / "toolchain/msys-clang64/clang64/bin"
    env = os.environ.copy(); env["PATH"] = str(host) + os.pathsep + env.get("PATH", "")
    executable = out / "expert-policy-tests.exe"
    commands = [ [str(host / "clang++.exe"), "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror",
                  "-I", str(header.parent), "-I", str(out), str(ROOT / "tests/expert_policy.cpp"), "-o", str(executable)],
                 [str(executable)] ]
    names = ["host_compile", "actual_planner_bf16_fixtures"]
    database = json.loads((a.cache / "build/llama-ps5/compile_commands.json").read_text())
    for name in ("llama-moe-cache.cpp", "llama-model.cpp"):
        entry = next(row for row in database if row["file"].replace("\\", "/").endswith("/" + name))
        command = windows_arguments(entry["command"])
        output = command.index("-o")
        del command[output:output + 2]
        source_index = next(i for i, arg in enumerate(command) if arg.replace("\\", "/") == entry["file"].replace("\\", "/"))
        command[source_index] = str(src / name)
        command += ["-o", str(out / (name + ".o"))]
        commands.append(command); names.append(name + "_ps5_object_compile")
    receipt = {"schema": "ps5-qwen-expert-policy-check-v1", "console_access": False, "driver_linked": False,
               "model_loaded": False, "patches": patches, "header_sha256": hashlib.sha256(header.read_bytes()).hexdigest(), "steps": []}
    for name, command in zip(names, commands):
        result = subprocess.run(command, cwd=a.cache / "build/llama-ps5", env=env, capture_output=True, text=True)
        (out / (name + ".private.log")).write_text(result.stdout + result.stderr)
        receipt["steps"].append({"name": name, "returncode": result.returncode})
        (out / "receipt.private.json").write_text(json.dumps(receipt, indent=2) + "\n")
        if result.returncode:
            raise SystemExit(result.stdout + result.stderr)
        print(name + " passed: " + result.stdout.strip(), flush=True)


if __name__ == "__main__":
    main()
