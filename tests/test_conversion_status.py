# SPDX-License-Identifier: MIT
"""A rejected shard or timed-out host converter cannot publish a model receipt."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
spec = importlib.util.spec_from_file_location("conversion_under_test", ROOT / "tools/convert_model.py")
conversion = importlib.util.module_from_spec(spec)
spec.loader.exec_module(conversion)


class ConversionFailureStatus(unittest.TestCase):
    def fixture(self, root):
        cache = root / "cache"; (cache / "metadata").mkdir(parents=True); (cache / "model").mkdir()
        data = b"host fixture; never model weights"
        shard = cache / "model/fixture.safetensors"; shard.write_bytes(data)
        model = conversion.LOCK["model"]
        (cache / "metadata/checkpoint.json").write_text(json.dumps({"revision": model["revision"], "quantization": False,
            "files": [{"name": shard.name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}]}))
        upstream = cache / "upstream" / ("llama.cpp-" + conversion.LOCK["llama_cpp"]["revision"])
        upstream.mkdir(parents=True)
        (upstream / "convert_hf_to_gguf.py").write_text("import time\ntime.sleep(60)\n")
        archive = cache / ("llama-" + conversion.LOCK["llama_cpp"]["revision"] + ".zip")
        with zipfile.ZipFile(archive, "w") as bundle:
            bundle.write(upstream / "convert_hf_to_gguf.py", upstream.name + "/convert_hf_to_gguf.py")
        return cache, shard, archive

    def run_tool(self, cache, out, archive):
        pinned = dict(conversion.LOCK["llama_cpp"], archive_sha256=conversion.digest(archive))
        argv = ["convert_model.py", "--cache", str(cache), "--out", str(out), "--timeout-seconds", "1"]
        with patch.dict(conversion.LOCK, llama_cpp=pinned), patch.object(sys, "argv", argv), \
             patch.object(conversion.shutil, "disk_usage", return_value=type("Space", (), {"free": 1 << 50})()):
            conversion.main()

    def test_corrupt_shard_is_recorded_before_any_converter_execution(self):
        with tempfile.TemporaryDirectory() as folder:
            cache, shard, archive = self.fixture(Path(folder)); out = Path(folder) / "out"
            shard.write_bytes(b"X" * shard.stat().st_size)
            with patch.object(conversion.subprocess, "run") as run, self.assertRaises(ValueError):
                self.run_tool(cache, out, archive)
            run.assert_not_called()
            self.assertEqual(json.loads((out / "conversion-status.private.json").read_text())["phase"], "failed")
            self.assertFalse((out / "model-receipt.json").exists())

    def test_timeout_retains_failed_status_without_receipt(self):
        with tempfile.TemporaryDirectory() as folder:
            cache, _, archive = self.fixture(Path(folder)); out = Path(folder) / "out"
            with self.assertRaises(conversion.subprocess.TimeoutExpired):
                self.run_tool(cache, out, archive)
            status = json.loads((out / "conversion-status.private.json").read_text())
            self.assertEqual((status["phase"], status["error_type"]), ("failed", "TimeoutExpired"))
            self.assertFalse((out / "model-receipt.json").exists())

    def test_modified_or_shadowing_converter_is_rejected_before_execution(self):
        for change in ("modified", "extra"):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as folder:
                cache, _, archive = self.fixture(Path(folder)); out = Path(folder) / "out"
                upstream = cache / "upstream" / ("llama.cpp-" + conversion.LOCK["llama_cpp"]["revision"])
                path = upstream / ("convert_hf_to_gguf.py" if change == "modified" else "json.py")
                path.write_text("raise RuntimeError('must not run')\n")
                with patch.object(conversion.subprocess, "run") as run, self.assertRaisesRegex(ValueError, "Python sources"):
                    self.run_tool(cache, out, archive)
                run.assert_not_called()
                self.assertFalse((out / "model-receipt.json").exists())

    def test_failed_post_conversion_audit_cannot_publish_a_model_receipt(self):
        for error in (ValueError("Missing original expert"), TimeoutError("Payload audit deadline")):
            with self.subTest(error=type(error).__name__), tempfile.TemporaryDirectory() as folder:
                cache, _, archive = self.fixture(Path(folder)); out = Path(folder) / "out"
                def converted(*args, **kwargs):
                    (out / "fixture.gguf").write_bytes(b"unqualified fixture")
                    return type("Result", (), {"returncode": 0})()
                with patch.object(conversion.subprocess, "run", side_effect=converted), \
                     patch("audit_conversion.audit_conversion", side_effect=error), self.assertRaises(type(error)):
                    self.run_tool(cache, out, archive)
                state = json.loads((out / "conversion-status.private.json").read_text())
                self.assertEqual((state["phase"], state["receipt_published"]), ("failed", False))
                self.assertTrue((out / "fixture.gguf").exists())
                self.assertFalse((out / "model-receipt.json").exists())


if __name__ == "__main__":
    unittest.main()
