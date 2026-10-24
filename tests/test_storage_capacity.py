# SPDX-License-Identifier: MIT
import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from storage_capacity import data_capacity, human_bytes_lower_bound, require_storage


class StorageCapacity(unittest.TestCase):
    sample = b"Filesystem Size Used Avail Use% Mounted on\n/user/data 625.1G 69.3G 536.5G 11% /data\n"

    def test_conservative_decimal_rounding(self):
        result = data_capacity(self.sample)
        self.assertEqual(result["free_bytes_lower_bound"], 536400000000)
        self.assertFalse(result["freshness_proven"])
        self.assertFalse(result["capture_completion_proven"])
        self.assertGreater(result["free_bytes_lower_bound"], require_storage(result, 359235922432, 1 << 20))

    def test_byte_counts_remain_integral(self):
        self.assertEqual(human_bytes_lower_bound("123456"), 123456)
        self.assertEqual(human_bytes_lower_bound("0.0G"), 0)
        self.assertEqual(human_bytes_lower_bound("1T"), 0)
        self.assertEqual(human_bytes_lower_bound("1.25T"), 1240000000000)

    def test_unrelated_mounts_are_excluded(self):
        result = data_capacity(b"x 1G 0G 1G 0% /data/other\n" + self.sample)
        self.assertEqual(result["mount"], "/data")

    def test_duplicate_missing_or_wrong_filesystem_rejects(self):
        for sample in [self.sample + self.sample, b"x 1G 0G 1G 0% /\n",
                self.sample.replace(b"/user/data", b"/other"), self.sample.replace(b"11%", b"101%")]:
            with self.assertRaises(ValueError): data_capacity(sample)

    def test_incomplete_oversized_or_invalid_capture_rejects(self):
        for sample in [b"", b"x" * ((1 << 20) + 1), self.sample.replace(b"536.5G", b"unknown"),
                self.sample.replace(b"536.5G", b"900G"), b"\xff" + self.sample]:
            with self.assertRaises((ValueError, UnicodeError)): data_capacity(sample)

    def test_reserve_and_receipt_are_required(self):
        cap = data_capacity(self.sample); amount = cap["free_bytes_lower_bound"] - (32 << 30)
        with self.assertRaises(ValueError): require_storage(cap, amount, 1)
        for payload in [0, -1, True, 513 << 30]:
            with self.assertRaises(ValueError): require_storage(cap, payload, 1)
        for receipt in [0, True, (1 << 20) + 1]:
            with self.assertRaises(ValueError): require_storage(cap, 1, receipt)


if __name__ == "__main__": unittest.main()
