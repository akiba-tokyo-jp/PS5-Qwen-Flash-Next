#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Bound original BF16 copies while retaining the pinned converter's transforms.

The upstream source tree is unchanged. Its normal dense transformations and
GGUF writer still run; independently planned expert/embedding/PLE byte copies
use its LazyChunkedTensor and BF16 formatter in bounded row-aligned chunks.
No learned forward pass or console access is performed.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
from qwen_flash_next import json_write, safe_name

CHUNK_BYTES = 8 << 20


def copy_plans(plan, manifest):
    result = {}
    for copy in plan["raw_expert_copies"] + plan["raw_embedding_copies"]:
        name = copy["tensor"]
        if name in result:
            raise ValueError("Duplicate original BF16 copy output")
        if copy["count"] > 1 and copy["output_stride"] != copy["size"]:
            raise ValueError("Original BF16 output rows must remain contiguous")
        result[name] = [(copy["file"], copy["source_offset"] + index * copy["source_stride"], copy["size"])
                        for index in range(copy["count"])]
    result["per_layer_token_embd.weight"] = [
        (manifest["tensors"][name]["file"], manifest["tensors"][name]["file_offset"],
         math.prod(manifest["tensors"][name]["shape"]) * 2) for name in plan["ple_parts"]]
    for name, spans in result.items():
        expected = plan["tensors"][name]
        row_bytes = expected["shape"][-1] * 2
        if expected["dtype"] != "BF16" or sum(size for _, _, size in spans) != expected["bytes"]:
            raise ValueError("Original BF16 copy byte count differs from its pinned plan")
        for filename, offset, size in spans:
            safe_name(filename)
            if type(offset) is not int or type(size) is not int or offset < 0 or size <= 0 or size % row_bytes:
                raise ValueError("Original BF16 copy span is not row aligned")
    return result


class ChunkCursor:
    """One read-only source descriptor at a time; each planned chunk loads once."""
    def __init__(self, root, spans, width, numpy, chunk_bytes=CHUNK_BYTES):
        self.root, self.numpy, self.width = Path(root), numpy, width
        row_bytes = width * 2
        if type(width) is not int or width <= 0 or row_bytes > chunk_bytes:
            raise ValueError("Original BF16 row exceeds the bounded converter chunk")
        self.limit = chunk_bytes // row_bytes * row_bytes
        self.parts = []
        for filename, offset, size in spans:
            safe_name(filename)
            if offset < 0 or size <= 0 or size % row_bytes:
                raise ValueError("Original BF16 source span is invalid")
            for at in range(0, size, self.limit):
                self.parts.append((filename, offset + at, min(self.limit, size - at)))
        self.next = 0
        self.stream = None
        self.filename = None
        self.maximum_read_bytes = 0

    def load(self, index):
        if index != self.next or index >= len(self.parts):
            raise ValueError("Original BF16 chunks must be read once in their exact order")
        filename, offset, size = self.parts[index]
        try:
            if filename != self.filename:
                self.close()
                path = self.root / filename
                if path.is_symlink():
                    raise ValueError("Original BF16 source must not be a symlink")
                self.stream = path.open("rb")
                self.filename = filename
            self.stream.seek(offset)
            raw = self.stream.read(size)
            if len(raw) != size:
                raise ValueError("Original BF16 source chunk is truncated")
            self.maximum_read_bytes = max(self.maximum_read_bytes, size)
            self.next += 1
            if self.next == len(self.parts): self.close()
            # Exact BF16-to-F32 widening; the unchanged pinned formatter writes
            # BF16 again. The independent final audit compares original bytes.
            values = self.numpy.frombuffer(raw, dtype="<u2").astype(self.numpy.uint32)
            values <<= self.numpy.uint32(16)
            return values.view(self.numpy.float32).reshape(-1, self.width)
        except BaseException:
            self.close()
            raise

    def close(self):
        if self.stream is not None:
            self.stream.close()
            self.stream = None
            self.filename = None

    def loaders(self):
        return [(lambda index=index: self.load(index)) for index in range(len(self.parts))]


def wrap_transforms(original, plan, manifest, model_root, gguf, numpy):
    copies = copy_plans(plan, manifest)
    cursors = {}

    def modify(model, tensor, name, bid):
        for mapped, output in original(model, tensor, name, bid):
            if mapped not in copies:
                yield mapped, output
                continue
            expected = plan["tensors"][mapped]
            if mapped in cursors or list(output.shape) != expected["shape"]:
                raise ValueError("Pinned BF16 copy output name or shape changed")
            cursor = ChunkCursor(model_root, copies[mapped], expected["shape"][-1], numpy)
            cursors[mapped] = cursor
            yield mapped, gguf.LazyChunkedTensor(cursor.loaders(), shape=tuple(expected["shape"]), dtype=numpy.float32)
    return modify, cursors, copies


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if not args.out.is_dir() or any(args.out.glob("*.gguf")):
        raise ValueError("Bounded conversion requires a new empty GGUF output directory")
    from audit_conversion import expected_plan, inputs, LOCK
    gguf, _, model_class, manifest, config, sources_before = inputs(args.cache)
    plan, _, _ = expected_plan(args.cache)
    import numpy
    import convert_hf_to_gguf
    architecture = convert_hf_to_gguf.get_model_architecture(config, convert_hf_to_gguf.ModelType.TEXT)
    if convert_hf_to_gguf.get_model_class(architecture, mmproj=False) is not model_class:
        raise ValueError("The actual text converter does not select the bounded Qwen class")
    upstream = args.cache / "upstream" / ("llama.cpp-" + LOCK["llama_cpp"]["revision"])
    original = model_class.modify_tensors
    adapter_before = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    wrapped, cursors, copies = wrap_transforms(original, plan, manifest, args.cache / "model", gguf, numpy)
    model_class.modify_tensors = wrapped
    try:
        sys.argv = [str(upstream / "convert_hf_to_gguf.py"), str(args.cache / "model"), "--outtype", "bf16",
                    "--outfile", str(args.out / "qwen-flash-next-bf16.gguf"), "--split-max-size", "4G"]
        convert_hf_to_gguf.main()
        if set(cursors) != set(copies) or any(cursor.next != len(cursor.parts) for cursor in cursors.values()):
            raise ValueError("The complete planned original BF16 copies were not streamed")
    finally:
        model_class.modify_tensors = original
        for cursor in cursors.values(): cursor.close()
    from convert_model import converter_sources
    archive = args.cache / ("llama-" + LOCK["llama_cpp"]["revision"] + ".zip")
    if converter_sources(archive, upstream) != sources_before or hashlib.sha256(Path(__file__).read_bytes()).hexdigest() != adapter_before:
        raise ValueError("Converter sources or bounded adapter changed during conversion")
    receipt = dict(schema="ps5-qwen-bounded-copy-adapter-v1", adapter_sha256=adapter_before,
        pinned_sources_modified=False, chunk_limit_bytes=CHUNK_BYTES,
        maximum_source_read_bytes=max(cursor.maximum_read_bytes for cursor in cursors.values()),
        streamed_tensors=len(cursors), streamed_BF16_bytes=sum(plan["tensors"][name]["bytes"] for name in cursors),
        complete_planned_copies_streamed=True, console_access=False, learned_inference_performed=False)
    json_write(args.out / "bounded-copy-receipt.private.json", receipt)
    print(json.dumps(receipt), flush=True)


if __name__ == "__main__":
    main()
