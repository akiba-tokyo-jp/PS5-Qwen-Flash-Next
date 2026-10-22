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


class ConsoleEvidence(unittest.TestCase):
    """Synthetic CPU metadata only; no original-model gate or console execution."""
    def setUp(self):
        base = Path(__file__).resolve().parents[1] / ".test-tmp"; base.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=base); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.workspace = self.root / "workspace"; self.cache = self.root / "cache"
        self.cache.mkdir(); self.workspace.mkdir()
        self.admission = {}
        self.session = dict(boot="synthetic-boot", services=[dict(name="synthetic-service", pid=123)],
            double_snapshot_equal=True, native_eboot_count=0, runningBigApp=-1)
        self.evidence("baseline", self.session)
        self.evidence("completed_context", dict(original_restored=True, original_numerical_re_admission="passed",
            complete_original_SELF_readback_after_shutdown=True, console_reserved=True,
            native_running=False, gateway_running=False, model_loaded=False,
            final_session=self.admission["baseline"]["path"]))
        self.evidence("fresh_session", self.session)
        self.evidence("fresh_CPU_admission", dict(state="fresh_CPU_metadata_admitted", GPU_calls=0,
            session=self.admission["fresh_session"]["path"]))
        self.evidence("fresh_host_interval", dict(host_before_epoch_ms=500, host_after_epoch_ms=1000, host_elapsed_ms=500))
        reference = self.cache / "build/display-metadata-observer-016/observer.c"
        reference.parent.mkdir(parents=True); reference.write_bytes(b"Synthetic never-compiled observer source")
        self.source = self.cache / "observer.c"; self.source.write_bytes(reference.read_bytes())
        self.evidence("fresh_CPU_manifest", dict(nonce="a" * 32, frozen_inputs=[dict(
            path=str(self.source), sha256=transfer.sha(self.source))]))
        self.evidence("fresh_CPU_log", b"END success=1 log_healthy=1 nonce=" + b"a" * 32 + b"\n")
        self.reservation = self.workspace / "driver-work/reservation/active-context.private.json"
        self.reservation.parent.mkdir(parents=True)
        self.reservation.write_text(json.dumps(dict(context=self.admission["completed_context"]["path"])))

    def evidence(self, key, value):
        raw = value if isinstance(value, bytes) else json.dumps(value).encode()
        path = self.cache / (key + ".json"); path.write_bytes(raw)
        self.admission[key] = dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())

    def check(self):
        with patch.object(transfer.time, "time_ns", return_value=2000000000):
            return transfer.validate_console_evidence(self.admission, self.workspace, self.cache, self.reservation)

    def test_positive_CPU_metadata_is_separate_from_model_or_directory_admission(self):
        result = self.check()
        self.assertEqual(result["session"], self.session)
        self.assertNotIn("plan", result); self.assertNotIn("marker_bytes", result)

    def test_stale_CPU_observation_rejects(self):
        self.evidence("fresh_host_interval", dict(host_before_epoch_ms=-400000, host_after_epoch_ms=-399500, host_elapsed_ms=500))
        with self.assertRaisesRegex(ValueError, "fresh and bounded"): self.check()

    def test_changed_boot_or_active_title_rejects(self):
        for changed in (dict(self.session, boot="different"), dict(self.session, native_eboot_count=1)):
            self.evidence("fresh_session", changed)
            with self.assertRaisesRegex(ValueError, "boot/service/process"): self.check()

    def test_recorded_CPU_source_digest_must_match_actual_and_reference(self):
        self.evidence("fresh_CPU_manifest", dict(nonce="a" * 32,
            frozen_inputs=[dict(path=str(self.source), sha256="b" * 64)]))
        with self.assertRaisesRegex(ValueError, "unchanged reviewed"): self.check()

    def test_missing_fresh_nonce_completion_rejects(self):
        self.evidence("fresh_CPU_log", b"END success=1 log_healthy=1 nonce=" + b"b" * 32 + b"\n")
        with self.assertRaisesRegex(ValueError, "fresh-nonce"): self.check()

    def test_lost_reservation_rejects(self):
        self.reservation.write_text(json.dumps(dict(context=str(self.cache / "different-context.json"))))
        with self.assertRaisesRegex(ValueError, "reservation"): self.check()


if __name__ == "__main__": unittest.main()
