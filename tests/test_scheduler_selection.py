# SPDX-License-Identifier: MIT
import copy
import json
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from scheduler_slot_map_production import validate_scheduler_measurements

class SchedulerSelectionTests(unittest.TestCase):
    def setUp(self):
        self.report = json.loads((ROOT / 'docs/scheduler-slot-map-adoption-20261101.json').read_text())

    def test_actual_measured_selection(self):
        validate_scheduler_measurements(self.report)

    def test_missing_native_or_source_proof_refused(self):
        for section, field, value in [('scheduler_fixture','GPU_graphs',36),
                ('scheduler_fixture','live_address_changes',1),
                ('model_comparison','all_full_F32_routes_tokens_exact',False),
                ('model_comparison','identical_source_demand',False),
                ('normal','actual_native_frames_viewed',0),
                ('normal','all_actual_ordered_routes_exact',False),
                ('normal','initial_prefill_latency_regression_reported',False)]:
            report = copy.deepcopy(self.report); report[section][field] = value
            with self.subTest(section=section,field=field), self.assertRaises(ValueError):
                validate_scheduler_measurements(report)

    def test_gain_within_control_variation_refused(self):
        report = copy.deepcopy(self.report)
        report['normal']['groups'][1]['paired_whole_savings_ms'][0] = 0
        with self.assertRaises(ValueError): validate_scheduler_measurements(report)

    def test_other_binary_or_precision_refused(self):
        for section, field, value in [('application_SELF','sha256','0'*64),
                                       ('precision','KV_cache','F16')]:
            report = copy.deepcopy(self.report); report[section][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_scheduler_measurements(report)

if __name__ == '__main__': unittest.main()
