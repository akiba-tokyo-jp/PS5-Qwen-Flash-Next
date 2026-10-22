#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Validate the linked emulated-BF16 matvec modules without console execution."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--workspace", type=Path, required=True)
    p.add_argument("--cache", type=Path, required=True)
    p.add_argument("--out", type=Path, help="Fresh evidence directory; preserve earlier shader checks")
    a = p.parse_args()
    linked = json.loads((a.cache / "build/application-native/receipt.private.json").read_text())
    image = Path(linked["artifact"]["path"]).read_bytes()
    image_hash = hashlib.sha256(image).hexdigest()
    if image_hash != linked["artifact"]["sha256"] or not linked["input_hashes_stable"]:
        raise ValueError("A stable matching native link is required")
    directory = a.cache / "build/llama-ps5/ggml/src/ggml-vulkan/vulkan-shaders.spv"
    binaries = a.workspace / "toolchain/msys-clang64/clang64/bin"
    env = dict(os.environ, PATH=str(binaries) + os.pathsep + os.environ.get("PATH", ""))
    out = a.out or a.cache / "build/bf16-shader-check"
    out.mkdir(parents=True, exist_ok=a.out is None)
    rows = []
    for suffix in ("", "_subgroup", "_subgroup_no_shmem"):
        name = "mul_mat_vec_bf16_f32_f32" + suffix
        path = directory / (name + ".spv")
        data = path.read_bytes()
        if len(data) < 20 or data[:4] != b"\x03\x02\x23\x07" or data not in image:
            raise ValueError("SPIR-V must be embedded byte-for-byte in the linked native image")
        validated = subprocess.run([str(binaries / "spirv-val.exe"), "--target-env", "vulkan1.3", str(path)],
                                   env=env, capture_output=True)
        (out / (name + "-validation.private.log")).write_bytes(validated.stdout + validated.stderr)
        if validated.returncode:
            raise RuntimeError("BF16 shader validation failed: " + name)
        assembly = subprocess.check_output([str(binaries / "spirv-dis.exe"), str(path)], env=env, text=True)
        (out / (name + ".private.spvasm")).write_text(assembly, encoding="utf-8")
        caps = sorted(set(re.findall(r"\bOpCapability\s+(\w+)", assembly)))
        if any(any(feature in cap for feature in ("BFloat", "CooperativeMatrix", "DotProduct")) for cap in caps):
            raise ValueError("The first fixture must not require native BF16, cooperative matrices or integer-dot features")
        rows.append({"name": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
                     "validation": "vulkan1.3", "capabilities": caps, "embedded_in_native_image": True})
    receipt = {"schema": "ps5-qwen-bf16-shader-check-v1", "native_image_sha256": image_hash,
               "modules": rows, "console_access": False, "GPU_execution": False, "full_model_qualified": False}
    (out / "receipt.private.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"linked_BF16_modules_validated": len(rows), "capabilities": [r["capabilities"] for r in rows],
                      "console_access": False, "GPU_execution": False}))


if __name__ == "__main__":
    main()
