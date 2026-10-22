# SPDX-License-Identifier: MIT
import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from clock_calibration import calibration


class ClockCalibrationTest(unittest.TestCase):
    def test_observed_offset_and_bounded_uncertainty(self):
        result = calibration(1792649360, 1792648682000, 1792648684000, 2000)
        self.assertEqual(result["utc_epoch_ms"], 1792648683000)
        self.assertEqual(result["console_epoch_ms"], 1792649360000)
        self.assertEqual(result["uncertainty_ms"], 2000)

    def test_refuse_ambiguous_or_discontinuous_interval(self):
        valid = (1792649360, 1792648682000, 1792648684000, 2000)
        for index, value in ((0, True), (0, 0), (1, "epoch"), (2, valid[1] - 1),
                             (2, valid[1] + 8001), (3, -1), (3, 1000)):
            changed = list(valid)
            changed[index] = value
            with self.subTest(index=index, value=value), self.assertRaises(ValueError):
                calibration(*changed)
