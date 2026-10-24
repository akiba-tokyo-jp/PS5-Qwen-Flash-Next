#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Validate linked BF16 indexed-matrix, expert-count and activation-copy SPIR-V."""
import argparse
import hashlib
import json
import mmap
import os
from pathlib import Path
import re
import subprocess
from qwen_flash_next import json_write


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    linked = json.loads((args.cache / "build/application-native/receipt.private.json").read_text())
    path = Path(linked["artifact"]["path"])
    with path.open("rb") as file:
        digest = hashlib.file_digest(file, "sha256").hexdigest()
    if digest != linked["artifact"]["sha256"] or not linked["input_hashes_stable"]:
        raise ValueError("The exact stable native link is required")
    revision = linked["engine_build_provenance"]["upstream_revision"]
    if revision != "0a1ef309cdbb9f2024f58a38fb4c42352c5db569":
        raise ValueError("The pinned BF16 MoE implementation is required")
    implementation = args.cache / "upstream" / ("llama.cpp-" + revision) / "ggml/src/ggml-vulkan/ggml-vulkan.cpp"
    source = implementation.read_bytes()
    text = source.decode("utf-8")
    matrix_names = sorted(set(re.findall(r"\b(matmul_id(?:_subgroup)?_bf16(?:_fp32)?)_data\b", text)))
    expected_names = sorted("matmul_id" + subgroup + "_bf16" + precision
        for subgroup in ("", "_subgroup") for precision in ("", "_fp32"))
    if matrix_names != expected_names or re.search(r"\bmatmul_id(?:_subgroup)?_bf16_f16acc_(?:len|data)\b", text):
        raise ValueError("The scalar BF16 indexed path must reference the four expected F32 accumulation modules")
    binaries = args.workspace / "toolchain/msys-clang64/clang64/bin"
    env = dict(os.environ, PATH=str(binaries) + os.pathsep + os.environ.get("PATH", ""))
    shaders = args.cache / "build/llama-ps5/ggml/src/ggml-vulkan/vulkan-shaders.spv"
    names = ["count_experts", "count_experts_subgroup", "cpy_f32_bf16", "contig_cpy_f32_bf16"]
    names += matrix_names
    rows = []
    with path.open("rb") as file, mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ) as image:
        for name in names:
            shader = shaders / (name + ".spv")
            data = shader.read_bytes()
            if data[:4] != b"\x03\x02\x23\x07" or image.find(data) < 0:
                raise ValueError("An indexed MoE shader is not embedded byte-for-byte: " + name)
            result = subprocess.run([str(binaries / "spirv-val.exe"), "--target-env", "vulkan1.3", str(shader)],
                                    capture_output=True, env=env, timeout=30)
            (args.out / (name + "-validation.private.log")).write_bytes(result.stdout + result.stderr)
            if result.returncode:
                raise RuntimeError("Indexed MoE SPIR-V validation failed: " + name)
            assembly = subprocess.check_output([str(binaries / "spirv-dis.exe"), str(shader)], env=env, text=True, timeout=30)
            (args.out / (name + ".private.spvasm")).write_text(assembly)
            caps = sorted(set(re.findall(r"\bOpCapability\s+(\w+)", assembly)))
            if any(any(feature in cap for feature in ("BFloat", "CooperativeMatrix", "DotProduct")) for cap in caps):
                raise ValueError("The bounded MoE stage requires no native BF16, matrix-core or integer-dot capability")
            rows.append(dict(name=name, sha256=hashlib.sha256(data).hexdigest(), bytes=len(data), capabilities=caps))
    if implementation.read_bytes() != source:
        raise ValueError("The pinned shader implementation changed during validation")
    json_write(args.out / "receipt.private.json", dict(native_image_sha256=digest, modules=rows,
        implementation_sha256=hashlib.sha256(source).hexdigest(),
        scalar_BF16_matrix_data_references=matrix_names, unreferenced_F16_accumulation_modules_excluded=True,
        all_embedded_and_validated=True, console_access=False, GPU_execution=False, full_model_inference=False))
    print(json.dumps(dict(linked_MoE_modules_validated=len(rows), console_access=False)))


if __name__ == "__main__":
    main()
