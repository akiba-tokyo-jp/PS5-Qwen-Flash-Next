#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reject native imports not exported by the real public module stubs."""
import argparse
import json
from pathlib import Path
import re
import subprocess

from driver_inputs import sha


def audit(workspace, cache, native_build=None):
    native_build = Path(native_build) if native_build else cache / "build/application-native"
    receipt = json.loads((native_build / "receipt.private.json").read_text())
    image = Path(receipt["artifact"]["path"])
    if sha(image) != receipt["artifact"]["sha256"]:
        raise ValueError("Native image changed after linking")
    llvm = workspace / "toolchain/llvm-mingw-20261006-ucrt-x86_64/bin"
    imports = [Path(row["path"]) for row in receipt["inputs_before"]
               if row["path"].endswith(".so") and not Path(row["path"]).name.endswith("_stub_weak.so")]
    providers = {}
    for path in imports:
        dynamic = subprocess.check_output([str(llvm / "llvm-readelf.exe"), "--dynamic", str(path)], text=True)
        name = re.search(r"Library soname: \[([^\]]+)\]", dynamic)[1]
        if name not in receipt["runtime_providers"]:
            continue
        output = subprocess.check_output([str(llvm / "llvm-nm.exe"), "-D", "--defined-only", "--format=posix", str(path)], text=True)
        for line in output.splitlines():
            parts = line.split()
            if len(parts) > 1:
                providers.setdefault(parts[0], name)
    output = subprocess.check_output([str(llvm / "llvm-nm.exe"), "-D", "--undefined-only", "--format=posix", str(image)], text=True)
    required = [line.split()[0] for line in output.splitlines() if line.strip()]
    cpp_runtime = [name for name in required if name.startswith("_Z") or
                   name in {"__gxx_personality_v0", "__dynamic_cast", "__cxa_get_globals", "__cxa_get_globals_fast",
                            "__cxa_demangle", "__cxa_guard_acquire", "__cxa_guard_release", "__cxa_guard_abort", "__cxa_pure_virtual"}]
    if cpp_runtime:
        raise ValueError("Native C++ runtime ABI must remain static: " + ", ".join(sorted(cpp_runtime)))
    return {"schema": "ps5-qwen-native-import-audit-v1", "console_access": False,
            "image_sha256": sha(image), "weak_stubs_accepted_as_providers": False,
            "missing": sorted(set(required) - providers.keys()),
            "resolved": {name: providers[name] for name in required if name in providers}}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--workspace", type=Path, required=True)
    p.add_argument("--cache", type=Path, required=True)
    a = p.parse_args()
    result = audit(a.workspace, a.cache)
    target = a.cache / "build/application-native/import-audit.private.json"
    target.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"real_module_imports": len(result["resolved"]), "missing": result["missing"]}))
    if result["missing"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
