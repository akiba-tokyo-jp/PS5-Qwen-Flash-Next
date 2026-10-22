# SPDX-License-Identifier: MIT
"""Build admission rejects untrusted recipes and metadata fixtures before tools run."""
from pathlib import Path
import hashlib
import json
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import build_model_directory as build
from model_transport import REMOTE_ROOT


class DirectoryBuild(unittest.TestCase):
    def setUp(self):
        base = Path(__file__).resolve().parents[1] / ".test-tmp"; base.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=base); self.root = Path(self.temp.name).resolve()
        self.addCleanup(self.temp.cleanup)

    def arguments(self):
        args = ["build_model_directory.py"]
        for name, path in [("workspace", self.root), ("cache", self.root), ("plan", self.root / "plan.json"),
                ("qualified-reference", self.root / "ref/manifest.json"), ("out", self.root / "build")]:
            args += ["--" + name, str(path)]
        return args

    def marker(self):
        raw = json.dumps(dict(schema="ps5-qwen-bf16-conversion-v2", test_fixture_only=True,
                             original_shards_verified=True, outtype="bf16")).encode()
        path = self.root / "receipt.json"; path.write_bytes(raw)
        return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())

    def test_complete_original_fixture_gate_precedes_any_compiler(self):
        plan = dict(schema="ps5-qwen-model-transfer-plan-v1", nonce="a" * 32, remote_root=REMOTE_ROOT,
            maximum_upload_connections=1, console_access=False, remote_payload_SHA_verified=False,
            input_hashes_stable=True, file_timeout_seconds=21600, receipt_copy=self.marker())
        (self.root / "plan.json").write_text(json.dumps(plan))
        with patch.object(sys, "argv", self.arguments()), patch.object(build.subprocess, "run") as compiler:
            with self.assertRaises(ValueError): build.main()
            compiler.assert_not_called()
        self.assertFalse((self.root / "build").exists())

    def test_unqualified_command_recipe_is_never_executed(self):
        (self.root / "plan.json").write_text(json.dumps(dict(receipt_copy=self.marker(), source_directory=str(self.root))))
        (self.root / "conversion-status.private.json").write_text("{}")
        reference = self.root / "ref"; reference.mkdir()
        (reference / "manifest.json").write_text(json.dumps(dict(source_path="synthetic-source.c", elf="synthetic.elf",
            sha256="synthetic-digest", commands=[["untrusted-compiler.exe", "--untrusted-option"]])))
        def fake_sha(path):
            return build.QUALIFIED_SOURCE if str(path) == "synthetic-source.c" else "synthetic-digest"
        with patch.object(sys, "argv", self.arguments()), patch.object(build, "validate_plan"), \
                patch.object(build, "preparation_gate"), patch.object(build, "sha", side_effect=fake_sha), \
                patch.object(build.subprocess, "run") as compiler:
            with self.assertRaisesRegex(ValueError, "qualified CPU build recipe"): build.main()
            compiler.assert_not_called()
        self.assertFalse((self.root / "build").exists())

    def test_literal_template_placeholder_is_not_an_executable_path(self):
        with self.assertRaises(ValueError):
            build.command_template([["${WORKSPACE}/untrusted.exe"]], self.root / "ref", self.root)


if __name__ == "__main__": unittest.main()
