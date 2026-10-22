#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Validate the additional linked F32 RMS/SiLU modules before native admission."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from qwen_flash_next import json_write


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--workspace", type=Path, required=True)
    p.add_argument("--cache", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args(); a.out.mkdir(parents=True, exist_ok=False)
    linked = json.loads((a.cache / "build/application-native/receipt.private.json").read_text())
    image = Path(linked["artifact"]["path"]).read_bytes()
    if hashlib.sha256(image).hexdigest() != linked["artifact"]["sha256"] or not linked["input_hashes_stable"]:
        raise ValueError("A stable exact native link is required")
    shader_root = a.cache / "build/llama-ps5/ggml/src/ggml-vulkan/vulkan-shaders.spv"
    binaries = a.workspace / "toolchain/msys-clang64/clang64/bin"
    env = dict(os.environ, PATH=str(binaries) + os.pathsep + os.environ.get("PATH", ""))
    rows = []
    for name in ("rms_norm_f32", "silu_f32"):
        path = shader_root / (name + ".spv"); data = path.read_bytes()
        if data[:4] != b"\x03\x02\x23\x07" or data not in image:
            raise ValueError("The actual F32 operation shader must be embedded byte-for-byte")
        result = subprocess.run([str(binaries / "spirv-val.exe"), "--target-env", "vulkan1.3", str(path)],
                                env=env, capture_output=True, timeout=30)
        (a.out / (name + "-validation.private.log")).write_bytes(result.stdout + result.stderr)
        if result.returncode: raise RuntimeError("Linked F32 operation shader validation failed")
        assembly = subprocess.check_output([str(binaries / "spirv-dis.exe"), str(path)], env=env, text=True, timeout=30)
        (a.out / (name + ".private.spvasm")).write_text(assembly)
        caps = sorted(set(re.findall(r"\bOpCapability\s+(\w+)", assembly)))
        if any(any(feature in cap for feature in ("BFloat", "CooperativeMatrix", "DotProduct")) for cap in caps):
            raise ValueError("The bounded operation stage must not require unsupported native arithmetic features")
        rows.append(dict(name=name, sha256=hashlib.sha256(data).hexdigest(), bytes=len(data), capabilities=caps))
    json_write(a.out / "receipt.private.json", dict(native_image_sha256=linked["artifact"]["sha256"],
        linked_F32_modules=rows, all_embedded_and_validated=True, console_access=False, GPU_execution=False))
    print(json.dumps(dict(linked_F32_modules_validated=len(rows), capabilities=[row["capabilities"] for row in rows], console_access=False)))


if __name__ == "__main__": main()
