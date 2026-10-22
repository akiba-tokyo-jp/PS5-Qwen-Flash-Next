# SPDX-License-Identifier: MIT
"""Host-only negative admission and offline dispatch tests; no real model/network."""
from contextlib import redirect_stdout
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import transfer_model as transfer


class TransferAdmission(unittest.TestCase):
    def setUp(self):
        base = Path(__file__).resolve().parents[1] / ".test-tmp"; base.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=base); self.root = Path(self.temp.name).resolve()
        self.addCleanup(self.temp.cleanup)
        self.admission = dict(schema="ps5-qwen-model-data-transfer-admission-v1",
            model_data_transfer_enabled=True, GPU_execution_enabled=False,
            model_loading_enabled=False, plan_sha256="a" * 64, remote_root=transfer.REMOTE_ROOT)

    def arguments(self):
        values = dict(workspace=self.root, cache=self.root, plan=self.root / "plan.json",
            admission=self.root / "admission.json", connection=self.root / "connection.json",
            reservation=self.root / "reservation.json", out=self.root / "run")
        args = ["transfer_model.py"]
        for key, value in values.items(): args += ["--" + key, str(value)]
        return args, values

    def test_data_only_fields_are_exact_and_plan_bound(self):
        transfer.require_admission(self.admission, "a" * 64)
        for key, value in [("model_data_transfer_enabled", False), ("GPU_execution_enabled", True),
                ("GPU_execution_enabled", 0), ("model_loading_enabled", True), ("plan_sha256", "b" * 64),
                ("remote_root", "/data/other")]:
            changed = deepcopy(self.admission); changed[key] = value
            with self.assertRaises(ValueError): transfer.require_admission(changed, "a" * 64)

    def test_mutated_evidence_rejects(self):
        path = self.root / "proof.json"; raw = b'{"synthetic_only":true}'; path.write_bytes(raw)
        record = dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
        self.assertEqual(transfer.record_bytes(record, self.root), raw)
        path.write_bytes(b"changed")
        with self.assertRaises(ValueError): transfer.record_bytes(record, self.root)

    def test_evidence_outside_data_root_rejects(self):
        path = self.root / "proof.json"; path.write_bytes(b"{}")
        record = dict(path=str(path), bytes=2, sha256=hashlib.sha256(b"{}").hexdigest())
        with self.assertRaises(ValueError): transfer.record_bytes(record, self.root / "different")

    def test_metadata_size_and_regular_file_bounds(self):
        path = self.root / "oversized.json"; path.write_bytes(b" " * ((1 << 20) + 1))
        with self.assertRaises(ValueError): transfer.bounded_json(path)
        with self.assertRaises(ValueError): transfer.bounded_json(self.root)

    def test_disabled_admission_rejects_before_any_connection(self):
        args, paths = self.arguments(); paths["plan"].write_text("{}")
        paths["admission"].write_text(json.dumps(dict(self.admission, model_data_transfer_enabled=False)))
        with patch.object(sys, "argv", args + ["--execute"]), patch.object(transfer, "PS5ModelConnection") as network:
            with self.assertRaises(ValueError): transfer.main()
            network.assert_not_called()

    def test_offline_dispatch_never_constructs_connection(self):
        args, _ = self.arguments()
        # Stub only the local validator to isolate CLI dispatch. This deliberately
        # does not manufacture a successful complete-model validation fixture.
        state = dict(plan=dict(source_directory=str(self.root / "synthetic-source")))
        output = io.StringIO()
        with patch.object(sys, "argv", args), patch.object(transfer, "validate_local", return_value=state), \
                patch.object(transfer, "PS5ModelConnection") as network, redirect_stdout(output):
            transfer.main(); network.assert_not_called()
        self.assertFalse(json.loads(output.getvalue())["transfer_started"])


if __name__ == "__main__": unittest.main()
