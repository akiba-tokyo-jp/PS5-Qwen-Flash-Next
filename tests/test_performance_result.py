# SPDX-License-Identifier: MIT
import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from performance_result import FIELDS, validate_performance


class PerformanceResultTests(unittest.TestCase):
    def setUp(self):
        self.record = dict(schema='ps5-qwen-completed-performance-v1',
            process_includes_source_and_backend_work=True, GPU_timestamp_queries=False,
            hot_path_logs_added=False, GPU_operations_added=False,
            delta=dict.fromkeys(FIELDS, 1))
        self.record['delta'].update(process_ns=1000, synchronize_ns=0, process_calls=52)
        self.result = dict(stop_reason='end_of_generation', metrics=dict(prompt_tokens=30, generated_tokens=22))

    def test_nested_intervals_are_not_GPU_compute_time(self):
        result = validate_performance(self.record, self.result)
        self.assertEqual(result['measured_source_wall_fraction'], .004)
        self.assertFalse(result['GPU_compute_time_qualified'])

    def test_failed_missing_uncompleted_and_inconsistent_measurements(self):
        mutations = [lambda r: r['delta'].pop('source_read_ns'),
            lambda r: r['delta'].update(source_completed_windows=0),
            lambda r: r['delta'].update(source_read_ns=1001),
            lambda r: r['delta'].update(process_calls=51),
            lambda r: r['delta'].update(source_consumer_ns=-1),
            lambda r: r.update(GPU_timestamp_queries=True)]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                record = copy.deepcopy(self.record); mutation(record)
                with self.assertRaises(ValueError): validate_performance(record, self.result)
        self.result['stop_reason'] = 'failed'
        with self.assertRaises(ValueError): validate_performance(self.record, self.result)

    def test_output_limit_has_no_extra_EOG_decode(self):
        self.result['stop_reason'] = 'output_token_limit'
        self.record['delta']['process_calls'] = 51
        validate_performance(self.record, self.result)


if __name__ == '__main__': unittest.main()
