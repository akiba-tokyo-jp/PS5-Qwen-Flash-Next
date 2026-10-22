# SPDX-License-Identifier: MIT
"""Synthetic journal framing/counters only; never a real model admission."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1] / "tools"))
from model_integrity_progress import integrity_progress


def progress(index,count,size,total,time=0,files=2,maximum=30):
    return (f"model_file_integrity_progress file={index} files={files} verified_file_bytes={count} "
        f"file_bytes={size} total_verified_bytes={total} total_bytes={maximum} elapsed_ms={time} deadline_seconds=7200\n").encode()


def complete(index,size,total):
    return f"model_file_integrity_completed file={index} bytes={size} total_verified_bytes={total} SHA256_matched=1\n".encode()


class IntegrityProgress(unittest.TestCase):
    def test_complete_bytes_do_not_imply_matched_SHA(self):
        result=integrity_progress(progress(1,0,10,0)+progress(1,10,10,10),2,30)
        self.assertEqual(result["total_hashed_bytes"],10);self.assertEqual(result["SHA_matched_bytes"],0)
        self.assertFalse(result["all_file_SHA_markers_seen"])

    def test_sequential_positive_markers_still_require_native_terminal_reports(self):
        raw=b"unrelated bootstrap metadata\n"+progress(1,0,10,0)+progress(1,10,10,10)+complete(1,10,10)
        raw+=progress(2,0,20,10)+progress(2,20,20,30)+complete(2,20,30)
        result=integrity_progress(raw,2,30)
        self.assertEqual(result["SHA_matched_file_markers"],2)
        self.assertTrue(result["all_file_SHA_markers_seen"])
        self.assertTrue(result["final_native_integrity_and_mapping_reports_required"])
        self.assertFalse(result["full_model_inference"])

    def test_partial_final_line_is_not_a_completed_observation(self):
        result=integrity_progress(progress(1,0,10,0)+progress(1,10,10,10)[:-1],2,30)
        self.assertEqual(result["total_hashed_bytes"],0)

    def test_legacy_or_malformed_lines_reject(self):
        for raw in (b"model_file_integrity_progress\n",b"model_file_integrity_completed\n",
                    progress(1,0,10,0).replace(b"deadline_seconds=7200",b"deadline_seconds=1800")):
            with self.assertRaises(ValueError):integrity_progress(raw,2,30)

    def test_regression_and_false_totals_reject(self):
        start=progress(1,0,10,0)+progress(1,5,10,5,time=10)
        for row in (progress(1,4,10,4,time=11),progress(1,6,10,6,time=9),progress(1,6,10,7,time=11),
                    progress(1,11,10,11,time=11),progress(1,6,20,6,time=11)):
            with self.assertRaises(ValueError):integrity_progress(start+row,2,30)

    def test_missing_or_duplicate_SHA_markers_reject(self):
        start=progress(1,0,10,0)+progress(1,10,10,10)
        with self.assertRaises(ValueError):integrity_progress(start+progress(2,0,20,10),2,30)
        with self.assertRaises(ValueError):integrity_progress(start+complete(1,10,10)*2,2,30)
        with self.assertRaises(ValueError):integrity_progress(progress(1,0,10,0)+complete(1,10,10),2,30)

    def test_completed_file_cannot_restart(self):
        raw=progress(1,0,10,0)+progress(1,10,10,10)+complete(1,10,10)+progress(1,0,10,0)
        with self.assertRaises(ValueError):integrity_progress(raw,2,30)

    def test_late_completed_boundary_exposes_deadline(self):
        result=integrity_progress(progress(1,0,10,0)+progress(1,5,10,5,time=7200010),2,30)
        self.assertTrue(result["deadline_reached"])
        self.assertFalse(result["all_file_SHA_markers_seen"])

    def test_capture_and_metadata_bounds(self):
        for files,total in ((0,30),(257,30),(True,30),(2,0),(2,(512<<30)+1)):
            with self.assertRaises(ValueError):integrity_progress(b"",files,total)
        with self.assertRaises(ValueError):integrity_progress(b"x"*((8<<20)+1),2,30)


if __name__=="__main__":unittest.main()
