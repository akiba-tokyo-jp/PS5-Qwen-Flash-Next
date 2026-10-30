# SPDX-License-Identifier: MIT
"""Exercise refusal boundaries with synthetic placement and qualification fixtures."""
import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from resident_all_q8_production import (CONTROL_SELF, DRIVER, MODEL_RECEIPT, POLICY,
    PRECISION, REPORT, SELECTED_SELF, require_resident_all_q8_production)
from prepare_first_case import qualified_control


class ResidentQ8Production(unittest.TestCase):
    def setUp(self):
        app = dict(bytes=20065607, sha256=SELECTED_SELF)
        self.i = dict(schema='ps5-qwen-production-installation-v1',
            application_SELF=app, previous_production_SHA256=CONTROL_SELF,
            driver=DRIVER, precision=PRECISION, model_receipt_SHA256=MODEL_RECEIPT,
            active_expert_slots=1381, physical_cache_planes=1382, expert_cache_bytes=2123243520,
            workspace_reservation_bytes=50331648, prefill_tokens=32,
            normal_validation_case=11480, production_placement_case=11560, qualification_report=REPORT)
        for key in ('canonical_startup_SELF_full_readback_verified', 'installed_configuration_full_readback_verified',
                    'source_GPU_model_resources_positively_retired', 'ordinary_OS_shutdown_verified',
                    'previous_production_rollback_preserved'):
            self.i[key] = True
        self.c = dict(production_deployment_completed=True, original_restored=False, console_reserved=True,
            production_SELF=app, selected_model_receipt_SHA256=MODEL_RECEIPT, active_cache_slots=1381,
            prefill_tokens=32, normal_performance_case=11480, normal_performance_placement_case=11560,
            Expert_format='Gate_Up_Q2_K_Down_Q2_0_MSE', PLE_convolution_weight_type='BF16',
            remaining_resident_matrix_weight_type='Q8_0', selected_routing_policy=14,
            graph_reuse_disabled_for_policy=False, native_running=False, gateway_running=False, model_loaded=False)
        self.r = dict(schema='ps5-qwen-all-resident-Q8-adoption-v1', completed=True, pending_steps=[],
            application_SELF=app, previous_application_SELF=dict(sha256=CONTROL_SELF),
            driver=DRIVER, precision=PRECISION, model_receipt_SHA256=MODEL_RECEIPT, policy=POLICY,
            weight_conversion=dict(converted_tensors=544, saved_resident_payload_bytes=3163852800,
                resident_payload_bytes=4774100480, PLE_convolution_BF16_preserved=True,
                Expert_Q2_payloads_unchanged=True, other_F32_and_nonresident_tensors_unchanged=True,
                native_whole_source_seal_completed=True),
            normal=dict(case=11480, completed=True, POSTs=3, actual_native_frames_viewed=2,
                same_profile_F32_and_routes_passed=True, all_counting_answers_correct=True,
                source_model_GPU_owners_positively_retired=True, ordinary_close_exact_restore=True,
                CPU_heap_peak_bytes=500000000, device_ledger_peak_bytes=2400000000,
                actual_workspace_capacity_peak_bytes=8388608,
                independent=dict(total_ms=10., TTFT_ms=2., decode_tokens_per_second=3.),
                retained=dict(total_ms=5., TTFT_ms=1., decode_tokens_per_second=4.)),
            fixed_quality=dict(case=11520, compared_requests=8, semantic_correct_requests=8,
                all_ordered_routes_equal=True, all_application_caches_empty=True,
                same_profile_full_F32_passed=True, ordinary_close_exact_restore=True,
                application_output_normalization=False),
            placement=dict(completed=True, case=11560, normal_case=11480, verification_files=12,
                native_whole_SHA256_identity_EOF_verified=True, immediate_control_preserved=True,
                fresh_idle_confirmed=True, runtime_ownership_restored=True, native_title_running=False,
                gateway_running=False, model_loaded=False))

    def test_exact_scope_and_control_dispatch(self):
        require_resident_all_q8_production(self.i, self.c, self.r)
        with patch('prepare_first_case.read', return_value=self.r):
            self.assertEqual(qualified_control(self.c, True, self.i), self.i['application_SELF'])

    def test_refuse_incomplete_native_or_changed_precision(self):
        changes = [('weight_conversion', 'PLE_convolution_BF16_preserved', False),
            ('weight_conversion', 'converted_tensors', 545), ('weight_conversion', 'native_whole_source_seal_completed', False),
            ('driver', 'persistent_pipeline_cache', True), ('normal', 'POSTs', 2),
            ('normal', 'device_ledger_peak_bytes', 2480332801), ('normal', 'same_profile_F32_and_routes_passed', False),
            ('fixed_quality', 'semantic_correct_requests', 7), ('fixed_quality', 'ordinary_close_exact_restore', False),
            ('placement', 'native_whole_SHA256_identity_EOF_verified', False), ('placement', 'model_loaded', True)]
        for section, key, value in changes:
            with self.subTest(section=section, key=key), self.assertRaises(ValueError):
                report = copy.deepcopy(self.r)
                report[section][key] = value
                require_resident_all_q8_production(self.i, self.c, report)

    def test_refuse_mixed_models_or_nonfinite_timing(self):
        for key, value in [('model_receipt_SHA256', '0' * 64), ('pending_steps', ['native verification'])]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                require_resident_all_q8_production(self.i, self.c, dict(self.r, **{key: value}))
        report = copy.deepcopy(self.r)
        report['normal']['independent']['decode_tokens_per_second'] = float('nan')
        with self.assertRaises(ValueError):
            require_resident_all_q8_production(self.i, self.c, report)
        with patch('prepare_first_case.read', return_value=self.r), self.assertRaises(ValueError):
            qualified_control(dict(self.c, native_running=True), True, self.i)


if __name__ == '__main__':
    unittest.main()
