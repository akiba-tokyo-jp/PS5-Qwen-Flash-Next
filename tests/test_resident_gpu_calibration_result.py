# SPDX-License-Identifier: MIT
import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from resident_gpu_calibration_result import PHASES, review


class GPUResultTests(unittest.TestCase):
    def test_complete_boundaries_and_no_model_admission(self):
        binding = dict(pid=1, run_id='a' * 32)
        report = dict(binding, schema='ps5-qwen-resident-GPU-initialization-calibration-result-v1',
                      completed=True, backend_instance_positively_synchronized_and_retired=True,
                      source_workers_stopped=True, ordinary_OS_close_required=True,
                      global_device_lifetime_retained_until_ordinary_OS_close=True,
                      model_loaded=False, unknown_completion=False, postload_model_device_ledger_enabled=False,
                      whole_model_CPU_preflight_repeated=False, model_loads=0, model_requests=0,
                      graph_computes=0, tensor_payload_allocations=0, model_tensor_API_calls=0,
                      source_workers_started=0, whole_model_metadata_files=0, source_chunks=0,
                      source_completed_windows=0, backend_instances=1, selected_required_pages=1410,
                      selected_total_above_kernel_minimum_pages=512, ordinary_operational_floor_pages=1154,
                      sampled_phase_component_pages=245, entry_free_pages=2000)
        trace = dict(schema='ps5-qwen-resident-startup-memory-v1', global_snapshots_not_exclusive_attribution=True,
                     samples=[dict(phase=phase, ns=i, kernel_free_pages=2000-i,
                                   kernel_minimum_pages=898, kernel_reserved_pages=206) for i, phase in enumerate(PHASES)])
        result = review(report, trace, binding)
        self.assertEqual(result['maximum_sampled_global_decline_pages'], 6)
        self.assertFalse(result['model_execution_admitted'])
        controls = []
        for key, value in (('unknown_completion', True), ('model_loads', 1), ('tensor_payload_allocations', 1),
                           ('backend_instance_positively_synchronized_and_retired', False), ('source_workers_started', 1),
                           ('run_id', 'b' * 32), ('pid', True), ('selected_required_pages', 1154)):
            changed = dict(report); changed[key] = value; controls.append((changed, trace))
        for change in ('missing', 'duplicate', 'reordered', 'below-floor', 'backwards'):
            changed = copy.deepcopy(trace)
            if change == 'missing': del changed['samples'][3]
            elif change == 'duplicate': changed['samples'][3] = dict(changed['samples'][2])
            elif change == 'reordered': changed['samples'][3]['phase'] = PHASES[4]
            elif change == 'below-floor': changed['samples'][3]['kernel_free_pages'] = 1153
            else: changed['samples'][3]['ns'] = 0
            controls.append((report, changed))
        for terminal, samples in controls:
            with self.assertRaises(ValueError): review(terminal, samples, binding)


if __name__ == '__main__': unittest.main()
