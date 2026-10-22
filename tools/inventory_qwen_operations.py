#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Record a lexical source inventory, not runtime operation support or coverage."""
import argparse
import hashlib
import json
from pathlib import Path
import re
from model_transport import exclusive_json

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cache", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    lock = json.loads((ROOT / "native/qwen_flash_next/dependencies.lock.json").read_text())
    upstream = a.cache / "upstream" / ("llama.cpp-" + lock["llama_cpp"]["revision"])
    build = json.loads((a.cache / "build/llama-ps5/receipt.private.json").read_text())
    if build["upstream_revision"] != lock["llama_cpp"]["revision"] or build["compile_returncode"] != 0:
        raise ValueError("The pinned built engine receipt is required")
    config_path = a.cache / "model/config.json"
    config_bytes = config_path.read_bytes(); config = json.loads(config_bytes)["text_config"]
    expected = dict(hidden_size=2560, num_hidden_layers=48, num_experts=512, num_experts_per_tok=10,
        linear_key_head_dim=128, linear_value_head_dim=128, full_attention_interval=4,
        hc_count=4, indexer_head_dim=128, indexer_budget=2048, indexer_compress_ratio=4,
        ngram_size=3, heads_per_ngram=8, split_ngram_parts=128, ple_conv_kernel_size=4)
    if any(config.get(key) != value for key, value in expected.items()) or config.get("ple_layer_ids") != [2]:
        raise ValueError("The complete pinned original Qwen configuration differs")
    paths = ["src/models/qwen4exp.cpp", "src/llama-graph.cpp", "ggml/src/ggml.c",
             "ggml/src/ggml-vulkan/ggml-vulkan.cpp"]
    sources = []
    for path in paths:
        data = (upstream / path).read_bytes()
        sources.append(dict(path=path, bytes=len(data), sha256=hashlib.sha256(data).hexdigest()))
    text = (upstream / paths[0]).read_text()
    # Comments may mention intentionally unused APIs, such as conv_1d_dw.
    lexical = re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.S)
    direct = sorted(set(re.findall(r"\b(ggml_[a-z0-9_]+)\s*\(", lexical)))
    helpers = sorted(set(re.findall(r"\b(build_[a-z0-9_]+)\s*\(", lexical)))
    backend = (upstream / paths[-1]).read_text()
    required_cases = ["GGML_OP_DSV4_HC_PRE", "GGML_OP_DSV4_HC_POST", "GGML_OP_DSV4_HC_COMB",
        "GGML_OP_LIGHTNING_INDEXER", "GGML_OP_GATED_DELTA_NET", "GGML_OP_SSM_CONV",
        "GGML_OP_MUL_MAT_ID", "GGML_OP_GET_ROWS", "GGML_OP_TOP_K", "GGML_OP_CUMSUM"]
    result = dict(schema="ps5-qwen-operation-source-inventory-v1", upstream_revision=lock["llama_cpp"]["revision"],
        original_revision=lock["model"]["revision"], configuration_sha256=hashlib.sha256(config_bytes).hexdigest(),
        configuration_geometry=expected, PLE_layer_ids=config["ple_layer_ids"], sources=sources,
        application_patches=build["upstream_patches"], direct_GGML_API_names=direct, graph_helper_names=helpers,
        backend_case_text_present={name: bool(re.search(r"\bcase\s+" + name + r"\s*:", backend)) for name in required_cases},
        lexical_inventory_only=True, complete_transitive_graph_coverage=False,
        runtime_support_proven=False, PS5_execution=False, model_loaded=False,
        learned_inference_performed=False, console_access=False)
    a.out.mkdir(parents=True, exist_ok=False)
    exclusive_json(a.out / "receipt.private.json", result)
    print(json.dumps(dict(direct_GGML_API_names=len(direct), graph_helper_names=len(helpers),
        specialized_backend_case_names_found=sum(result["backend_case_text_present"].values()),
        runtime_support_proven=False, console_access=False)))


if __name__ == "__main__": main()
