# SPDX-License-Identifier: MIT
"""Opaque-call bounds with a synthetic clock; no network or native execution."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from native_source_deadline import NativeSourceDeadline

class SourceDeadline(unittest.TestCase):
    def test_full_sha_wait_does_not_consume_virtual_source_budget(self):
        value=NativeSourceDeadline()
        value.observe(["model_file_integrity_progress"],7200)
        value.observe(["source_virtual_small_probe_started"],7201)
        value.observe(["source_virtual_reserve_before_native_call"],7266)
        with self.assertRaises(ValueError):value.observe(["source_virtual_reserve_before_native_call"],7267)

    def test_incomplete_release_is_bounded_even_when_the_process_remains_alive(self):
        value=NativeSourceDeadline();value.observe(["model_mapping_before_virtual_source_reserve"],10)
        with self.assertRaises(ValueError):value.observe(["source_virtual_release_before_native_call"],76)

    def test_positive_completion_does_not_reactivate_on_historical_stage_lines(self):
        value=NativeSourceDeadline();lines=["source_virtual_small_probe_started"]
        value.observe(lines,10);lines.append("model_validation_completed GPU_not_started=1 model_loaded=0")
        value.observe(lines,11);value.observe(lines,20000)

    def test_file_backed_mapping_is_always_rejected(self):
        value=NativeSourceDeadline()
        with self.assertRaises(ValueError):value.observe(["model_mapping_before_public_mmap mapped_files=0"],0)

if __name__=="__main__":unittest.main()
