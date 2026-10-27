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
    p.add_argument("--engine-source", type=Path, help="Pinned native engine header directory")
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=False)
    host = a.workspace / "toolchain/msys-clang64/clang64/bin"
    target = a.workspace / "toolchain/llvm-mingw-20261006-ucrt-x86_64/bin"
    sdk = a.workspace / "toolchain/ps5-sdk-radv/ps5-payload-sdk"
    env = dict(os.environ, PATH=str(host) + os.pathsep + os.environ.get("PATH", ""))
    app = ROOT / "native/app"
    exe = a.out / "mapped-source.exe"
    obj = a.out / "mapped-source-ps5.o"
    split_exe = a.out / "split-source.exe"
    checks = [("control_compile", [host / "clang++.exe", "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror",
        "-I", app, ROOT / "tests/mapped_source.cpp", "-o", exe]), ("control_failures", [exe]),
        ("split_control_compile", [host / "clang++.exe", "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror",
        "-I", app, ROOT / "tests/split_source.cpp", "-o", split_exe]), ("split_control_failures", [split_exe]),
        ("PS5_provider", [target / "clang++.exe", "--no-default-config", "--target=x86_64-sie-ps5",
            "-fno-stack-protector", "-fno-plt", "-femulated-tls", "-fPIC", "-std=c++17", "-O1", "-fexceptions",
            "-fcxx-exceptions", "-frtti", "-nostdinc++", "-isystem", sdk / "target/include/c++/v1",
            "-isystem", sdk / "target/include", "-I", app, "-c", app / "mapped_source.cpp", "-o", obj])]
    memory_command=list(checks[-1][1])
    memory_command[memory_command.index(app / "mapped_source.cpp")]=app / "system_memory.cpp"
    memory_command[-1]=a.out / "system-memory-ps5.o"
    checks.append(("PS5_memory_admission",memory_command))
    for name in ("direct_metadata", "model_mapping"):
        command=list(checks[4][1])
        command[command.index(app / "mapped_source.cpp")]=app / (name+".cpp")
        command[-1]=a.out / (name+"-ps5.o")
        if name == "direct_metadata":
            lock=json.loads((ROOT / "native/qwen_flash_next/dependencies.lock.json").read_text())
            candidates=([a.engine_source] if a.engine_source else
                [parent / "upstream" / ("llama.cpp-"+lock["llama_cpp"]["revision"]) for parent in a.out.resolve().parents])
            upstream=next((path for path in candidates if (path / "ggml/include/gguf.h").is_file()),None)
            if upstream is None:
                raise ValueError("Direct metadata checks require the data-disk native engine headers")
            command += ["-I",upstream / "ggml/include"]
        checks.append(("PS5_"+name,command))
    padded_exe=a.out / "padded-source.exe"
    checks.extend([("padded_control_compile",[host / "clang++.exe","-std=c++17","-O2","-Wall","-Wextra","-Werror",
        "-I",app,ROOT / "tests/padded_source.cpp","-o",padded_exe]),("padded_control_failures",[padded_exe])])
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
        for path in (app / "mapped_source.h", app / "mapped_source.cpp", app / "mapped_source_bridge.h", app / "mapped_copy.h", app / "profile_clock.h", app / "paired_source_io.h",
                     app / "system_memory.h",app / "system_memory.cpp",app / "memory_backpressure.h",
                     app / "device_buffer_budget.h",app / "logical_source_bridge.h", app / "direct_metadata.h",
                     app / "direct_metadata.cpp",app / "model_mapping.cpp", ROOT / "tests/mapped_source.cpp",
                     ROOT / "tests/split_source.cpp",ROOT / "tests/padded_source.cpp",app / "padded_bank.h",
                     app / "padded_bank_layout.h",app / "padded_cache_bridge.h",app / "padded_cache_geometry.h")}
    (a.out / "receipt.private.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
