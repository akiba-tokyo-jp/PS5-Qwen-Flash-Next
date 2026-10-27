# SPDX-License-Identifier: MIT
import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from resident_gpu_buffer_result import SIZES, review


class BufferResultTests(unittest.TestCase):
    def test_allocation_conservation_and_retained_backing(self):
        # Common initializer ownership/order controls have their own tests.
        # Isolate the new allocation-conservation rules here.
        rows = [dict(ordinal=i, requested_bytes=n, free_before=3000-i*20,
                     free_after=2980-i*20, allocation_returned=True, allocation_succeeded=True)
                for i, n in enumerate(SIZES)]
        capacity = dict(completed=True, allocated_buffers=5, all_five_allocated=True,
                        requested_live_peak_bytes=sum(SIZES), buffer_free_callbacks_returned=5,
                        live_calibration_buffer_objects=0, queue_submissions=0, model_tensors_created=0,
                        physical_backing_retained_for_ordinary_OS_close=True, observations=rows,
                        driver_owned_bytes_at_peak=sum(SIZES), driver_owned_bytes_before=0,
                        driver_owned_bytes_after_callbacks=sum(SIZES), terminal='completed')
        report = dict(buffer_capacity_measurement=capacity)
        trace = dict(samples=[dict(phase='GPU_initializer_before', kernel_free_pages=3000),
                              dict(phase='GPU_capacity_buffers_live_before_metadata_retirement', kernel_free_pages=2900)])
        with patch('resident_gpu_buffer_result.review_initializer', return_value={'elapsed_ns': 100}):
            result = review(report, trace, {})
            self.assertTrue(result['all_five_allocated'])
            self.assertTrue(result['physical_backing_still_owned_before_normal_OS_close'])
            self.assertFalse(result['model_execution_admitted'])
            controls = []
            for key, value in (('allocated_buffers', True), ('requested_live_peak_bytes', sum(SIZES)-1),
                               ('buffer_free_callbacks_returned', 4), ('driver_owned_bytes_after_callbacks', 0),
                               ('physical_backing_retained_for_ordinary_OS_close', False), ('queue_submissions', 1)):
                changed = copy.deepcopy(report); changed['buffer_capacity_measurement'][key] = value; controls.append(changed)
            changed = copy.deepcopy(report); changed['buffer_capacity_measurement']['observations'][2]['ordinal'] = 1; controls.append(changed)
            changed = copy.deepcopy(report); changed['buffer_capacity_measurement']['observations'][2]['free_before'] = 1665; controls.append(changed)
            for changed in controls:
                with self.assertRaises(ValueError): review(changed, trace, {})
            # A positively returned short prefix is a measured refusal, not a
            # fabricated full-payload result or a physical-impossibility claim.
            short = copy.deepcopy(capacity)
            short.update(allocated_buffers=2, all_five_allocated=False, requested_live_peak_bytes=sum(SIZES[:2]),
                         buffer_free_callbacks_returned=2, observations=rows[:2],
                         driver_owned_bytes_at_peak=sum(SIZES[:2]), driver_owned_bytes_after_callbacks=sum(SIZES[:2]),
                         terminal='selected_per_buffer_VM_allowance_refused')
            self.assertFalse(review(dict(buffer_capacity_measurement=short), trace, {})['all_five_allocated'])


if __name__ == '__main__': unittest.main()
