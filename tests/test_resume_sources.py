# SPDX-License-Identifier: MIT
"""Check actual Windows share-mode preservation on disposable tiny sources."""
from contextlib import ExitStack
import os
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from resume_conversion import read_only_leases


@unittest.skipUnless(os.name == "nt", "The read-only sharing contract is Windows-specific")
class SourceLeases(unittest.TestCase):
    def test_lease_allows_reads_but_prevents_writes_and_deletion(self):
        root = Path(__file__).resolve().parents[1] / ".test-tmp"; root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as temporary:
            path = Path(temporary) / "synthetic-source"; path.write_bytes(b"preserved")
            with ExitStack() as leases:
                read_only_leases([path], leases)
                self.assertEqual(path.read_bytes(), b"preserved")
                with self.assertRaises(PermissionError):
                    with path.open("r+b"): pass
                with self.assertRaises(PermissionError): path.unlink()
            path.write_bytes(b"ordinary access restored")
            self.assertEqual(path.read_bytes(), b"ordinary access restored")


if __name__ == "__main__": unittest.main()
