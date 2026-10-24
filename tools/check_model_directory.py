#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Run in-memory ownership checks and compile the actual PS5 provider object."""
import argparse
import json
import os
from pathlib import Path
import subprocess
from build_model_directory import QUALIFIED_COMMAND_TEMPLATE, QUALIFIED_SOURCE, command_template, record
from model_transport import exclusive_json
from transfer_model import ROOT, bounded_json, sha


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("workspace", "cache", "qualified_reference", "out"):
        p.add_argument("--" + name.replace("_", "-"), type=Path, required=True)
    a = p.parse_args(); workspace = a.workspace.resolve(); cache = a.cache.resolve()
    reference_path = a.qualified_reference.resolve(); reference = reference_path.parent
    old = bounded_json(reference_path)
    if (not reference_path.is_relative_to(cache) or sha(old["source_path"]) != QUALIFIED_SOURCE or
            command_template(old["commands"], reference, workspace) != QUALIFIED_COMMAND_TEMPLATE or
            not Path(old["commands"][0][0]).resolve().is_relative_to(workspace / "toolchain")):
        raise ValueError("The task's exact qualified CPU build reference is required")
    out = a.out.resolve()
    if not out.is_relative_to(cache): raise ValueError("A fresh data-disk check directory is required")
    out.mkdir(parents=True, exist_ok=False); (out / "tmp").mkdir()
    header = out / "model_directory_context.h"
    synthetic_marker = "synthetic-model-directory-marker:" + "x" * (4095 - len("synthetic-model-directory-marker:")) + "\n"
    header.write_text('#define OWNER_NONCE "' + 'a' * 32 + '"\n'
        '#define MODEL_MARKER ' + json.dumps(synthetic_marker) + '\n'
        '#define LOG_PREFIX "/data/ai/moss-qwen-directory-host-check-only"\n', newline="\n")
    source = ROOT / "native/qwen_flash_next/model_directory_control.c"
    test = ROOT / "tests/model_directory_control.c"
    stub = ROOT / "tests/stubs/model_directory_stubs.h"
    original_object = Path(old["commands"][0][old["commands"][0].index("-o") + 1])
    inputs = [source, test, stub, header, reference_path, Path(old["source_path"]), original_object]
    before = [record(path) for path in inputs]
    native = [value.replace(str(reference), str(out)) for value in old["commands"][0]]
    native[native.index("-c") + 1] = str(source)
    native_object = out / "model-directory-native.o"
    native[native.index("-o") + 1] = str(native_object)
    native += ["-Wall", "-Wextra", "-Werror"]
    host = workspace / "toolchain/msys-clang64/clang64/bin"
    executable = out / "model-directory-host.exe"
    commands = [native, [str(host / "clang.exe"), "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
        "-I", str(ROOT / "tests/stubs"), "-I", str(out), str(test), "-o", str(executable)]]
    env = dict(os.environ, PATH=str(host) + os.pathsep + os.environ.get("PATH", ""),
               TMP=str(out / "tmp"), TEMP=str(out / "tmp"))
    for index, command in enumerate(commands):
        result = subprocess.run(command, capture_output=True, env=env, timeout=120)
        (out / ("compile-" + str(index) + ".private.log")).write_bytes(result.stdout + result.stderr)
        if result.returncode: raise RuntimeError("Directory controller provider/API compilation failed")
    result = subprocess.run([str(executable)], capture_output=True, env=env, timeout=30)
    (out / "API-run.private.log").write_bytes(result.stdout + result.stderr)
    if result.returncode: raise RuntimeError("Directory controller API ownership checks failed")
    nm = Path(native[0]).with_name("llvm-nm.exe")
    imported = subprocess.check_output([str(nm), "--undefined-only", str(native_object)], text=True, timeout=30)
    prior = subprocess.check_output([str(nm), "--undefined-only", str(original_object)], text=True, timeout=30)
    names = lambda raw: {line.split()[-1] for line in raw.splitlines() if line.split()}
    if names(imported) - names(prior) or any(value in imported for value in
            ("sceAgc", "sceSystemService", "ptrace", "mmap", "mprotect", "kernel_set_", "kernel_copy")):
        raise ValueError("Unqualified CPU controller import")
    if before != [record(path) for path in inputs]: raise ValueError("Directory check inputs changed")
    exclusive_json(out / "receipt.private.json", dict(actual_source_and_provider_checked=True,
        API_output=result.stdout.decode("utf-8", "strict").strip(), source_inputs=before,
        source_stable=True, native_object=record(native_object), host_check=record(executable),
        qualified_import_subset=True, native_executable_linked=False, only_synthetic_context=True,
        console_access=False, commands=commands, GPU_calls=0))
    print(json.dumps(dict(directory_ownership_API_checks="passed", PS5_provider_object="compiled",
        qualified_import_subset=True, native_executable_linked=False, console_access=False)))


if __name__ == "__main__": main()
