#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise the actual pinned GGUF writer/reader against malformed host fixtures."""
import argparse
import importlib
from pathlib import Path
import shutil
import sys

from audit_conversion import inspect_gguf, LOCK
from qwen_flash_next import json_write


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        parser.error("A fresh fixture output directory is required")
    upstream = args.cache / "upstream" / ("llama.cpp-" + LOCK["llama_cpp"]["revision"])
    sys.path.insert(0, str(upstream / "gguf-py"))
    gguf = importlib.import_module("gguf")
    import numpy as np
    if not Path(gguf.__file__).resolve().is_relative_to(upstream.resolve()):
        raise ValueError("Fixture writer is not the selected upstream implementation")
    args.out.mkdir(parents=True)
    results = {}

    def create(name, dtype, big_endian=False, second=False):
        path = args.out / (name + ".gguf")
        writer = gguf.GGUFWriter(path, "qwen4exp", endianess=gguf.GGUFEndian.BIG if big_endian else gguf.GGUFEndian.LITTLE)
        writer.add_ple_layer_multipliers([2 ** 45 + 1, 3])
        writer.add_ple_layers([1])
        values = np.arange(6, dtype=np.float32).reshape(2, 3)
        data = gguf.quants.quantize(values, dtype)
        writer.add_tensor("fixture.weight", data, raw_dtype=dtype)
        if second:
            writer.add_tensor("second.weight", data, raw_dtype=dtype)
        writer.write_header_to_file()
        writer.write_kv_data_to_file()
        writer.write_tensors_to_file()
        writer.close()
        return path

    def reject(name, path):
        try:
            inspect_gguf(path, gguf)
        except (ValueError, TypeError, IndexError):
            results[name] = "rejected"
        else:
            raise AssertionError("Malformed fixture was accepted: " + name)

    valid = create("original-bf16", gguf.GGMLQuantizationType.BF16)
    fields, tensors = inspect_gguf(valid, gguf)
    assert tensors["fixture.weight"]["shape"] == [2, 3]
    assert tensors["fixture.weight"]["bytes"] == 12
    assert fields["qwen4exp.ple.layer_multipliers"] == ([gguf.GGUFValueType.ARRAY, gguf.GGUFValueType.UINT64], [2 ** 45 + 1, 3])
    assert fields["qwen4exp.ple.layers"] == ([gguf.GGUFValueType.ARRAY, gguf.GGUFValueType.INT32], [1])
    results["original_BF16_dimensions_and_64bit_integers"] = "passed"
    _, wide = inspect_gguf(create("widened-f32", gguf.GGMLQuantizationType.F32), gguf)
    assert wide["fixture.weight"]["dtype"] == "F32" and wide["fixture.weight"]["bytes"] == 24
    results["F32_storage"] = "passed"
    reject("F16_reduction", create("reduced-f16", gguf.GGMLQuantizationType.F16))
    reject("big_endian", create("big-endian", gguf.GGMLQuantizationType.BF16, big_endian=True))
    truncated = args.out / "truncated.gguf"
    shutil.copyfile(valid, truncated)
    with truncated.open("r+b") as stream:
        stream.truncate(tensors["fixture.weight"]["offset"] + 10)
    reject("truncated_payload", truncated)
    overlap = create("overlapping", gguf.GGMLQuantizationType.BF16, second=True)
    reader = gguf.GGUFReader(overlap, "r+")
    reader.tensors[1].field.parts[-1][0] = reader.tensors[0].field.parts[-1][0]
    reader.data.flush()
    reader.data._mmap.close()
    reject("overlapping_tensor_spans", overlap)
    json_write(args.out / "receipt.private.json", {"checks": results, "console_access": False,
                                                   "learned_inference_performed": False})
    for name, result in results.items():
        print(name + ": " + result)


if __name__ == "__main__":
    main()
