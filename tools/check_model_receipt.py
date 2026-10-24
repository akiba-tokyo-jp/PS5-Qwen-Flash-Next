#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Test the actual native receipt gate using a clearly marked metadata fixture."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

from qwen_flash_next import json_write

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        parser.error("A fresh host metadata check directory is required")
    args.out.mkdir(parents=True)
    plan = json.loads(args.plan.read_text())
    lock_path = ROOT / "native/qwen_flash_next/dependencies.lock.json"
    lock = json.loads(lock_path.read_text())
    mapped = sum(row["bytes"] for row in plan["tensors"].values()) + (1 << 20)
    raw = plan["raw_expert_copies"] + plan["raw_embedding_copies"]
    dense = len(plan["tensors"]) - len(raw) - 1
    dense_bytes = sum(row["bytes"] for row in plan["tensors"].values()) - plan["footprint_bytes"]["lazy_ple"] - sum(row["count"] * row["size"] for row in raw)
    audit = {"schema": "ps5-qwen-conversion-audit-v2", "original_revision": lock["model"]["revision"],
        "tensor_layout_sha256": plan["tensor_layout_sha256"], "converter_sources": plan["converter_sources"],
        "tensor_count": plan["tensor_count"], "trunk_layers": plan["trunk_layers"], "mtp_layers": plan["mtp_layers"],
        "complete_tensor_set": True, "exact_shapes_and_precision": True, "exact_PLE_integer_constants": True,
        "complete_converted_tensor_payload_verified": True, "original_shards_verified": True,
        "physical_memory_admitted": False, "console_access": False, "learned_inference_performed": False,
        "PLE_parts_verified": len(plan["ple_parts"]), "PLE_payload_bytes_verified": plan["footprint_bytes"]["lazy_ple"],
        "expert_projection_tensors_verified": len(plan["raw_expert_copies"]),
        "expert_payload_bytes_verified": sum(row["count"] * row["size"] for row in plan["raw_expert_copies"]),
        "embedding_payload_bytes_verified": sum(row["size"] for row in plan["raw_embedding_copies"]),
        "dense_tensors_replayed": dense, "dense_payload_bytes_replayed": dense_bytes, "mapped_file_bytes": mapped}
    fixture = args.out / "metadata-fixture.private.json"
    json_write(fixture, {"schema": "ps5-qwen-bf16-conversion-v2", "test_fixture_only": True,
        "original_revision": lock["model"]["revision"], "upstream_revision": lock["llama_cpp"]["revision"],
        "outtype": "bf16", "original_shards_verified": True, "console_access": False,
        "learned_inference_performed": False, "converter_sources": plan["converter_sources"], "conversion_audit": audit,
        "files": [{"path": "nonexistent-fixture.gguf", "sha256": "0" * 64, "bytes": mapped}]})
    oversized = args.out / "oversized-metadata.private.json"
    oversized.write_bytes(b" " * ((1 << 20) + 1))
    host = args.workspace / "toolchain/msys-clang64/clang64/bin"
    upstream = args.cache / "upstream" / ("llama.cpp-" + lock["llama_cpp"]["revision"])
    env = dict(os.environ, PATH=str(host) + os.pathsep + os.environ.get("PATH", ""))
    exe = args.out / "model-receipt.exe"
    command = [str(host / "clang++.exe"), "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror",
               "-I", str(ROOT / "native/app"), "-I", str(upstream / "vendor"),
               str(ROOT / "tests/model_receipt.cpp"), "-o", str(exe)]
    result = subprocess.run(command, env=env, capture_output=True, timeout=120)
    (args.out / "compile.private.log").write_bytes(result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError("Native receipt verifier compilation failed")
    result = subprocess.run([str(exe), str(fixture), str(oversized), str(lock_path)], env=env, capture_output=True, timeout=30)
    (args.out / "run.private.log").write_bytes(result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError("Native model receipt checks failed")
    json_write(args.out / "receipt.private.json", {"native_model_receipt_gate": "passed",
        "native_header_sha256": hashlib.sha256((ROOT / "native/app/model_receipt.h").read_bytes()).hexdigest(),
        "plan_sha256": hashlib.sha256(args.plan.read_bytes()).hexdigest(), "console_access": False,
        "model_data_read": False, "model_loaded": False, "GPU_initialized": False,
        "learned_inference_performed": False, "fixture_is_not_a_model_receipt": True})
    print(result.stdout.decode("utf-8", "replace"), end="")


if __name__ == "__main__":
    main()
