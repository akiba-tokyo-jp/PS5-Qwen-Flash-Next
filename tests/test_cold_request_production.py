# SPDX-License-Identifier: MIT
"""Reject mismatched programs, delivery semantics and incomplete native evidence."""
import copy
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from cold_request_production import require_cold_request_production
from prepare_first_case import qualified_control


class ColdProductionTests(unittest.TestCase):
    def setUp(self):
        self.r = json.loads((ROOT / 'docs/cold-request-results-20261030.json').read_text())
        # A synthetic placement fixture exercises admission without asserting
        # that an unexecuted deployment happened. Native qualification is real.
        self.r.update(schema='ps5-qwen-cold-request-adoption-v1', completed=True, pending_steps=[])
        self.r['placement'] = dict(completed=True, case=11050, normal_case=10970,
            native_whole_SHA256_identity_EOF_verified=True, verified_programs=2,
            verified_settings=5, verified_control_settings=5, verification_files=12,
            immediate_control_preserved=True, fresh_idle_confirmed=True,
            runtime_ownership_restored=True, native_title_running=False,
            gateway_running=False, model_loaded=False)
        self.i = json.loads((ROOT / 'config/production-installation-shared-Q8-20261030.json').read_text())
        self.i.update(application_SELF=self.r['application_SELF'],
            previous_production_SHA256=self.r['previous_application_SELF']['sha256'],
            prefill_tokens=32, workspace_reservation_bytes=48 << 20,
            normal_validation_case=10970, production_placement_case=11050,
            qualification_report='docs/cold-request-adoption-20261030.json')
        self.c = dict(active_cache_slots=1381, Expert_format='Gate_Up_Q2_K_Down_Q2_0_MSE',
            output_weight_type='Q8_0', shared_Expert_weight_type='Q8_0',
            graph_reuse_disabled_for_policy=False, prefill_tokens=32,
            selected_routing_policy=14, normal_performance_case=10970,
            normal_performance_placement_case=11050,
            selected_model_receipt_SHA256=self.r['model_receipt_SHA256'],
            native_running=False, gateway_running=False, model_loaded=False,
            production_deployment_completed=True, original_restored=False,
            console_reserved=True, production_SELF=self.r['application_SELF'])

    def test_exact_selected_profile_and_dispatch(self):
        require_cold_request_production(self.i, self.c, self.r)
        with patch('prepare_first_case.read', return_value=self.r):
            self.assertEqual(qualified_control(self.c, True, self.i), self.r['application_SELF'])

    def test_actual_published_installation(self):
        report = json.loads((ROOT / 'docs/cold-request-adoption-20261030.json').read_text())
        installation = json.loads((ROOT / 'config/production-installation.json').read_text())
        require_cold_request_production(installation, self.c, report)
        self.assertEqual(qualified_control(self.c, True, installation), report['application_SELF'])

    def test_refuse_unqualified_or_mixed_evidence(self):
        changes = [('policy', 'prefill_tokens', 16), ('policy', 'workspace_reservation_bytes', 64 << 20),
            ('policy', 'maximum_parallel_source_reads', 5), ('policy', 'speculative_source_reads', True),
            ('policy', 'additional_GPU_forecast', True), ('policy', 'physical_Direct_reserve_bytes', 0),
            ('policy', 'postload_device_budget_bytes', 2480332801), ('policy', 'integer_activation_quantization', True),
            ('normal', 'CPU_heap_peak_bytes', 536870913), ('normal', 'device_ledger_peak_bytes', 2480332801),
            ('normal', 'actual_workspace_capacity_peak_bytes', 50331649),
            ('normal', 'same_policy_independent_full_F32_max_error', 1e-8),
            ('normal', 'source_model_GPU_owners_positively_retired', False),
            ('fixed_quality', 'cross_delivery_full_F32_max_error', 1e-8),
            ('fixed_quality', 'all_ordered_routes_equal', False), ('fixed_quality', 'semantic_correct_requests', 7),
            ('fixed_quality', 'all_application_caches_empty', False), ('fixed_quality', 'application_output_normalization', True),
            ('placement', 'verified_control_settings', 4), ('placement', 'native_whole_SHA256_identity_EOF_verified', False),
            ('placement', 'runtime_ownership_restored', False), ('placement', 'model_loaded', True),
            ('timing_diagnostic', 'ordinary_speed_comparison_valid', True), ('driver', 'persistent_pipeline_cache', True)]
        for section, key, value in changes:
            with self.subTest(section=section, key=key):
                report = copy.deepcopy(self.r)
                report[section][key] = value
                with self.assertRaises(ValueError):
                    require_cold_request_production(self.i, self.c, report)

    def test_exact_identity_and_closed_scope(self):
        for key, value in [('pending_steps', ['unfinished']), ('all_five_candidates_disposed', False),
                           ('model_receipt_SHA256', '0' * 64), ('dispositions', {})]:
            with self.subTest(key=key):
                report = copy.deepcopy(self.r)
                report[key] = value
                with self.assertRaises(ValueError):
                    require_cold_request_production(self.i, self.c, report)
        for key, value in [('workspace_reservation_bytes', 64 << 20), ('prefill_tokens', 16),
                           ('previous_production_SHA256', '0' * 64)]:
            with self.subTest(installed_key=key):
                installation = dict(self.i, **{key: value})
                with self.assertRaises(ValueError):
                    require_cold_request_production(installation, self.c, self.r)
        with patch('prepare_first_case.read', return_value=self.r), self.assertRaises(ValueError):
            qualified_control(dict(self.c, native_running=True), True, self.i)


if __name__ == '__main__':
    unittest.main()
