# SPDX-License-Identifier: MIT
"""Exercise real Windows metadata sharing conflicts without console access."""
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from local_progress import read_progress, publish_progress
from model_transport import atomic_progress


@unittest.skipUnless(os.name == "nt", "Windows file sharing test")
class LocalProgressTests(unittest.TestCase):
    def setUp(self):
        parent = ROOT / ".test-tmp"; parent.mkdir(exist_ok=True)
        self.directory = tempfile.TemporaryDirectory(dir=parent)
        self.assertTrue(Path(self.directory.name).resolve().is_relative_to(parent.resolve()))
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "status.json"
        self.path.write_text('{"phase":"old"}')
        self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        self.kernel.CreateFileW.argtypes = (wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
            wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE)
        self.kernel.CreateFileW.restype = wintypes.HANDLE
        self.kernel.CloseHandle.argtypes = (wintypes.HANDLE,)

    def lock(self, sharing):
        handle = self.kernel.CreateFileW(str(self.path), 0x80000000, sharing, None, 3, 0x80, None)
        self.assertNotEqual(handle, wintypes.HANDLE(-1).value)
        return handle

    def under_temporary_lock(self, sharing, operation):
        handle = self.lock(sharing)
        outcome = []
        def work():
            try: outcome.append((True, operation()))
            except BaseException as error: outcome.append((False, error))
        worker = threading.Thread(target=work); worker.start()
        time.sleep(.15)
        self.assertTrue(worker.is_alive(), "The operation must wait for the actual sharing conflict")
        self.kernel.CloseHandle(handle)
        worker.join(3)
        self.assertFalse(worker.is_alive())
        self.assertTrue(outcome[0][0], repr(outcome[0][1]))
        return outcome[0][1]

    def test_read_waits_for_exclusive_writer(self):
        self.assertEqual(self.under_temporary_lock(0, lambda: read_progress(self.path)), {"phase": "old"})

    def test_publish_waits_for_reader_denying_delete(self):
        self.under_temporary_lock(3, lambda: publish_progress(self.path, {"phase": "new"}))
        self.assertEqual(read_progress(self.path), {"phase": "new"})

    def test_transport_progress_waits_for_reader_denying_delete(self):
        self.under_temporary_lock(3, lambda: atomic_progress(self.path, {"phase": "new"}))
        self.assertEqual(read_progress(self.path), {"phase": "new"})

    def test_transport_progress_permanent_conflict_is_bounded(self):
        handle = self.lock(3)
        try:
            started = time.monotonic()
            with self.assertRaises(PermissionError):
                atomic_progress(self.path, {"phase": "new"}, timeout_seconds=.1)
            self.assertLess(time.monotonic()-started, 1)
        finally: self.kernel.CloseHandle(handle)
        self.assertEqual(read_progress(self.path), {"phase": "old"})

    def test_permanent_conflict_has_deadline(self):
        handle = self.lock(0)
        try:
            started = time.monotonic()
            with self.assertRaises(PermissionError): read_progress(self.path, timeout_seconds=.1)
            self.assertLess(time.monotonic()-started, 1)
        finally: self.kernel.CloseHandle(handle)

    def test_invalid_or_oversized_progress_is_rejected(self):
        self.path.write_text("{")
        with self.assertRaises(json.JSONDecodeError): read_progress(self.path)
        self.path.write_text("x" * 1025)
        with self.assertRaises(ValueError): read_progress(self.path, limit=1024)


if __name__ == "__main__": unittest.main()
