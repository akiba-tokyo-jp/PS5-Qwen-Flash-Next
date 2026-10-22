#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Audit original model layout using the pinned converter and metadata-only tensors.

No learned inference or console access is performed. Large tensors have no host
storage in the plan. GGUF inspection maps files read-only, and PLE verification
compares bounded byte ranges against every original PLE shard.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
import os
from pathlib import Path
import re
import struct
import sys
import time

from qwen_flash_next import json_write, safe_name

ROOT = Path(__file__).resolve().parents[1]
LOCK = json.loads((ROOT / "native/qwen_flash_next/dependencies.lock.json").read_text())
HASH_KEYS = {
    "ple_embedding.layer_multipliers": "qwen4exp.ple.layer_multipliers",
    "ple_embedding.ngram_heads_offsets": "qwen4exp.ple.head_offsets",
    "ple_embedding.ngram_heads_vocab_sizes": "qwen4exp.ple.head_vocab_sizes",
}


def inputs(cache):
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    from convert_model import converter_sources, digest
    upstream = cache / "upstream" / ("llama.cpp-" + LOCK["llama_cpp"]["revision"])
    archive = cache / ("llama-" + LOCK["llama_cpp"]["revision"] + ".zip")
    if digest(archive) != LOCK["llama_cpp"]["archive_sha256"]:
        raise ValueError("Pinned converter archive digest mismatch")
    identity = converter_sources(archive, upstream)
    sys.path[:0] = [str(upstream), str(upstream / "gguf-py")]
    import gguf
    import torch
    from conversion.qwen4exp import Qwen4ExpTextModel
    for module in (gguf, sys.modules[Qwen4ExpTextModel.__module__]):
        if not Path(module.__file__).resolve().is_relative_to(upstream.resolve()):
            raise ValueError("Audit imported a different converter tree")
    manifest = json.loads((cache / "metadata/checkpoint.json").read_text())
    config = json.loads((cache / "model/config.json").read_text())
    if (manifest["revision"] != LOCK["model"]["revision"] or manifest["quantization"] or
            config.get("quantization_config") or config["text_config"]["dtype"] != "bfloat16"):
        raise ValueError("Original BF16 model identity is required")
    return gguf, torch, Qwen4ExpTextModel, manifest, config, identity


def integer_values(cache, row):
    count = math.prod(row["shape"])
    if row["dtype"] != "I64" or not 0 < count <= 1024:
        raise ValueError("Invalid original PLE integer constants")
    with (cache / "model" / safe_name(row["file"])).open("rb") as stream:
        stream.seek(row["file_offset"])
        raw = stream.read(count * 8)
    if len(raw) != count * 8:
        raise ValueError("Truncated original PLE constants")
    return list(struct.unpack("<" + "q" * count, raw))


def placement(name, layers):
    match = re.match(r"^blk\.(\d+)\.", name)
    if match and int(match[1]) >= layers:
        return "skipped_mtp"
    if name == "per_layer_token_embd.weight":
        return "lazy_ple"
    if name == "token_embd.weight":
        return "mapped_embeddings"
    if ".ffn_" in name and "_exps.weight" in name:
        return "mapped_experts"
    return "device_weights"


def expected_plan(cache):
    gguf, torch, model_class, manifest, config, identity = inputs(cache)
    layers = config["text_config"]["num_hidden_layers"]
    if (layers, config["text_config"]["num_experts"], config["text_config"]["num_experts_per_tok"],
            config["text_config"]["hidden_size"]) != (48, 512, 10, 2560):
        raise ValueError("Original trunk and expert routing dimensions changed")
    excluded = []
    constants = {}
    original_names = {}
    raw_copies = []

    class MetadataModel(model_class):
        model_arch = model_class.model_arch

        def index_tensors(self, remote_hf_model_id=None):
            type(self)._original_block_count = layers
            type(self).opt_num_mtp_layers = 0
            indexed = {}
            for name, row in manifest["tensors"].items():
                if row["dtype"] == "I64":
                    values = integer_values(cache, row)
                    key = next((key for suffix, key in HASH_KEYS.items() if name.endswith(suffix)), None)
                    if key is None or key in constants:
                        raise ValueError("Unexpected or duplicate original integer constants")
                    constants[key] = values
                    gen = lambda values=values: torch.tensor(values, dtype=torch.int64)
                elif row["dtype"] == "BF16":
                    gen = lambda shape=row["shape"]: torch.empty(shape, dtype=torch.float32, device="meta")
                else:
                    raise ValueError("Unexpected original tensor precision")
                item = self.filter_tensors((name, gen))
                if item is None:
                    if "visual." not in name:
                        raise ValueError("A non-vision model component was excluded")
                    excluded.append(name)
                else:
                    if item[0] in indexed:
                        raise ValueError("Duplicate filtered model tensor")
                    indexed[item[0]] = item[1]
                    original_names[item[0]] = name
            return indexed

    model = MetadataModel(cache / "model", gguf.LlamaFileType.MOSTLY_BF16,
                          Path("unused-metadata-only.gguf"), dry_run=True)
    expected = {}
    forced_f32 = [gguf.MODEL_TENSOR.FFN_GATE_INP, gguf.MODEL_TENSOR.FFN_GATE_INP_SHEXP,
                  gguf.MODEL_TENSOR.SSM_CONV1D, gguf.MODEL_TENSOR.INDEXER_PROJ]
    for name, gen in model.model_tensors.items():
        if any(name.endswith(suffix) for suffix in HASH_KEYS):
            continue
        bid = next((int(part) for part in name.split(".") if part.isdecimal()), None)
        metadata = gen()
        if metadata.device.type != "meta":
            raise ValueError("Shape planning must not materialize learned tensors")
        for mapped, tensor in model.modify_tensors(metadata, name, bid):
            shape = [int(value) for value in tensor.shape]
            qtype = model.tensor_force_quant(name, mapped, bid, len(shape))
            if qtype is not False:
                raise ValueError("Unexpected precision override in pinned converter")
            f32 = (len(shape) <= 1 or mapped.endswith("_norm.weight") or
                   any(model.match_model_tensor_name(mapped, key, bid) for key in forced_f32) or
                   mapped[-7:] not in (".weight", ".lora_a", ".lora_b"))
            dtype = "F32" if f32 else "BF16"
            if mapped in expected or not shape or any(value <= 0 for value in shape):
                raise ValueError("Invalid converted tensor shape or duplicate name")
            expected[mapped] = {"shape": shape, "dtype": dtype,
                                "bytes": math.prod(shape) * (4 if f32 else 2),
                                "placement": placement(mapped, layers)}
            original = manifest["tensors"][original_names[name]]
            if name.endswith(("mlp.experts.down_proj", "mlp.experts.down_proj.weight")):
                if dtype != "BF16" or shape != original["shape"]:
                    raise ValueError("Original expert down projection must remain a BF16 copy")
                raw_copies.append({"tensor": mapped, "file": original["file"],
                                   "source_offset": original["file_offset"], "size": math.prod(shape) * 2,
                                   "count": 1, "source_stride": 0, "output_stride": 0})
            elif name.endswith(("mlp.experts.gate_up_proj", "mlp.experts.gate_up_proj.weight")):
                original_shape = original["shape"]
                if dtype != "BF16" or shape != [original_shape[0], original_shape[1] // 2, original_shape[2]]:
                    raise ValueError("Original expert gate/up split must remain BF16")
                size = math.prod(shape[1:]) * 2
                half = 0 if mapped.endswith(".ffn_gate_exps.weight") else 1
                if not mapped.endswith((".ffn_gate_exps.weight", ".ffn_up_exps.weight")):
                    raise ValueError("Unexpected converted expert gate/up name")
                raw_copies.append({"tensor": mapped, "file": original["file"],
                                   "source_offset": original["file_offset"] + half * size,
                                   "size": size, "count": shape[0], "source_stride": size * 2,
                                   "output_stride": size})
    if model._mtp_fc or (model._experts and any(model._experts)):
        raise ValueError("Converter left incomplete model components")
    if set(constants) != set(HASH_KEYS.values()):
        raise ValueError("Required PLE hash constants are missing")
    ple_parts = sorted((name for name in manifest["tensors"] if ".ngram_embedding.shard_" in name),
                       key=lambda name: int(name.rpartition(".shard_")[2].partition(".")[0]))
    if len(ple_parts) != config["text_config"]["split_ngram_parts"] or len(model._ple_shards) != len(ple_parts):
        raise ValueError("Every original PLE part must be present")
    if sorted(model._ple_shards) != list(range(len(ple_parts))):
        raise ValueError("Original PLE part indices are incomplete")
    if len(raw_copies) != model.block_count * 3:
        raise ValueError("Every original expert projection must have an exact byte-copy plan")
    footprint = Counter()
    largest = 0
    for name, row in expected.items():
        footprint[row["placement"]] += row["bytes"]
        if row["placement"] == "device_weights":
            largest = max(largest, row["bytes"])
        if row["placement"] == "mapped_experts" and row["shape"][0] != 512:
            raise ValueError("Every original expert must be retained")
    ple = expected.get("per_layer_token_embd.weight")
    if not ple or ple["dtype"] != "BF16" or ple["bytes"] != sum(
            math.prod(manifest["tensors"][name]["shape"]) * 2 for name in ple_parts):
        raise ValueError("The complete original BF16 PLE table is required")
    budget = {"expert_cache": 512 << 20, "context": 1024 << 20, "workspace": 512 << 20,
              "staging": 128 << 20, "cpu_working": 128 << 20, "os_reserve": 256 << 20,
              "direct_reserve": 512 << 20}
    plan = {"schema": "ps5-qwen-conversion-plan-v1", "original_revision": manifest["revision"],
            "converter_sources": identity, "trunk_layers": layers, "mtp_layers": model.block_count - layers,
            "tensor_count": len(expected), "tensors": expected, "ple_parts": ple_parts,
            "raw_expert_copies": raw_copies,
            "integer_constants": constants, "ple_layers": [value - 1 for value in config["text_config"]["ple_layer_ids"]],
            "text_lane_excluded_vision_tensors": excluded, "original_vision_shards_retained": True,
            "footprint_bytes": dict(footprint), "largest_device_tensor_bytes": largest,
            "budget_bytes": budget, "planned_device_requirement_bytes": footprint["device_weights"] + sum(budget.values()),
            "physical_memory_admitted": False, "original_shards_verified": False,
            "console_access": False, "learned_inference_performed": False}
    plan["tensor_layout_sha256"] = hashlib.sha256(json.dumps(expected, sort_keys=True).encode()).hexdigest()
    return plan, gguf, manifest


def inspect_gguf(path, gguf):
    reader = gguf.GGUFReader(path, "r")
    try:
        if reader.endianess != gguf.GGUFEndian.LITTLE:
            raise ValueError("Little-endian converted weights are required")
        fields = {key: (field.types, field.contents()) for key, field in reader.fields.items()
                  if key.startswith(("qwen4exp.", "general.architecture", "general.file_type", "split."))}
        tensors = {}
        spans = []
        for tensor in reader.tensors:
            if tensor.tensor_type not in (gguf.GGMLQuantizationType.BF16, gguf.GGMLQuantizationType.F32):
                raise ValueError("Reduced precision tensor in converted model")
            if tensor.name in tensors:
                raise ValueError("Duplicate tensor in a converted file")
            begin, end = int(tensor.data_offset), int(tensor.data_offset) + int(tensor.n_bytes)
            if begin < reader.data_offset or end > path.stat().st_size or begin % reader.alignment:
                raise ValueError("Converted tensor span exceeds its file or is unaligned")
            tensors[tensor.name] = {"shape": list(reversed([int(x) for x in tensor.shape])),
                                    "dtype": tensor.tensor_type.name, "bytes": int(tensor.n_bytes),
                                    "path": path.name, "offset": begin}
            spans.append((begin, end))
        spans.sort()
        if any(right[0] < left[1] for left, right in zip(spans, spans[1:])):
            raise ValueError("Overlapping converted tensor spans")
        return fields, tensors
    finally:
        # Explicitly close each read-only mapping before opening the next split.
        reader.data._mmap.close()


def compare_span(source, output, source_offset, output_offset, size, deadline, label="PLE"):
    source.seek(source_offset)
    output.seek(output_offset)
    remaining = size
    while remaining:
        if time.monotonic() >= deadline:
            raise TimeoutError("Host payload verification deadline exceeded")
        length = min(8 << 20, remaining)
        original, converted = source.read(length), output.read(length)
        if len(original) != length or converted != original:
            raise ValueError("Converted " + label + " bytes differ from the original BF16 data")
        remaining -= length


def audit_conversion(cache, out, files, progress=lambda *args, **kwargs: None, timeout_seconds=21600):
    plan, gguf, manifest = expected_plan(cache)
    actual = {}
    first_fields = None
    for index, path in enumerate(files):
        progress("auditing_converted_metadata", verified=index, total=len(files))
        fields, tensors = inspect_gguf(path, gguf)
        if index == 0:
            first_fields = fields
        if set(actual).intersection(tensors):
            raise ValueError("Duplicate tensor across converted splits")
        actual.update(tensors)
        if len(files) > 1:
            for key, value in (("split.count", len(files)), ("split.no", index)):
                if fields.get(key) != ([gguf.GGUFValueType.UINT16], value):
                    raise ValueError("Converted split sequence is incomplete or has an invalid type")
            if fields.get("split.tensors.count") != ([gguf.GGUFValueType.INT32], plan["tensor_count"]):
                raise ValueError("Converted split tensor count differs")
        elif any(key.startswith("split.") for key in fields):
            raise ValueError("Unexpected split metadata in an unsplit model")
    expected = plan["tensors"]
    if set(actual) != set(expected):
        raise ValueError("Converted tensor set differs from the complete original text/MTP plan")
    for name, row in expected.items():
        if any(actual[name][key] != row[key] for key in ("shape", "dtype", "bytes")):
            raise ValueError("Converted shape or precision mismatch: " + name)
    u32 = [gguf.GGUFValueType.UINT32]
    requirements = {"general.architecture": ([gguf.GGUFValueType.STRING], "qwen4exp"),
                    "general.file_type": (u32, int(gguf.LlamaFileType.MOSTLY_BF16)),
                    "qwen4exp.block_count": (u32, plan["trunk_layers"] + plan["mtp_layers"]),
                    "qwen4exp.nextn_predict_layers": (u32, plan["mtp_layers"]),
                    "qwen4exp.expert_count": (u32, 512), "qwen4exp.expert_used_count": (u32, 10),
                    "qwen4exp.embedding_length": (u32, 2560)}
    for key, expected_value in requirements.items():
        if first_fields.get(key) != expected_value:
            raise ValueError("Required original model metadata differs: " + key)
    layers = first_fields.get("qwen4exp.ple.layers")
    if layers != ([gguf.GGUFValueType.ARRAY, gguf.GGUFValueType.INT32], plan["ple_layers"]):
        raise ValueError("Required PLE layer assignment differs")
    for key, values in plan["integer_constants"].items():
        field = first_fields.get(key)
        if not field or field[0] not in ([gguf.GGUFValueType.ARRAY, gguf.GGUFValueType.INT64],
                                       [gguf.GGUFValueType.ARRAY, gguf.GGUFValueType.UINT64]) or field[1] != values:
            raise ValueError("Exact original PLE integer constants were not preserved: " + key)
    target = actual["per_layer_token_embd.weight"]
    offset = target["offset"]
    verified_bytes = 0
    deadline = time.monotonic() + timeout_seconds
    with (out / target["path"]).open("rb") as output:
        for number, name in enumerate(plan["ple_parts"]):
            row = manifest["tensors"][name]
            size = math.prod(row["shape"]) * 2
            progress("verifying_original_PLE_payload", verified=number, total=len(plan["ple_parts"]), bytes=verified_bytes)
            with (cache / "model" / safe_name(row["file"])).open("rb") as source:
                compare_span(source, output, row["file_offset"], offset, size, deadline)
            offset += size
            verified_bytes += size
    expert_bytes = 0
    for number, copy in enumerate(plan.get("raw_expert_copies", [])):
        progress("verifying_original_expert_payload", verified=number, total=len(plan["raw_expert_copies"]), bytes=expert_bytes)
        target = actual[copy["tensor"]]
        with (cache / "model" / safe_name(copy["file"])).open("rb") as source, (out / target["path"]).open("rb") as output:
            for index in range(copy["count"]):
                compare_span(source, output, copy["source_offset"] + index * copy["source_stride"],
                             target["offset"] + index * copy["output_stride"], copy["size"], deadline, "expert")
                expert_bytes += copy["size"]
    report = {key: value for key, value in plan.items() if key not in ("tensors", "ple_parts", "integer_constants", "raw_expert_copies")}
    report.update(schema="ps5-qwen-conversion-audit-v1", complete_tensor_set=True,
                  exact_shapes_and_precision=True, exact_PLE_integer_constants=True,
                  PLE_payload_bytes_verified=verified_bytes, PLE_parts_verified=len(plan["ple_parts"]),
                  expert_payload_bytes_verified=expert_bytes, expert_projection_tensors_verified=len(plan.get("raw_expert_copies", [])),
                  dense_payload_numerically_verified=False, original_shards_verified=True,
                  mapped_file_bytes=sum(path.stat().st_size for path in files))
    json_write(out / "conversion-audit.private.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--plan-out", type=Path, required=True)
    args = parser.parse_args()
    if args.plan_out.exists():
        parser.error("A fresh host plan output is required")
    plan, _, _ = expected_plan(args.cache.resolve())
    json_write(args.plan_out, plan)
    print(json.dumps({key: plan[key] for key in ("tensor_count", "footprint_bytes", "largest_device_tensor_bytes",
                                                 "planned_device_requirement_bytes", "physical_memory_admitted")}, indent=2))


if __name__ == "__main__":
    main()
