#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check actual converter weight transforms using a few retained original tensors.

This writes small private format fixtures. It does not execute a learned model,
run matrix inference, contact a console or qualify hardware numerical behavior.
"""
import argparse
import copy
import math
from pathlib import Path
import shutil
import time

from audit_conversion import expected_plan, inspect_gguf, verify_dense_payload
from qwen_flash_next import json_write


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        parser.error("A fresh private fixture directory is required")
    plan, gguf, manifest, model, torch, original_names = expected_plan(args.cache, return_transformer=True)
    torch.set_num_threads(2)
    selected = []
    for suffix in (".linear_attn.A_log", ".attn_hyper_connection.hc_norm.weight",
                   ".linear_attn.in_proj_a.weight", ".self_attn.indexer.index_qk_proj.weight"):
        candidates = [name for name in plan["dense_source_tensors"] if name.endswith(suffix) and
                      (args.cache / "model" / manifest["tensors"][name]["file"]).is_file()]
        if not candidates:
            raise ValueError("A retained original dense fixture is unavailable: " + suffix)
        selected.append(candidates[0])
    args.out.mkdir(parents=True)
    json_write(args.out / "complete-plan.private.json", plan)
    valid = args.out / "original-dense-fixture.gguf"
    writer = gguf.GGUFWriter(valid, "qwen4exp")
    expected = set()
    for name in model.model_tensors:
        original = original_names[name]
        if original not in selected:
            continue
        row = manifest["tensors"][original]
        size = math.prod(row["shape"]) * 2
        if size > (64 << 20):
            raise ValueError("Retained dense fixture exceeds its host input bound")
        with (args.cache / "model" / row["file"]).open("rb") as stream:
            stream.seek(row["file_offset"])
            raw = bytearray(stream.read(size))
        if len(raw) != size:
            raise ValueError("Invalid retained dense fixture span")
        tensor = torch.frombuffer(raw, dtype=torch.bfloat16).reshape(row["shape"]).to(torch.float32)
        bid = next((int(part) for part in name.split(".") if part.isdecimal()), None)
        for mapped, transformed in model.modify_tensors(tensor, name, bid):
            qtype = gguf.GGMLQuantizationType[plan["tensors"][mapped]["dtype"]]
            writer.add_tensor(mapped, gguf.quantize(transformed.contiguous().numpy(), qtype), raw_dtype=qtype)
            expected.add(mapped)
    writer.write_header_to_file()
    writer.write_kv_data_to_file()
    writer.write_tensors_to_file()
    writer.close()
    _, actual = inspect_gguf(valid, gguf)
    fixture_plan = {"dense_source_tensors": selected}
    def verify(tensors, source_manifest=manifest, deadline=None):
        return verify_dense_payload(args.cache, args.out, fixture_plan, source_manifest, tensors, model, torch,
                                    original_names, gguf, deadline or time.monotonic() + 120,
                                    lambda *args, **kwargs: None)
    names, size = verify(actual)
    if names != expected or len(names) != 5:
        raise ValueError("Actual dense fixture coverage differs")
    changed = args.out / "mutated-dense-fixture.gguf"
    shutil.copyfile(valid, changed)
    target = next(reversed(actual.values()))
    with changed.open("r+b") as stream:
        position = target["offset"] + target["bytes"] - 1
        stream.seek(position)
        value = stream.read(1)
        stream.seek(position)
        stream.write(bytes([value[0] ^ 1]))
    mutated = {name: dict(row, path=changed.name) for name, row in actual.items()}
    try:
        verify(mutated)
    except ValueError:
        pass
    else:
        raise AssertionError("A changed actual dense payload was accepted")
    oversized = copy.deepcopy(manifest)
    oversized["tensors"][selected[0]]["shape"] = [1 << 26]
    try:
        verify(actual, oversized)
    except ValueError:
        pass
    else:
        raise AssertionError("An oversized dense source was accepted")
    json_write(args.out / "receipt.private.json", {"actual_original_dense_inputs": selected,
        "actual_converted_dense_tensors": len(names), "bytes_replayed": size,
        "modified_payload_rejected": True, "oversized_input_rejected": True,
        "source_input_limit_bytes": 64 << 20, "console_access": False,
        "learned_inference_performed": False, "hardware_numerical_quality_qualified": False})
    print("Actual exp, norm, V-head reordering and indexer splitting replayed; five outputs verified")
    print("Changed output bits and oversized source rejected; no model inference performed")


if __name__ == "__main__":
    main()
