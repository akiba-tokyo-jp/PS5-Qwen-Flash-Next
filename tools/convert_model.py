#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Convert the complete verified original checkpoint into BF16 GGUF on the host.

This preserves model precision and exact PLE constants through the pinned
upstream converter. It does not perform learned inference or console access.
The converter's Python dependencies must already be installed in this runtime.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
LOCK = json.loads((ROOT / "native/qwen_flash_next/dependencies.lock.json").read_text())


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cache", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    cache, out = a.cache.resolve(), a.out.resolve()
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
    for number, row in enumerate(manifest["files"], 1):
        path = cache / "model" / row["name"]
        if path.name != row["name"] or path.stat().st_size != row["bytes"] or digest(path) != row["sha256"]:
            raise ValueError("Original shard verification failed: " + row["name"])
        print(f"Original shard verified: {number}/{len(manifest['files'])}", flush=True)
    out.mkdir()
    command = [sys.executable, str(upstream / "convert_hf_to_gguf.py"), str(cache / "model"),
               "--outtype", "bf16", "--outfile", str(out / "qwen-flash-next-bf16.gguf"), "--split-max-size", "4G"]
    with (out / "conversion.private.log").open("w", encoding="utf-8") as stream:
        result = subprocess.run(command, cwd=upstream, stdout=stream, stderr=subprocess.STDOUT)
    if result.returncode:
        raise RuntimeError("BF16 conversion failed; inspect conversion.private.log before resuming")
    files = sorted(out.glob("*.gguf"))
    if not files:
        raise RuntimeError("Converter did not produce GGUF files")
    receipt = {"schema": "ps5-qwen-bf16-conversion-v1", "original_revision": manifest["revision"],
               "upstream_revision": LOCK["llama_cpp"]["revision"], "outtype": "bf16", "original_shards_verified": True,
               "files": [{"path": path.name, "bytes": path.stat().st_size, "sha256": digest(path)} for path in files],
               "console_access": False, "learned_inference_performed": False}
    (out / "model-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print("BF16 conversion and host file digests complete; console qualification is still required")


if __name__ == "__main__":
    main()
