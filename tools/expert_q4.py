#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Prepare pinned, Expert-only Q4_0 assets without inference or console access."""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
LOCK = json.loads((ROOT/"native/qwen_flash_next/dependencies.lock.json").read_text())
EXPERT = re.compile(r"blk\.(\d+)\.ffn_(gate|up|down)_exps\.weight\Z")
READ_ALIGNMENT = 16384
Q4_BLOCK_VALUES, Q4_BLOCK_BYTES = 32, 18
MATRIX_VALUES = 2560*640
MATRIX_Q4_BYTES = MATRIX_VALUES//Q4_BLOCK_VALUES*Q4_BLOCK_BYTES


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def record(path):
    path = Path(path)
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return dict(path=str(path.resolve()), bytes=path.stat().st_size, sha256=digest)


def write_json(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix+".tmp")
    temporary.write_text(json.dumps(value, indent=2)+"\n", encoding="utf-8")
    os.replace(temporary, path)


def pinned_gguf(cache):
    revision = LOCK["llama_cpp"]["revision"]
    source = cache/"upstream"/("llama.cpp-"+revision)
    archive = cache/("llama-"+revision+".zip")
    require(record(archive)["sha256"] == LOCK["llama_cpp"]["archive_sha256"], "Pinned source archive changed")
    with zipfile.ZipFile(archive) as bundle:
        files = [x for x in bundle.namelist() if "/gguf-py/gguf/" in x and x.endswith(".py")]
        require(bool(files), "The pinned GGUF package is missing")
        for name in files:
            relative = name.split("/gguf-py/", 1)[1]
            require((source/"gguf-py"/relative).read_bytes() == bundle.read(name), "Pinned GGUF source changed: "+relative)
    sys.path.insert(0, str(source/"gguf-py"))
    import gguf
    import numpy as np
    require(Path(gguf.__file__).resolve().is_relative_to(source.resolve()), "Unexpected GGUF package")
    return gguf, np


def inventory(cache, directory):
    gguf, _ = pinned_gguf(cache)
    receipt_path = directory/"model-receipt.json"
    receipt = json.loads(receipt_path.read_text())
    require(receipt["original_revision"] == LOCK["model"]["revision"] and
            receipt["upstream_revision"] == LOCK["llama_cpp"]["revision"] and receipt["outtype"] == "bf16",
            "The preserved complete BF16 conversion is required")
    tensors, files = [], []
    for item in receipt["files"]:
        path = directory/item["path"]
        require(path.is_file() and path.stat().st_size == item["bytes"], "Original GGUF size changed")
        reader = gguf.GGUFReader(path, "r")
        require(reader.byte_order == "I" and reader.data_offset <= 32 << 20, "Bounded little-endian GGUF required")
        selected, unchanged = 0, 0
        for tensor in reader.tensors:
            match = EXPERT.fullmatch(tensor.name)
            row = dict(name=tensor.name, file=item["path"], offset=int(tensor.data_offset),
                bytes=int(tensor.n_bytes), shape=[int(x) for x in tensor.shape], original_type=tensor.tensor_type.name)
            if match:
                layer, role = int(match[1]), match[2]
                require(tensor.tensor_type == gguf.GGMLQuantizationType.BF16 and row["shape"] in (
                    [2560, 640, 512], [640, 2560, 512]), "Original routed Expert layout differs")
                require(row["shape"][0] % Q4_BLOCK_VALUES == 0, "Expert row is not Q4_0 compatible")
                row.update(layer=layer, role=role, q4_bytes=math.prod(row["shape"])*18//32, quantize=True)
                selected += row["bytes"]
            else:
                row["quantize"] = False
                unchanged += row["bytes"]
            tensors.append(row)
        files.append(dict(original=item, header_bytes=int(reader.data_offset), expert_bytes=selected,
            unchanged_payload_bytes=unchanged, replacement_required=selected > 0))
        del reader
    experts = [x for x in tensors if x["quantize"]]
    require(len({x["name"] for x in tensors}) == len(tensors) == 1256, "Complete unique original tensor set required")
    require({(x["layer"], x["role"]) for x in experts} == {(l, r) for l in range(49) for r in ("gate", "up", "down")},
            "All original Expert tensors, including MTP, must remain present")
    return dict(schema="ps5-qwen-expert-q4-inventory-v1", original_receipt=record(receipt_path),
        upstream_revision=LOCK["llama_cpp"]["revision"], format="Q4_0", effective_bits_per_weight=4.5,
        quantized_expert_tensors=len(experts), original_expert_bytes=sum(x["bytes"] for x in experts),
        q4_expert_bytes=sum(x["q4_bytes"] for x in experts), non_expert_tensors_unchanged=True,
        files=files, tensors=tensors, console_operations=0, model_inference=False)


def independent_dequantize(raw, np):
    blocks = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 18)
    scales = blocks[:, :2].copy().view("<f2").astype(np.float32)
    low = (blocks[:, 2:] & 15).astype(np.int16)-8
    high = (blocks[:, 2:] >> 4).astype(np.int16)-8
    return np.concatenate((low, high), axis=1).astype(np.float32)*scales


def prepare_samples(cache, source_receipt, out):
    gguf, np = pinned_gguf(cache)
    original = json.loads(source_receipt.read_text())
    require(original["schema"] == "ps5-qwen-bf16-lossless-host-screen-v1", "Original 27-matrix sample provenance required")
    out.mkdir(parents=True, exist_ok=False)
    manifest = dict(schema="ps5-qwen-expert-q4-samples-v1", format="Q4_0", original_source_receipt=record(source_receipt),
        upstream_revision=LOCK["llama_cpp"]["revision"], matrices=[], non_expert_weights_modified=False,
        console_operations=0, model_inference=False, completed=False)
    pack_path = out/"expert-q4-samples.bin"
    started = time.monotonic()
    with pack_path.open("xb") as pack:
        for index, item in enumerate(original["samples"]):
            source = item["original"]
            actual = record(source["path"])
            require(all(actual[k] == source[k] for k in ("bytes", "sha256")), "Preserved original Expert sample changed")
            raw = Path(source["path"]).read_bytes()
            require(len(raw) == MATRIX_VALUES*2, "Original Expert matrix byte count differs")
            values = (np.frombuffer(raw, dtype="<u2").astype(np.uint32) << 16).view(np.float32)
            require(bool(np.isfinite(values).all()), "Original Expert sample is nonfinite")
            encoded = gguf.quants.quantize(values, gguf.GGMLQuantizationType.Q4_0).tobytes()
            require(len(encoded) == MATRIX_Q4_BYTES, "Q4_0 matrix payload size differs")
            decoded = independent_dequantize(encoded, np).reshape(-1)
            upstream = gguf.quants.dequantize(np.frombuffer(encoded, dtype=np.uint8), gguf.GGMLQuantizationType.Q4_0)
            require(np.array_equal(decoded, upstream), "Independent and pinned Q4_0 decoding disagree")
            require(bool(np.isfinite(decoded).all()), "Q4_0 decoding became nonfinite")
            difference = decoded.astype(np.float64)-values
            rms = float(np.sqrt(np.mean(difference*difference)))
            ref_rms = float(np.sqrt(np.mean(values.astype(np.float64)**2)))
            columns, rows = (640, 2560) if item["role"] == "down" else (2560, 640)
            # Reference input is deterministic and F32; this is a component
            # arithmetic reference, never a model answer-quality measurement.
            input_values = ((np.arange(columns, dtype=np.int32) % 13)-6).astype(np.float32)/np.float32(1009)
            reference = decoded.reshape(rows, columns).astype(np.float64) @ input_values.astype(np.float64)
            original_reference = values.reshape(rows, columns).astype(np.float64) @ input_values.astype(np.float64)
            entry = dict(layer=item["layer"], role=item["role"], expert=item["expert"], columns=columns, rows=rows,
                original=source, q4_payload_bytes=len(encoded), q4_payload_sha256=sha(encoded),
                weight_RMSE=rms, weight_NRMSE=rms/ref_rms, maximum_weight_absolute_error=float(np.max(abs(difference))),
                component_output_NRMSE=float(np.linalg.norm(reference-original_reference)/np.linalg.norm(original_reference)),
                independent_dequantization_exact=True, model_quality_qualified=False)
            for label, content in (("bf16", raw), ("q4", encoded), ("reference_f64", reference.astype("<f8").tobytes())):
                padding = (-pack.tell()) % READ_ALIGNMENT
                pack.write(bytes(padding))
                entry[label+"_offset"] = pack.tell()
                entry[label+"_bytes"] = len(content)
                pack.write(content)
            manifest["matrices"].append(entry)
            write_json(out/"manifest.partial.private.json", manifest)
            print(json.dumps(dict(matrix=index+1, total=len(original["samples"]), weight_NRMSE=entry["weight_NRMSE"])), flush=True)
        pack.write(bytes((-pack.tell()) % READ_ALIGNMENT))
        pack.flush()
        os.fsync(pack.fileno())
    require(len(manifest["matrices"]) == 27, "All original representative matrices are required")
    manifest.update(completed=True, pack=record(pack_path), elapsed_seconds=time.monotonic()-started,
        payload_fraction=MATRIX_Q4_BYTES/(MATRIX_VALUES*2), native_model_speed_qualified=False)
    write_json(out/"manifest.private.json", manifest)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    sub = parser.add_subparsers(dest="mode", required=True)
    inv = sub.add_parser("inventory")
    inv.add_argument("--original", type=Path, required=True)
    samples = sub.add_parser("samples")
    samples.add_argument("--source-receipt", type=Path, required=True)
    args = parser.parse_args()
    if args.mode == "inventory":
        require(not args.out.exists(), "Inventory output must be new")
        result = inventory(args.cache, args.original)
        write_json(args.out, result)
        print(json.dumps({k: result[k] for k in ("quantized_expert_tensors", "original_expert_bytes", "q4_expert_bytes")}))
    else:
        result = prepare_samples(args.cache, args.source_receipt, args.out)
        print(json.dumps(dict(completed=True, matrices=len(result["matrices"]), elapsed_seconds=result["elapsed_seconds"])))


if __name__ == "__main__":
    main()
