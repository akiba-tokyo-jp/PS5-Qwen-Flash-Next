# SPDX-License-Identifier: MIT
"""Reject stale or altered driver inputs before native build/link writes."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from driver_inputs import sha, validate_driver


class DriverInputs(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / "builder.py").write_text("# fixture source\n")
        self.archive = self.root / "libvulkan_radeon.experimental.a"
        self.archive.write_bytes(b"fixture archive, not a driver")
        self.manifest = self.root / "manifest.json"
        self.profile = {
            "schema": "ps5-selected-mesa-members-v1", "profile": "cumulative-idle", "mesa_commit": "mesa-pin",
            "base_archive_sha256": "base-pin", "archive_sha256": sha(self.archive), "profile_selected_explicitly": True,
            "capture_isa": False, "client_platform_allocator_members_preserved": True,
            "persistent_shader_and_pipeline_caches_must_be_disabled": True,
            "production_cache_identity_release_qualified": False, "source_checkout_modified": False,
            "console_execution": False, "CI": False, "changed_members": [["shader.o", 0], ["winsys.o", 0]], "patches": []}
        self.selected = {
            "repository": "fixture/driver", "revision": "source-pin", "profile": "cumulative-idle",
            "mesa_revision": "mesa-pin", "base_archive_sha256": "base-pin", "archive_sha256": sha(self.archive),
            "capture_isa": False, "persistent_caches_enabled": False, "changed_members": self.profile["changed_members"],
            "patches": [], "source_files": [{"path": "builder.py", "sha256": sha(self.root / "builder.py")}]}
        self.save_manifest()
        self.revision = patch("driver_inputs.subprocess.check_output", return_value="source-pin\n").start()
        self.clean = patch("driver_inputs.subprocess.run", return_value=subprocess.CompletedProcess([], 0)).start()
        self.addCleanup(patch.stopall)

    def save_manifest(self):
        self.manifest.write_text(json.dumps(self.profile))
        self.selected["profile_manifest_sha256"] = sha(self.manifest)

    def validate(self):
        return validate_driver(self.root, self.manifest, self.selected)

    def test_exact_selection_records_source_profile_artifact_and_cache_policy(self):
        result = self.validate()
        self.assertEqual(result["source_revision"], "source-pin")
        self.assertEqual(result["archive_sha256"], sha(self.archive))
        self.assertTrue(result["persistent_caches_disabled_required"])

    def test_old_checkout_or_modified_tracked_source_is_rejected(self):
        self.revision.return_value = "old-pin\n"
        with self.assertRaisesRegex(ValueError, "revision"): self.validate()
        self.revision.return_value = "source-pin\n"
        self.clean.return_value = subprocess.CompletedProcess([], 1)
        with self.assertRaisesRegex(ValueError, "local changes"): self.validate()

    def test_changed_artifact_or_manifest_is_rejected(self):
        self.archive.write_bytes(b"different fixture")
        with self.assertRaisesRegex(ValueError, "archive digest"): self.validate()
        self.manifest.write_text("{}")
        with self.assertRaisesRegex(ValueError, "manifest"): self.validate()

    def test_incompatible_profile_cache_or_allocator_policy_is_rejected(self):
        original = copy.deepcopy(self.profile)
        for key, value in (("profile", "combined"), ("capture_isa", True),
                           ("persistent_shader_and_pipeline_caches_must_be_disabled", False),
                           ("client_platform_allocator_members_preserved", False), ("console_execution", True)):
            with self.subTest(key=key):
                self.profile = {**original, key: value}; self.save_manifest()
                with self.assertRaisesRegex(ValueError, "contract"): self.validate()

    def test_changed_source_or_member_provenance_is_rejected(self):
        (self.root / "builder.py").write_text("# altered fixture\n")
        with self.assertRaisesRegex(ValueError, "source digest"): self.validate()
        self.selected["source_files"][0]["sha256"] = sha(self.root / "builder.py")
        self.profile["changed_members"].append(["allocator.o", 0])
        self.selected["changed_members"] = [["shader.o", 0], ["winsys.o", 0]]
        self.save_manifest()
        with self.assertRaisesRegex(ValueError, "provenance"): self.validate()


if __name__ == "__main__":
    unittest.main()
