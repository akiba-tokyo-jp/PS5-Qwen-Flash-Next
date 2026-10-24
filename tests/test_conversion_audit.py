# SPDX-License-Identifier: MIT
"""Reject incomplete or lossy conversion receipts without executing a model."""
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
spec = importlib.util.spec_from_file_location("audit_under_test", ROOT / "tools/audit_conversion.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class ConversionAudit(unittest.TestCase):
    def test_byte_comparison_checks_every_byte_and_rejects_truncation_or_mutation(self):
        original = b"x" * (8 << 20) + b"\x80\x3f"
        for changed in (original[:-1], original[:-1] + b"X"):
            with self.assertRaisesRegex(ValueError, "PLE bytes"):
                audit.compare_span(io.BytesIO(original), io.BytesIO(changed), 0, 0, len(original), time.monotonic() + 10)
        audit.compare_span(io.BytesIO(b"prefix" + original), io.BytesIO(b"offset" + original),
                           6, 6, len(original), time.monotonic() + 10)
        with self.assertRaises(TimeoutError):
            audit.compare_span(io.BytesIO(original), io.BytesIO(original), 0, 0, len(original), 0)

    def fixture(self, root):
        (root / "model").mkdir()
        (root / "model/part.safetensors").write_bytes(b"skip\x80\x3f\x00\xc0")
        out = root / "out"
        out.mkdir()
        gguf_path = out / "split.gguf"
        gguf_path.write_bytes(b"gguf\x80\x3f\x00\xc0")
        types = SimpleNamespace(UINT16=2, INT32=5, UINT32=4, STRING=8, ARRAY=9, INT64=11, UINT64=10)
        gguf = SimpleNamespace(GGUFValueType=types, LlamaFileType=SimpleNamespace(MOSTLY_BF16=32))
        constants = {key: [2 ** 45 + 1, 3] for key in audit.HASH_KEYS.values()}
        fields = {"general.architecture": ([8], "qwen4exp"), "qwen4exp.block_count": ([4], 49),
                  "general.file_type": ([4], 32),
                  "qwen4exp.nextn_predict_layers": ([4], 1), "qwen4exp.expert_count": ([4], 512),
                  "qwen4exp.expert_used_count": ([4], 10), "qwen4exp.embedding_length": ([4], 2560),
                  "qwen4exp.ple.layers": ([9, 5], [1])}
        fields.update({key: ([9, 11], values) for key, values in constants.items()})
        expected = {"per_layer_token_embd.weight": {"shape": [1, 2], "dtype": "BF16", "bytes": 4, "placement": "lazy_ple"}}
        actual = {name: {**row, "path": gguf_path.name, "offset": 4} for name, row in expected.items()}
        plan = {"schema": "plan", "tensors": expected, "tensor_count": 1, "trunk_layers": 48, "mtp_layers": 1,
                "integer_constants": constants, "ple_layers": [1], "ple_parts": ["original_PLE"]}
        manifest = {"tensors": {"original_PLE": {"shape": [1, 2], "file": "part.safetensors", "file_offset": 4}}}
        return out, gguf_path, plan, gguf, manifest, fields, actual

    def run_audit(self, root, changed=lambda fields, actual: None):
        out, path, plan, gguf, manifest, fields, actual = self.fixture(root)
        changed(fields, actual)
        with patch.object(audit, "expected_plan", return_value=(plan, gguf, manifest, None, None, {})), \
             patch.object(audit, "inspect_gguf", return_value=(fields, actual)):
            return audit.audit_conversion(root, out, [path])

    def test_success_publishes_exact_constant_and_complete_PLE_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            report = self.run_audit(Path(directory))
            self.assertEqual(report["PLE_payload_bytes_verified"], 4)
            self.assertTrue(report["exact_PLE_integer_constants"])
            self.assertFalse(report["dense_payload_numerically_verified"])

    def test_missing_tensor_or_shape_precision_change_never_publishes_audit(self):
        changes = [lambda fields, actual: actual.clear(),
                   lambda fields, actual: actual["per_layer_token_embd.weight"].update(shape=[2, 1]),
                   lambda fields, actual: actual["per_layer_token_embd.weight"].update(dtype="F16")]
        for changed in changes:
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                with self.assertRaises(ValueError):
                    self.run_audit(root, changed)
                self.assertFalse((root / "out/conversion-audit.private.json").exists())

    def test_integer_rounding_wrong_metadata_type_and_missing_split_are_rejected(self):
        key = next(iter(audit.HASH_KEYS.values()))
        changes = [lambda fields, actual: fields.update({key: ([9, 11], [2 ** 45, 3])}),
                   lambda fields, actual: fields.update({key: ([9, 6], [2 ** 45 + 1, 3])}),
                   lambda fields, actual: fields.update({"split.count": ([4], 2)}),
                   lambda fields, actual: fields.update({"qwen4exp.ple.layers": ([9, 6], [1.0])}),
                   lambda fields, actual: fields.update({"qwen4exp.expert_count": ([4], 511)})]
        for changed in changes:
            with tempfile.TemporaryDirectory() as directory, self.assertRaises(ValueError):
                self.run_audit(Path(directory), changed)

    def test_host_memory_classes_match_the_native_preload_policy(self):
        for name, expected in [("blk.48.ffn_down_exps.weight", "skipped_mtp"),
                               ("blk.47.ffn_gate_exps.weight", "mapped_experts"),
                               ("token_embd.weight", "mapped_embeddings"),
                               ("per_layer_token_embd.weight", "lazy_ple"),
                               ("output.weight", "device_weights")]:
            self.assertEqual(audit.placement(name, 48), expected)

    def test_expert_gate_up_strides_preserve_every_expert_and_reject_changed_bits(self):
        for corrupt in (False, True):
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                out, path, plan, gguf, manifest, fields, actual = self.fixture(root)
                (root / "model/expert.safetensors").write_bytes(b"ABCDEFGH")
                with path.open("ab") as stream:
                    stream.write(b"ABEX" if corrupt else b"ABEF")
                name = "blk.0.ffn_gate_exps.weight"
                plan["tensors"][name] = {"shape": [2, 1, 1], "dtype": "BF16", "bytes": 4, "placement": "mapped_experts"}
                actual[name] = {**plan["tensors"][name], "offset": 8, "path": path.name}
                plan["raw_expert_copies"] = [{"tensor": name, "file": "expert.safetensors", "source_offset": 0,
                                               "count": 2, "size": 2, "source_stride": 4, "output_stride": 2}]
                with patch.object(audit, "expected_plan", return_value=(plan, gguf, manifest, None, None, {})), \
                     patch.object(audit, "inspect_gguf", return_value=(fields, actual)):
                    if corrupt:
                        with self.assertRaisesRegex(ValueError, "expert bytes"):
                            audit.audit_conversion(root, out, [path])
                        self.assertFalse((out / "conversion-audit.private.json").exists())
                    else:
                        report = audit.audit_conversion(root, out, [path])
                        self.assertEqual(report["expert_payload_bytes_verified"], 4)

    def test_dense_byte_comparison_rejects_changed_tail_truncation_and_deadline(self):
        encoded = bytearray(b"x" * (8 << 20) + b"tail")
        audit.compare_encoded(io.BytesIO(encoded), 0, encoded, len(encoded), time.monotonic() + 10)
        for contents in (encoded[:-1], encoded[:-1] + b"X"):
            with self.assertRaisesRegex(ValueError, "dense bytes"):
                audit.compare_encoded(io.BytesIO(contents), 0, encoded, len(encoded), time.monotonic() + 10)
        with self.assertRaises(TimeoutError):
            audit.compare_encoded(io.BytesIO(encoded), 0, encoded, len(encoded), 0)
        with self.assertRaisesRegex(ValueError, "size"):
            audit.compare_encoded(io.BytesIO(encoded), 0, encoded, len(encoded) + 1, time.monotonic() + 10)

    def test_unchecked_converted_tensor_cannot_publish_a_complete_payload_audit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            out, path, plan, gguf, manifest, fields, actual = self.fixture(root)
            name = "unverified_dense.weight"
            plan["tensors"][name] = {"shape": [1], "dtype": "F32", "bytes": 4, "placement": "device_weights"}
            actual[name] = {**plan["tensors"][name], "path": path.name, "offset": 0}
            with patch.object(audit, "expected_plan", return_value=(plan, gguf, manifest, None, None, {})), \
                 patch.object(audit, "inspect_gguf", return_value=(fields, actual)), self.assertRaisesRegex(ValueError, "Every converted tensor"):
                audit.audit_conversion(root, out, [path])
            self.assertFalse((out / "conversion-audit.private.json").exists())

    def test_dense_source_bound_is_checked_before_file_access_or_tensor_materialization(self):
        model = SimpleNamespace(model_tensors={"filtered": None}, _mtp_fc={})
        manifest = {"tensors": {"original": {"dtype": "BF16", "shape": [1 << 26],
                                               "file": "must-not-open", "file_offset": 0}}}
        with self.assertRaisesRegex(ValueError, "host verification bound"):
            audit.verify_dense_payload(Path("missing"), Path("missing"), {"dense_source_tensors": ["original"]},
                manifest, {}, model, object(), {"filtered": "original"}, None,
                time.monotonic() + 10, lambda *args, **kwargs: None)


if __name__ == "__main__":
    unittest.main()
