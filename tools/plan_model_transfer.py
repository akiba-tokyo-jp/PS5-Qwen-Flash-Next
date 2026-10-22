#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Prepare an offline transfer plan only after complete original-model auditing."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import stat
import subprocess
from model_transport import REMOTE_ROOT, exclusive_json, source_identity, validate_file

ROOT = Path(__file__).resolve().parents[1]
PREPARATION_TOOLS = ("convert_model.py", "bounded_conversion.py", "audit_conversion.py",
                     "qwen_flash_next.py", "fetch_engine.py", "prepare_model.py")


def sha(path):
    with Path(path).open("rb") as stream: return hashlib.file_digest(stream, "sha256").hexdigest()


def metadata(path):
    info = path.stat()
    return dict(path=str(path), bytes=info.st_size, sha256=sha(path))


def preparation_gate(receipt, status):
    if (status.get("schema") != "ps5-qwen-conversion-status-v1" or status.get("phase") != "completed" or
            status.get("receipt") != "model-receipt.json" or status.get("console_access") is not False or
            status.get("learned_inference_performed") is not False):
        raise ValueError("Completed host conversion, audit and final hashes are required before a transfer plan")
    if "test_fixture_only" in receipt: raise ValueError("A metadata fixture cannot become a model transfer plan")
    if (receipt.get("schema") != "ps5-qwen-bf16-conversion-v2" or
            status.get("verified") != len(receipt.get("files", [])) or
            status.get("total") != len(receipt.get("files", []))):
        raise ValueError("All original converted files must have completed verification")
    tools = receipt.get("preparation_tool_sources", {})
    if set(tools) != set(PREPARATION_TOOLS) or any(sha(ROOT / "tools" / name) != tools[name] for name in PREPARATION_TOOLS):
        raise ValueError("Frozen preparation source provenance differs")
    adapter = receipt.get("conversion_adapter", {})
    if adapter.get("schema") == "ps5-qwen-resumed-copy-adapter-v1":
        from resume_provenance import validate_adapter
        validate_adapter(adapter, tools, receipt.get("resume_tool_sources", {}))
        return
    exact = dict(schema="ps5-qwen-bounded-copy-adapter-v1", adapter_sha256=tools["bounded_conversion.py"],
        pinned_sources_modified=False, complete_planned_copies_streamed=True, chunk_limit_bytes=8 << 20,
        streamed_tensors=150, streamed_BF16_bytes=351568363520, console_access=False, learned_inference_performed=False)
    if any(type(adapter.get(key)) is not type(value) or adapter[key] != value for key, value in exact.items()):
        raise ValueError("Complete original BF16 adapter provenance is required")
    maximum = adapter.get("maximum_source_read_bytes")
    if type(maximum) is not int or not 0 < maximum <= 8 << 20:
        raise ValueError("The original BF16 copy read bound differs")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--workspace", type=Path, required=True)
    p.add_argument("--cache", type=Path, required=True)
    p.add_argument("--receipt", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    receipt_path = a.receipt.resolve(); directory = receipt_path.parent
    if receipt_path.name != "model-receipt.json" or receipt_path.is_symlink() or not 0 < receipt_path.stat().st_size <= 1 << 20:
        raise ValueError("The bounded completed original receipt is required")
    receipt_bytes = receipt_path.read_bytes(); receipt = json.loads(receipt_bytes)
    status_path = directory / "conversion-status.private.json"
    status = json.loads(status_path.read_text())
    preparation_gate(receipt, status)
    rows = []; names = set()
    for row in receipt["files"]:
        name = validate_file(row)
        if name in names: raise ValueError("Duplicate model split")
        names.add(name); source = directory / name
        info = source.stat()
        if source.is_symlink() or not stat.S_ISREG(info.st_mode) or info.st_size != row["bytes"]:
            raise ValueError("Original split metadata differs before transfer planning")
        rows.append(dict(original=row, source=str(source), source_identity=source_identity(info)))
    if {path.name for path in directory.glob("*.gguf")} != names:
        raise ValueError("The complete converted GGUF directory must match its receipt")
    a.out.mkdir(parents=True, exist_ok=False)
    host = a.workspace / "toolchain/msys-clang64/clang64/bin"
    lock = json.loads((ROOT / "native/qwen_flash_next/dependencies.lock.json").read_text())
    upstream = a.cache / "upstream" / ("llama.cpp-" + lock["llama_cpp"]["revision"])
    source = ROOT / "tools/model_transfer_receipt.cpp"
    inputs = [source, ROOT / "native/app/model_receipt.h", ROOT / "native/app/memory_admission.h",
              upstream / "vendor/nlohmann/json.hpp", host / "clang++.exe"]
    before = [metadata(path) for path in inputs]
    env = dict(os.environ, PATH=str(host) + os.pathsep + os.environ.get("PATH", ""))
    executable = a.out / "model-transfer-receipt.exe"
    command = [str(host / "clang++.exe"), "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror",
        "-I", str(ROOT / "native/app"), "-I", str(upstream / "vendor"), str(source), "-o", str(executable)]
    result = subprocess.run(command, env=env, capture_output=True, timeout=120)
    (a.out / "compile.private.log").write_bytes(result.stdout + result.stderr)
    if result.returncode: raise RuntimeError("Actual native receipt gate compilation failed")
    result = subprocess.run([str(executable), str(receipt_path)], env=env, capture_output=True, timeout=30)
    (a.out / "native-gate.private.log").write_bytes(result.stdout + result.stderr)
    if result.returncode: raise ValueError("The actual native full-original receipt gate rejected transfer planning")
    native = json.loads(result.stdout)
    total = sum(row["original"]["bytes"] for row in rows)
    if not native["native_receipt_gate_passed"] or native["mapped_file_bytes"] != total or native["files"] != len(rows):
        raise ValueError("The actual native receipt result differs from the complete transfer plan")
    if before != [metadata(path) for path in inputs] or receipt_path.read_bytes() != receipt_bytes:
        raise ValueError("Transfer-plan validation inputs changed")
    for row in rows:
        if tuple(row["source_identity"]) != source_identity(Path(row["source"]).stat()):
            raise ValueError("Original split metadata changed during planning")
    (a.out / "model-receipt.private.json").write_bytes(receipt_bytes)
    plan = dict(schema="ps5-qwen-model-transfer-plan-v1", nonce=secrets.token_hex(16),
        original_receipt=metadata(receipt_path), receipt_copy=metadata(a.out / "model-receipt.private.json"),
        source_directory=str(directory), files=rows, total_bytes=total, remote_root=REMOTE_ROOT,
        required_storage_bytes=total + len(receipt_bytes) + (32 << 30), storage_reserve_bytes=32 << 30,
        maximum_upload_connections=1, file_timeout_seconds=21600,
        native_receipt_gate=native, validator=metadata(executable), validator_inputs=before,
        compile_command=command, input_hashes_stable=True, console_access=False,
        learned_inference_performed=False, remote_payload_SHA_verified=False,
        requires_fresh_idle_capacity_and_owned_directory_admission=True)
    exclusive_json(a.out / "plan.private.json", plan)
    print(json.dumps(dict(offline_transfer_plan=True, files=len(rows), total_bytes=total,
        maximum_upload_connections=1, console_access=False, remote_payload_SHA_verified=False)))


if __name__ == "__main__": main()
