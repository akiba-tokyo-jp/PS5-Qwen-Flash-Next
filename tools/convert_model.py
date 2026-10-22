#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Convert the complete verified original checkpoint into BF16 GGUF on the host.

This preserves model precision and exact PLE constants through the pinned
upstream converter. It does not perform learned inference or console access.
The converter's Python dependencies must already be installed in this runtime.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import zipfile

from fetch_engine import source_relative
from qwen_flash_next import atomic_replace, json_write

ROOT = Path(__file__).resolve().parents[1]
LOCK = json.loads((ROOT / "native/qwen_flash_next/dependencies.lock.json").read_text())


def digest(path, deadline=None):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            if deadline is not None and time.monotonic() >= deadline:
                raise TimeoutError("Host file verification deadline exceeded")
            block = stream.read(8 << 20)
            if not block:
                break
            result.update(block)
    return result.hexdigest()


def converter_sources(archive, upstream):
    """Verify the executed Python tree, not only the downloaded source ZIP."""
    prefix = "llama.cpp-" + LOCK["llama_cpp"]["revision"]
    expected = {}
    with zipfile.ZipFile(archive) as bundle:
        for entry in bundle.infolist():
            if entry.is_dir() or not entry.filename.endswith(".py"):
                continue
            relative = source_relative(entry.filename, prefix)
            name = relative.as_posix()
            if name in expected:
                raise ValueError("Duplicate converter Python source")
            expected[name] = hashlib.sha256(bundle.read(entry)).hexdigest()
    actual = {}
    for path in upstream.rglob("*.py"):
        if path.is_symlink() or not path.resolve().is_relative_to(upstream.resolve()):
            raise ValueError("Converter Python source escapes the pinned source root")
        actual[path.relative_to(upstream).as_posix()] = digest(path)
    if not expected or expected != actual:
        raise ValueError("Executed converter Python sources differ from the pinned archive")
    identity = hashlib.sha256(json.dumps(expected, sort_keys=True).encode()).hexdigest()
    return {"python_files": len(expected), "python_tree_sha256": identity,
            "source_archive_sha256": LOCK["llama_cpp"]["archive_sha256"]}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cache", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--timeout-seconds", type=int, default=21600,
                   help="Maximum converter process duration; failures retain explicit status and partial output")
    a = p.parse_args()
    cache, out = a.cache.resolve(), a.out.resolve()
    if not 1 <= a.timeout_seconds <= 86400:
        p.error("timeout-seconds must be between 1 and 86400")
    manifest = json.loads((cache / "metadata/checkpoint.json").read_text())
    if manifest["revision"] != LOCK["model"]["revision"] or manifest["quantization"]:
        raise ValueError("Original model identity mismatch")
    missing = [row["name"] for row in manifest["files"] if not (cache / "model" / row["name"]).is_file()]
    if missing:
        raise ValueError(f"Original checkpoint is incomplete: {len(missing)} shards missing")
    if out.exists():
        raise ValueError("Conversion output must be a new directory")
    out.parent.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(out.parent).free < sum(row["bytes"] for row in manifest["files"]) + 32 * 1024**3:
        raise ValueError("Insufficient data-disk space for BF16 output and headroom")
    upstream = cache / "upstream" / ("llama.cpp-" + LOCK["llama_cpp"]["revision"])
    archive = cache / ("llama-" + LOCK["llama_cpp"]["revision"] + ".zip")
    if digest(archive) != LOCK["llama_cpp"]["archive_sha256"]:
        raise ValueError("Converter source archive identity mismatch")
    out.mkdir()
    started = time.monotonic()
    def status(phase, **fields):
        value = {"schema": "ps5-qwen-conversion-status-v1", "phase": phase,
                 "pid": os.getpid(), "updated_at": datetime.now(timezone.utc).isoformat(),
                 "elapsed_seconds": time.monotonic() - started,
                 "console_access": False, "learned_inference_performed": False, **fields}
        json_write(out / "conversion-status.private.json", value)
    try:
        status("verifying_converter_sources")
        source_identity = converter_sources(archive, upstream)
        preparation_tools = {name: digest(ROOT / "tools" / name) for name in (
            "convert_model.py", "bounded_conversion.py", "audit_conversion.py",
            "qwen_flash_next.py", "fetch_engine.py", "prepare_model.py")}
        status("verifying_original_shards", verified=0, total=len(manifest["files"]))
        verification_deadline = time.monotonic() + a.timeout_seconds
        for number, row in enumerate(manifest["files"], 1):
            path = cache / "model" / row["name"]
            if path.name != row["name"] or path.stat().st_size != row["bytes"] or digest(path, verification_deadline) != row["sha256"]:
                raise ValueError("Original shard verification failed: " + row["name"])
            status("verifying_original_shards", verified=number, total=len(manifest["files"]))
            print(f"Original shard verified: {number}/{len(manifest['files'])}", flush=True)
        command = [sys.executable, str(ROOT / "tools/bounded_conversion.py"), "--cache", str(cache), "--out", str(out)]
        status("converting_BF16", timeout_seconds=a.timeout_seconds, original_copy_chunk_limit_bytes=8 << 20)
        with (out / "conversion.private.log").open("w", encoding="utf-8") as stream:
            result = subprocess.run(command, cwd=upstream, stdout=stream, stderr=subprocess.STDOUT,
                                    timeout=a.timeout_seconds,
                                    env=dict(os.environ, HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1"))
        if result.returncode:
            raise RuntimeError("BF16 conversion failed; inspect conversion.private.log before resuming")
        adapter = json.loads((out / "bounded-copy-receipt.private.json").read_text())
        if (adapter.get("schema") != "ps5-qwen-bounded-copy-adapter-v1" or
            adapter.get("adapter_sha256") != preparation_tools["bounded_conversion.py"] or
            adapter.get("pinned_sources_modified") is not False or
            adapter.get("complete_planned_copies_streamed") is not True or
            adapter.get("chunk_limit_bytes") != 8 << 20 or
            not 0 < adapter.get("maximum_source_read_bytes", 0) <= 8 << 20 or
            adapter.get("streamed_tensors") != 150 or adapter.get("streamed_BF16_bytes") != 351568363520 or
            adapter.get("console_access") is not False or adapter.get("learned_inference_performed") is not False):
            raise ValueError("Complete bounded original-BF16 copy provenance is required")
        files = sorted(out.glob("*.gguf"))
        if not files:
            raise RuntimeError("Converter did not produce GGUF files")
        from audit_conversion import audit_conversion
        audit = audit_conversion(cache, out, files, status, a.timeout_seconds)
        outputs = []
        hashing_deadline = time.monotonic() + a.timeout_seconds
        for index, path in enumerate(files):
            status("hashing_converted_files", verified=index, total=len(files))
            outputs.append({"path": path.name, "bytes": path.stat().st_size, "sha256": digest(path, hashing_deadline)})
        if source_identity != converter_sources(archive, upstream):
            raise ValueError("Converter source identity changed during conversion")
        if preparation_tools != {name: digest(ROOT / "tools" / name) for name in preparation_tools}:
            raise ValueError("Application preparation sources changed during conversion or audit")
        receipt = {"schema": "ps5-qwen-bf16-conversion-v2", "original_revision": manifest["revision"],
                   "upstream_revision": LOCK["llama_cpp"]["revision"], "outtype": "bf16", "original_shards_verified": True,
                   "files": outputs, "converter_sources": source_identity,
                   "conversion_audit": audit,
                   "conversion_adapter": adapter, "preparation_tool_sources": preparation_tools,
                   "console_access": False, "learned_inference_performed": False}
        temporary_receipt = out / "model-receipt.next.private.json"
        with temporary_receipt.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(receipt, indent=2) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        atomic_replace(temporary_receipt, out / "model-receipt.json")
        status("completed", verified=len(files), total=len(files), receipt="model-receipt.json")
    except BaseException as error:
        (out / "model-receipt.json").unlink(missing_ok=True)
        status("failed", error_type=type(error).__name__, receipt_published=False)
        raise
    print("BF16 layout, complete PLE/expert payloads and file digests verified; console qualification is still required")


if __name__ == "__main__":
    main()
