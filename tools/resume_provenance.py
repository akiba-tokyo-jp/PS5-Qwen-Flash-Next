# SPDX-License-Identifier: MIT
"""Strict host admission of resumed copy provenance, before transfer planning."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESUME_TOOLS = ("resume_conversion.py", "resumable_gguf.py", "resume_provenance.py")


def sha(path):
    with Path(path).open("rb") as stream: return hashlib.file_digest(stream, "sha256").hexdigest()


def validate_adapter(adapter, original_tools, resume_tools):
    exact = dict(schema="ps5-qwen-resumed-copy-adapter-v1", pinned_sources_modified=False,
        chunk_limit_bytes=8 << 20, complete_planned_copy_partition=True, original_copy_tensors=150,
        original_copy_BF16_bytes=351568363520, independent_payload_audit_required=True,
        maximum_new_payload_bytes=64 << 30,
        console_access=False, learned_inference_performed=False)
    if any(type(adapter.get(key)) is not type(value) or adapter[key] != value for key, value in exact.items()):
        raise ValueError("The complete resumed original-copy provenance is required")
    actual = {name: sha(ROOT / "tools" / name) for name in RESUME_TOOLS}
    if resume_tools != actual or adapter.get("resume_tool_sources") != actual or adapter.get("preparation_tool_sources") != original_tools:
        raise ValueError("Frozen original and resumed source provenance differs")
    for suffix, total in (("tensors", 150), ("BF16_bytes", 351568363520)):
        a, b = adapter.get("retained_copy_" + suffix), adapter.get("written_copy_" + suffix)
        if type(a) is not int or type(b) is not int or a <= 0 or b < 0 or a + b != total:
            raise ValueError("The retained/new original-copy partition is incomplete")
    maximum = adapter.get("maximum_source_read_bytes")
    if (type(maximum) is not int or not 0 <= maximum <= 8 << 20 or
            bool(maximum) != bool(adapter["written_copy_tensors"])):
        raise ValueError("A resumed original source read exceeded its bound or differs from its partition")
    for key in ("checkpoint", "retention_record"):
        row = adapter.get(key, {}); path = Path(row.get("path", ""))
        if (path.is_symlink() or not path.is_file() or type(row.get("bytes")) is not int or
                not 0 < row["bytes"] <= 2 << 20 or path.stat().st_size != row["bytes"] or sha(path) != row.get("sha256")):
            raise ValueError("A resumed preparation record changed")
    retention = json.loads(Path(adapter["retention_record"]["path"]).read_text(encoding="utf-8"))
    if (retention.get("all_splits_written") is not True or
            len(retention.get("retained", [])) + len(retention.get("written", [])) != 76 or
            not retention["retained"]):
        raise ValueError("Every split must have one complete retained/new outcome")
    retained, written = retention.get("retained_tensors", []), retention.get("written_tensors", [])
    if (not isinstance(retained, list) or not isinstance(written, list) or
            len(set(retained)) != len(retained) or len(set(written)) != len(written) or
            set(retained) & set(written) or len(retained) + len(written) != 1256):
        raise ValueError("The complete retained/new tensor partition differs")
    counts = [retention.get(key) for key in ("retained_payload_bytes", "newly_written_payload_bytes")]
    if (any(type(value) is not int or value < 0 for value in counts) or counts[0] <= 0 or
            counts[1] > 64 << 30 or sum(counts) != 359235922432 or bool(counts[1]) != bool(retention["written"])):
        raise ValueError("The complete retained/new payload byte count differs")
    checkpoint = json.loads(Path(adapter["checkpoint"]["path"]).read_text(encoding="utf-8"))
    if (checkpoint.get("schema") != "ps5-qwen-source-verification-checkpoint-v1" or
            checkpoint.get("original_verification_reused") is not True or
            checkpoint.get("fresh_original_payload_rehash") is not False or
            checkpoint.get("preparation_tool_sources") != original_tools or len(checkpoint.get("sources", [])) != 131 or
            checkpoint.get("console_access") is not False or checkpoint.get("learned_inference_performed") is not False):
        raise ValueError("Completed original SHA verification provenance is required")
