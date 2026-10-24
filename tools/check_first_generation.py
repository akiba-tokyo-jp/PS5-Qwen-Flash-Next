#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check bounded generation control and compile changed PS5 entry points only.

Uses API stubs on the host. No weights, full engine rebuild, driver linking,
console access, installation or inference occurs.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--only", action="append", choices=["first_generation", "adapter", "preceding_policy",
        "startup", "llama_engine", "native_main", "http_app", "bounded_demo", "chat_prompt", "native_display", "render"],
        help="Run only affected checks; default runs all checks")
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    workspace = args.workspace.resolve()
    lock = json.loads((ROOT / "native/qwen_flash_next/dependencies.lock.json").read_text())
    upstream = args.cache.resolve() / "upstream" / ("llama.cpp-" + lock["llama_cpp"]["revision"])
    host = workspace / "toolchain/msys-clang64/clang64/bin"
    target = workspace / "toolchain/llvm-mingw-20261006-ucrt-x86_64/bin"
    sdk = workspace / "toolchain/ps5-sdk-radv/ps5-payload-sdk"
    environment = dict(os.environ, PATH=str(host) + os.pathsep + os.environ.get("PATH", ""))
    app = ROOT / "native/app"
    sources = [app / name for name in ("first_generation.h", "first_generation_policy.h", "validation_policy.h",
        "startup.h", "startup.cpp", "llama_engine.h", "llama_engine.cpp", "native_main.cpp", "http_app.h", "http_app.cpp",
        "chat_prompt.h", "chat_prompt.cpp", "bounded_demo.h", "bounded_demo.cpp", "model_cpu_budget.h",
        "mapped_source.h", "mapped_source_bridge.h", "profile_clock.h", "device_buffer_budget.h", "native_display.h", "native_display.cpp", "demo_support.cpp")]
    sources += [ROOT / "tests" / name for name in ("first_generation.cpp", "first_generation_render.cpp", "llama_adapter.cpp", "validation_policy.cpp")]
    inputs = {str(path.relative_to(ROOT)): digest(path) for path in sources}
    flags = ["-std=c++17", "-O1", "-Wall", "-Wextra", "-Werror", "-I", app,
        "-I", upstream / "vendor", "-I", upstream / "include", "-I", upstream / "ggml/include"]
    checks = []
    for name, files in (("first_generation", [app / "startup.cpp", ROOT / "tests/first_generation.cpp"]),
                        ("adapter", [app / "llama_engine.cpp", ROOT / "tests/llama_adapter.cpp"]),
                        ("preceding_policy", [ROOT / "tests/validation_policy.cpp"])):
        if args.only and name not in args.only:
            continue
        executable = out / (name + ".exe")
        checks.append((name + "_compile", [host / "clang++.exe", *flags, *files, "-o", executable]))
        checks.append((name + "_run", [executable, out / "startup.private.json"] if name == "first_generation" else [executable]))
    native_flags = ["--no-default-config", "--target=x86_64-sie-ps5", "-fno-stack-protector", "-fno-plt",
        "-femulated-tls", "-fdenormal-fp-math=ieee", "-fPIC", "-std=c++17", "-O1", "-DNDEBUG",
        "-fvisibility-nodllstorageclass=default", "-fexceptions", "-fcxx-exceptions", "-frtti", "-nostdinc++",
        "-isystem", sdk / "target/include/c++/v1", "-isystem", sdk / "target/include", "-DQWEN_NATIVE_PLATFORM=1"]
    for include in (app, upstream / "include", upstream / "ggml/include", upstream / "common", upstream / "vendor/hash",
                    upstream / "src", upstream / "vendor", upstream / "vendor/nlohmann", upstream / "vendor/cpp-httplib"):
        native_flags += ["-I", include]
    for name in ("startup", "llama_engine", "native_main", "http_app", "bounded_demo", "chat_prompt", "native_display"):
        if args.only and name not in args.only:
            continue
        checks.append((name + "_PS5_object", [target / "clang++.exe", *native_flags,
            "-c", app / (name + ".cpp"), "-o", out / (name + "-ps5.o")]))
    if not args.only or "render" in args.only:
        # Link the actual shared renderer/interpreter without an HTTP server,
        # demo process, model or networking requests.
        render_sources = [app / "chat_prompt.cpp", ROOT / "tests/first_generation_render.cpp", app / "demo_support.cpp"]
        render_sources += [upstream / "common/jinja" / name for name in
            ("lexer.cpp", "parser.cpp", "runtime.cpp", "value.cpp", "string.cpp")]
        render_sources += [upstream / name for name in
            ("common/json.cpp", "common/unicode.cpp", "src/unicode.cpp", "src/unicode-data.cpp")]
        render_objects = []
        # Use the production preview warning policy for third-party interpreter
        # translation units; its headers intentionally retain unused helpers.
        render_flags = [*[flag for flag in flags if flag not in ("-Werror", "-Wextra")], "-O0", "-ffunction-sections", "-fdata-sections",
            "-I", upstream / "common", "-I", upstream / "src", "-I", upstream / "vendor/cpp-httplib"]
        for index, source in enumerate(render_sources):
            obj = out / ("render-" + str(index) + ".o")
            render_objects.append(obj)
            checks.append(("render_compile_" + str(index), [host / "clang++.exe", *render_flags, "-c", source, "-o", obj]))
        render_executable = out / "original-template-render.exe"
        checks.append(("render_link", [host / "clang++.exe", *render_objects, "-Wl,--gc-sections", "-lws2_32", "-o", render_executable]))
        template = args.cache.resolve() / "model/chat_template.jinja"
        receipt_template = dict(bytes=template.stat().st_size, sha256=digest(template))
        checks.append(("render_original_template", [render_executable, template]))
    receipt = dict(schema="ps5-qwen-first-generation-check-v1", inputs=inputs, steps=[],
        console_access=False, model_loaded=False, learned_host_inference=False,
        driver_linked=False, SELF_packaged=False, physical_first_generation_admitted=False)
    receipt["selected_checks"] = args.only or ["all"]
    if not args.only or "render" in args.only:
        receipt["original_template"] = receipt_template
    try:
        for name, command in checks:
            started = time.monotonic()
            result = subprocess.run(list(map(str, command)), env=environment, capture_output=True, timeout=180)
            (out / (name + ".private.log")).write_bytes(result.stdout + result.stderr)
            receipt["steps"].append(dict(name=name, returncode=result.returncode,
                elapsed_seconds=time.monotonic() - started))
            if result.returncode:
                raise RuntimeError(name + " failed: " + result.stderr.decode("utf-8", "replace")[:6000])
            print(name + " passed", flush=True)
        if inputs != {str(path.relative_to(ROOT)): digest(path) for path in sources}:
            raise RuntimeError("Application inputs changed during their focused checks")
        receipt["PS5_objects"] = {path.name: digest(path) for path in sorted(out.glob("*-ps5.o"))}
        receipt["state"] = "host_checks_completed"
    except BaseException as error:
        receipt["state"] = "failed"
        receipt["error"] = str(error)
        raise
    finally:
        (out / "receipt.private.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
