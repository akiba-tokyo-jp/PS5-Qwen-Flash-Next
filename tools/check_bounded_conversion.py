#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check actual pinned GGUF bytes and all metadata with bounded BF16 copies."""
import argparse
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from qwen_flash_next import json_write
from bounded_conversion import ChunkCursor, wrap_transforms, CHUNK_BYTES


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cache", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    from audit_conversion import expected_plan, inputs
    import numpy as np
    gguf, _, model_class, manifest, _, _ = inputs(args.cache)
    original_plan, _, _ = expected_plan(args.cache)
    original = model_class.modify_tensors
    wrapped, full_cursors, planned = wrap_transforms(original, original_plan, manifest, args.cache / "model", gguf, np)
    model_class.modify_tensors = wrapped
    try:
        bounded_plan, _, _ = expected_plan(args.cache)
    finally:
        model_class.modify_tensors = original
        for cursor in full_cursors.values(): cursor.close()
    assert original_plan == bounded_plan
    assert len(full_cursors) == len(planned) == 150
    assert all(cursor.next == 0 and cursor.maximum_read_bytes == 0 for cursor in full_cursors.values())

    source = args.out / "source.safetensors"
    values = ((np.arange(72, dtype=np.float32) - 36) / 16).view(np.uint32)
    raw = (values >> 16).astype("<u2").tobytes()
    source.write_bytes(b"metadata-prefix!" + raw)
    prefix = 16
    names = ("blk.0.ffn_gate_exps.weight", "token_embd.weight", "per_layer_token_embd.weight")
    toy_plan = dict(tensors={names[0]: dict(shape=[3, 2, 4], dtype="BF16", bytes=48),
                              names[1]: dict(shape=[2, 4], dtype="BF16", bytes=16),
                              names[2]: dict(shape=[2, 4], dtype="BF16", bytes=16)},
        raw_expert_copies=[dict(tensor=names[0], file=source.name, source_offset=prefix,
            size=16, count=3, source_stride=32, output_stride=16)],
        raw_embedding_copies=[dict(tensor=names[1], file=source.name, source_offset=prefix + 96,
            size=16, count=1, source_stride=0, output_stride=0)], ple_parts=["ple.0", "ple.1"])
    toy_manifest = dict(tensors={"ple.0": dict(file=source.name, file_offset=prefix + 112, shape=[1, 4]),
                                "ple.1": dict(file=source.name, file_offset=prefix + 120, shape=[1, 4])})
    def original_toy(*_):
        # No payload interface exists on these outputs: only their shape can
        # be examined before the replacement supplies its bounded data source.
        return [(name, SimpleNamespace(shape=value["shape"])) for name, value in toy_plan["tensors"].items()]
    wrapped, cursors, _ = wrap_transforms(original_toy, toy_plan, toy_manifest, args.out, gguf, np)
    output = args.out / "bounded-fixture.gguf"
    writer = gguf.GGUFWriter(output, "qwen4exp")
    for name, data in wrapped(None, None, "unused", None):
        writer.add_tensor(name, data.quantize(gguf.GGMLQuantizationType.BF16), raw_dtype=gguf.GGMLQuantizationType.BF16)
    writer.write_header_to_file(); writer.write_kv_data_to_file(); writer.write_tensors_to_file(); writer.close()
    expected = {names[0]: b"".join(raw[index * 32:index * 32 + 16] for index in range(3)),
                names[1]: raw[96:112], names[2]: raw[112:128]}
    reader = gguf.GGUFReader(output, "r")
    try:
        assert {tensor.name: tensor.data.tobytes() for tensor in reader.tensors} == expected
    finally:
        reader.data._mmap.close()
    assert all(cursor.next == len(cursor.parts) and cursor.stream is None for cursor in cursors.values())

    large = args.out / "chunk-bound.safetensors"
    with large.open("wb") as stream:
        for _ in range(18): stream.write(b"\x80\x3f" * (1 << 18))
    cursor = ChunkCursor(args.out, [(large.name, 0, large.stat().st_size)], 32, np)
    payload = args.out / "chunk-bound.bf16"
    tensor = gguf.LazyChunkedTensor(cursor.loaders(), shape=(large.stat().st_size // 64, 32), dtype=np.float32)
    with payload.open("wb") as stream: tensor.quantize(gguf.GGMLQuantizationType.BF16).tofile(stream)
    assert hashlib.sha256(payload.read_bytes()).digest() == hashlib.sha256(large.read_bytes()).digest()
    assert cursor.next == 2 and cursor.maximum_read_bytes <= CHUNK_BYTES and cursor.stream is None
    truncated = ChunkCursor(args.out, [(source.name, 999999, 8)], 4, np)
    try:
        truncated.load(0)
    except ValueError:
        assert truncated.next == 0 and truncated.stream is None
    else: raise AssertionError("Truncated source was admitted")
    try: cursor.load(0)
    except ValueError: pass
    else: raise AssertionError("Repeated source chunk was admitted")
    result = dict(all_1256_metadata_tensors_unchanged=True, all_150_original_copy_outputs_planned=True,
        metadata_learned_payload_bytes_read=0, actual_pinned_GGUF_copy_bytes="matched",
        actual_chunked_BF16_bytes="matched", chunk_limit_bytes=CHUNK_BYTES,
        maximum_source_read_bytes=cursor.maximum_read_bytes, truncation_and_repeat_rejected=True,
        console_access=False, learned_inference_performed=False, full_model_conversion_completed=False)
    json_write(args.out / "receipt.private.json", result)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
