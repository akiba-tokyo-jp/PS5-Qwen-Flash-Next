#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build the host-only application preview and cross-compile app objects.

No driver link, model execution, console access, packaging or deployment occurs.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
LOCK = json.loads((ROOT / "native/qwen_flash_next/dependencies.lock.json").read_text())


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--workspace", type=Path, required=True)
    p.add_argument("--cache", type=Path, required=True)
    a = p.parse_args()
    workspace, cache = a.workspace.resolve(), a.cache.resolve()
    source = cache / "upstream" / ("llama.cpp-" + LOCK["llama_cpp"]["revision"])
    archive = cache / ("llama-" + LOCK["llama_cpp"]["revision"] + ".zip")
    with archive.open("rb") as stream:
        if hashlib.file_digest(stream, "sha256").hexdigest() != LOCK["llama_cpp"]["archive_sha256"]:
            raise ValueError("Pinned engine archive mismatch")
    out = cache / "build/application-preview"
    out.mkdir(parents=True, exist_ok=True)
    host = workspace / "toolchain/msys-clang64/clang64/bin"
    target = workspace / "toolchain/llvm-mingw-20261006-ucrt-x86_64/bin"
    sdk = workspace / "toolchain/ps5-sdk-radv/ps5-payload-sdk"
    includes = [ROOT / "native/app", source / "include", source / "ggml/include", source / "common",
                source / "src", source / "vendor", source / "vendor/nlohmann", source / "vendor/cpp-httplib"]
    flags = [flag for path in includes for flag in ("-I", str(path))]
    files = [ROOT / "native/app" / name for name in ("session.cpp", "http_app.cpp", "chat_prompt.cpp", "demo_main.cpp", "demo_support.cpp", "monitor_raster.cpp")]
    files += [source / "common/jinja" / name for name in ("lexer.cpp", "parser.cpp", "runtime.cpp", "value.cpp", "string.cpp")]
    files += [source / "common/json.cpp", source / "common/unicode.cpp", source / "src/unicode.cpp", source / "src/unicode-data.cpp", source / "vendor/cpp-httplib/httplib.cpp"]
    env = os.environ.copy(); env["PATH"] = str(host) + os.pathsep + env.get("PATH", "")
    objects = out / "host-objects"
    objects.mkdir(exist_ok=True)
    app_headers = b"".join(path.read_bytes() for path in sorted((ROOT / "native/app").glob("*.h")))

    def compile_one(path):
        identity = hashlib.sha256((str(path) + json.dumps(flags)).encode() + path.read_bytes() + app_headers).hexdigest()
        obj = objects / (path.stem + "-" + identity[:16] + ".o")
        if not obj.exists():
            command = [host / "clang++.exe", "-std=c++17", "-O0", *flags, "-c", path, "-o", obj]
            result = subprocess.run(list(map(str, command)), env=env, capture_output=True, text=True)
            (objects / (obj.stem + ".private.log")).write_text(result.stdout + result.stderr)
            if result.returncode:
                obj.unlink(missing_ok=True)
                raise RuntimeError(result.stdout + result.stderr)
        print("compiled " + path.name, flush=True)
        return obj

    with ThreadPoolExecutor(max_workers=4) as pool:
        built = [future.result() for future in as_completed([pool.submit(compile_one, path) for path in files])]
    commands = [("preview_link", [host / "clang++.exe", *built, "-lws2_32", "-o", out / "app-demo.exe"])]
    for name in ("llama_engine", "http_app", "native_main"):
        commands.append((name + "_ps5_compile", [target / "clang++.exe", "--no-default-config", "--target=x86_64-sie-ps5",
            "-fno-stack-protector", "-fno-plt", "-femulated-tls", "-fPIC", "-std=c++17", "-O1",
            "-fexceptions", "-fcxx-exceptions", "-frtti", "-nostdinc++", "-isystem", sdk / "target/include/c++/v1",
            "-isystem", sdk / "target/include", *flags, "-c", ROOT / "native/app" / (name + ".cpp"), "-o", out / (name + "-ps5.o")]))
    receipt = {"schema": "ps5-qwen-application-preview-build-v1", "upstream_revision": LOCK["llama_cpp"]["revision"],
               "console_access": False, "driver_linked": False, "model_loaded": False, "steps": []}
    for name, command in commands:
        with (out / (name + ".private.log")).open("w", encoding="utf-8") as stream:
            result = subprocess.run(list(map(str, command)), env=env, stdout=stream, stderr=subprocess.STDOUT)
        receipt["steps"].append({"name": name, "returncode": result.returncode})
        (out / "receipt.private.json").write_text(json.dumps(receipt, indent=2) + "\n")
        if result.returncode:
            raise SystemExit((out / (name + ".private.log")).read_text(encoding="utf-8", errors="replace")[-10000:])
        print(name + " passed", flush=True)
    print("Preview executable: " + str(out / "app-demo.exe"))


if __name__ == "__main__":
    main()
