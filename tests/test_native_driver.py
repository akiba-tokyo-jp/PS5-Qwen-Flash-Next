# SPDX-License-Identifier: MIT
"""Protect native allocator members and duplicate occurrence identities."""
from pathlib import Path
import sys
import tempfile
import unittest
import json
import subprocess
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from native_driver import (check_plan, verify_composition, read_archive, PROFILE_MEMBERS,
                           NATIVE_COMPATIBILITY, NATIVE_PLATFORM, GENERIC_PLATFORM, compose, sha)


class NativeComposition(unittest.TestCase):
    def setUp(self):
        self.reference = {key: "original-" + key[0] for key in
                          PROFILE_MEMBERS | NATIVE_COMPATIBILITY | {GENERIC_PLATFORM}}
        self.reference.update({("unchanged-%d.o" % n, 0): "body-%d" % n for n in range(698)})
        self.base = dict(self.reference)
        del self.base[GENERIC_PLATFORM]
        self.base[NATIVE_PLATFORM] = "native-platform"
        for key in NATIVE_COMPATIBILITY:
            self.base[key] = "native-" + key[0]
        self.selected = dict(self.reference)
        for key in PROFILE_MEMBERS:
            self.selected[key] = "selected-" + key[0]

    def test_exact_profile_preserves_all_native_members(self):
        check_plan(self.base, self.reference, self.selected)
        after = dict(self.base)
        after.update({key: self.selected[key] for key in PROFILE_MEMBERS})
        verify_composition(self.base, after, self.selected)

    def test_wrong_compatibility_or_profile_members_are_rejected(self):
        compatibility = next(iter(NATIVE_COMPATIBILITY))
        cases = [(self.base, self.reference, {**self.selected, NATIVE_PLATFORM: "unexpected"}),
                 ({**self.base, compatibility: self.reference[compatibility]}, self.reference, self.selected)]
        # An archive digest pins exact compatibility bytes. This set-level
        # guard additionally rejects replacing a native object with the generic one.
        for base, reference, selected in cases:
            with self.subTest(case=len(selected)), self.assertRaises(ValueError):
                check_plan(base, reference, selected)
        duplicate = dict(self.selected)
        duplicate[("radv_shader.c.o", 1)] = duplicate.pop(("unchanged-0.o", 0))
        with self.assertRaises(ValueError):
            check_plan(self.base, self.reference, duplicate)

    def test_extra_change_missing_member_and_wrong_donor_are_rejected(self):
        correct = {**self.base, **{key: self.selected[key] for key in PROFILE_MEMBERS}}
        for key in [NATIVE_PLATFORM, *NATIVE_COMPATIBILITY, ("unchanged-3.o", 0), *PROFILE_MEMBERS]:
            after = {**correct, key: "not-the-required-object"}
            with self.subTest(key=key), self.assertRaises(ValueError):
                verify_composition(self.base, after, self.selected)
        del correct[("unchanged-3.o", 0)]
        with self.assertRaises(ValueError):
            verify_composition(self.base, correct, self.selected)

    def test_archive_duplicate_identities_and_truncation(self):
        def member(name, body):
            header = (name + "/").ljust(16) + "0".ljust(12) + "0".ljust(6) * 2
            header += "100644".ljust(8) + str(len(body)).ljust(10) + "`\n"
            return header.encode("ascii") + body + (b"\n" if len(body) % 2 else b"")
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "fixture.a"
            data = b"!<arch>\n" + member("same.o", b"\x7fELFone") + member("same.o", b"\x7fELFtwo")
            archive.write_bytes(data)
            index = read_archive(archive)
            self.assertEqual(list(index), [("same.o", 0), ("same.o", 1)])
            self.assertNotEqual(index[("same.o", 0)]["sha256"], index[("same.o", 1)]["sha256"])
            for invalid in [data[:-2], b"!<thin>\n", b"!<arch>\n" + member("../bad", b"\x7fELFbad")]:
                archive.write_bytes(invalid)
                with self.assertRaises(ValueError):
                    read_archive(archive)

    def test_timed_out_archiver_retains_failure_without_an_accepted_manifest(self):
        def archive(path, rows):
            with path.open("wb") as stream:
                stream.write(b"!<arch>\n")
                for (name, _), value in rows.items():
                    encoded = name.encode()
                    body = encoded + b"\x7fELF" + value.encode()
                    header = ("#1/" + str(len(encoded))).ljust(16) + "0".ljust(12) + "0".ljust(6) * 2
                    header += "100644".ljust(8) + str(len(body)).ljust(10) + "`\n"
                    stream.write(header.encode() + body + (b"\n" if len(body) % 2 else b""))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            base, reference, donor = [root / name for name in ("base.a", "reference.a", "selected.a")]
            for path, rows in ((base, self.base), (reference, self.reference), (donor, self.selected)):
                archive(path, rows)
            native_lock = {"base_archive_sha256": sha(base), "reference_archive_sha256": sha(reference)}
            selected = {"archive_path": str(donor), "archive_sha256": sha(donor), "profile": "cumulative-idle"}
            with patch("native_driver.subprocess.run", side_effect=subprocess.TimeoutExpired("fixture-ar", 1)), \
                 self.assertRaises(subprocess.TimeoutExpired):
                compose(base, reference, selected, native_lock, root / "fixture-ar", root / "out", 1)
            state = json.loads((root / "out/operation-status.private.json").read_text())
            self.assertEqual(state["phase"], "failed")
            self.assertFalse(state["accepted_manifest_published"])
            self.assertFalse((root / "out/manifest.private.json").exists())
            self.assertEqual(sha(base), native_lock["base_archive_sha256"])


if __name__ == "__main__":
    unittest.main()
