# SPDX-License-Identifier: MIT
"""Synthetic offline decision and capture faults; no hardware speed evidence."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import cache_cohort_result as cohort
from performance_result import FIELDS
import test_cache128_result as expanded_fixture


def capture(path):
    raw = path.read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


class CacheCohort(unittest.TestCase):
    def setUp(self):
        self.arms = []
        for i, speed in enumerate((50, 60, 60, 50)):
            requests = [dict(token_ids=[1, 2], output_bytes=[49, 50], stop_reason='end_of_generation',
                metrics=dict(prompt_tokens=30, generated_tokens=2, decode_tokens_per_second=speed,
                    total_ms=100, prefill_ms=50, **({'TTFT_ms': 60} if ordinal == 0 else {'ttft_ms': 60})))
                for ordinal in range(3)]
            self.arms.append(dict(run_id=f'{i+1:032x}', common='same', policy='same', app='same',
                requests=requests, routes=[[], [], []], prompts=['same'] * 3, performance=[{}, {}, {}],
                frame_epochs=[1792675000000 + i * 100000, 1792675010000 + i * 100000],
                clock_uncertainty_ms=100, CPU_heap_peak_bytes=128 << 20, postload_device_peak_bytes=1024 << 20))

    def test_both_orders_all_outputs_and_placement_remain_separate(self):
        result = cohort.compare(self.arms)
        self.assertTrue(result['speed_qualified'])
        self.assertFalse(result['production_adopted'])
        self.assertFalse(result['statistical_significance_claimed'])
        self.assertEqual(result['order'], [53, 128, 128, 53])
        self.assertFalse(result['requests'][0]['included_in_primary_speed'])

    def test_noisy_or_reversed_order_cannot_be_adopted(self):
        for speeds in ((50, 51, 51, 52), (50, 49, 60, 50), (50, 60, 51, 50)):
            arms = copy.deepcopy(self.arms)
            for arm, speed in zip(arms, speeds):
                for request in arm['requests']: request['metrics']['decode_tokens_per_second'] = speed
            with self.subTest(speeds=speeds):
                self.assertFalse(cohort.compare(arms)['speed_qualified'])
        arms = copy.deepcopy(self.arms)
        for request in arms[1]['requests'] + arms[2]['requests']:
            request['metrics']['decode_tokens_per_second'] = 49
        self.assertEqual(cohort.compare(arms)['state'], 'retain_control_slower_in_both_orders')

    def test_candidate_latency_spread_cannot_hide_setup_or_TTFT_regression(self):
        for ordinal, key in ((0, 'TTFT_ms'), (1, 'total_ms'), (2, 'ttft_ms'), (2, 'prefill_ms')):
            arms = copy.deepcopy(self.arms)
            arms[1]['requests'][ordinal]['metrics'][key] *= 3
            with self.subTest(ordinal=ordinal, key=key):
                result = cohort.compare(arms)
                self.assertFalse(result['speed_qualified'])
                self.assertEqual(result['state'], 'retain_control_latency_regression')

    def test_identity_output_route_prompt_count_and_order_faults(self):
        mutations = [lambda a: a[1].update(common='other model'), lambda a: a[1].update(policy='other driver'),
            lambda a: a[1].update(app='other config'), lambda a: a[1].update(routes=[[1], [], []]),
            lambda a: a[1].update(prompts=['different'] * 3), lambda a: a[1].update(run_id=a[0]['run_id']),
            lambda a: a[1]['requests'][1].update(token_ids=[3, 4]),
            lambda a: a[1]['requests'][1].update(output_bytes=[51]),
            lambda a: a[1]['requests'][1]['metrics'].update(prompt_tokens=31),
            lambda a: a[1]['requests'][1]['metrics'].update(decode_tokens_per_second=float('nan')),
            lambda a: a[1].update(frame_epochs=a[0]['frame_epochs']),
            lambda a: a[1].update(clock_uncertainty_ms=1000000)]
        for change in mutations:
            arms = copy.deepcopy(self.arms); change(arms)
            with self.subTest(change=change), self.assertRaises(ValueError): cohort.compare(arms)

    def test_whole_native_arm_reuses_existing_reviewers_and_rejects_mutated_capture(self):
        # Reuse the complete existing synthetic native fixture, not a fabricated
        # positive native-review boolean. Its sparse bitmaps are test containers.
        fixture = expanded_fixture.Cache128Records()
        fixture.setUp(); self.addCleanup(fixture.doCleanups); fixture.expanded()
        fixture.records['']['source_pipeline_worker_stopped'] = True
        for suffix in ('.first', '.demo1', '.demo2'):
            request = fixture.records[suffix + '.result']; request['prefill_batch_tokens'] = 4
            delta = dict.fromkeys(FIELDS, 0)
            delta.update(source_bytes=100, source_chunks=2, source_completed_windows=2,
                source_read_ns=1, process_ns=1000, process_calls=5, source_parallel_batches=1,
                source_coalesced_batches=0, source_selected_serial_batches=0, source_pipeline_batches=0,
                source_physical_read_bytes=128, source_physical_read_calls=2,
                source_worker_read_ns=1, source_worker_dispatch_ns=1,
                source_direct_bank_bytes=0, source_direct_bank_reads=0, source_padded_scatter_bytes=0)
            fixture.records[suffix + '.performance'] = dict(schema='ps5-qwen-completed-performance-v5',
                process_includes_source_and_backend_work=True, GPU_timestamp_queries=False,
                hot_path_logs_added=False, GPU_operations_added=False, source_read_ns_is_producer_wait_time=True,
                maximum_parallel_source_reads=2, file_range_schedule_enabled=True,
                physical_read_bytes_include_alignment=True, worker_times_overlap_consumers=True,
                owned_padded_bank_IO=True, prefill_batch_tokens=4, generated_token_batch_tokens=1,
                all_prompt_outputs_requested=True, delta=delta)
        fixture.records['.demo2.display.json']['epoch_ms'] += 1000
        fixture.records['.memory.backpressure'] = dict(schema='ps5-qwen-memory-backpressure-v2',
            enabled=True, maximum_boundary_wait_ms=20000, maximum_total_wait_ms=60000, poll_interval_ms=100,
            memory_reserves_unchanged=True, IO_or_GPU_operations_retried=False, last_qualified=True,
            kernel_page_size=16384, kernel_extra_margin_bytes=4 << 20, observations=1, pressure_events=0,
            recovered_admissions=0, cumulative_wait_ns=0, pause_calls=0, kernel_free_pages=3000,
            kernel_minimum_pages=898, kernel_reserved_pages=206)
        fixture.save()
        root = fixture.result.parent
        profile = json.loads((Path(__file__).resolve().parents[1] / 'config/qualified-performance.json').read_text())
        padded = copy.deepcopy(profile['selected_native_policy']['native_padded_expert_cache'])
        proof = fixture.binding['cache128']['layout_qualification']
        padded.update(schema='ps5-qwen-owned-padded-expert-cache-v2', active_slots=128,
            physical_planes=129, cache_cap_bytes=cohort.CACHE_BYTES,
            layout_qualification_SELF_SHA256=proof['SELF_sha256'], layout_qualification_result_SHA256=proof['report_sha256'])
        policy = dict(native_first_generation_validation=dict(run_id=fixture.binding['run_id'],
            candidate_SELF_sha256=fixture.binding['candidate_SELF_sha256'],
            model_receipt_sha256=fixture.binding['model_receipt_sha256'], persistent_caches_enabled=False),
            native_padded_expert_cache=padded, native_large_cache_scope=dict(
                schema='ps5-qwen-cache-128-experiment-v1', stage='model', active_slots=128, physical_planes=129,
                cache_request_bytes=cohort.CACHE_BYTES, context_tokens=256, context_allowance_bytes=256 << 20,
                CPU_heap_cap_bytes=512 << 20, device_ledger_cap_bytes=1792 << 20,
                precision_unchanged=True, automatic_retries=0, layout_qualification=proof))
        app = dict(schema='ps5-qwen-app-v1', mode='first-generation-validation', native_display=False, port=8086,
            admission_report='/app0/qwen-runtime/plan-' + fixture.binding['run_id'] + '.json',
            clock_calibration=dict(schema='ps5-qwen-clock-offset-v1', console_epoch_ms=1792675000000,
                utc_epoch_ms=1792675000000, uncertainty_ms=100))
        arm = dict(active_slots=128, result=capture(fixture.result))
        for key, value in (('binding', fixture.binding), ('policy', policy), ('app', app)):
            path = root / (key + '.json'); path.write_text(json.dumps(value), encoding='utf-8'); arm[key] = capture(path)
        arm['evidence'] = [capture(p) for p in sorted(root.glob(fixture.result.name + '.*'))]
        reviewed = cohort.review_arm(arm, root)
        self.assertEqual(reviewed['run_id'], fixture.binding['run_id'])
        fixture.records['.demo1.performance']['delta']['source_read_ns'] = 0; fixture.save()
        with self.assertRaisesRegex(ValueError, 'SHA256'): cohort.review_arm(arm, root)
        arm['evidence'] = [capture(p) for p in sorted(root.glob(fixture.result.name + '.*'))]
        with self.assertRaisesRegex(ValueError, 'Source intervals'): cohort.review_arm(arm, root)

    def test_manifest_is_finite_and_does_not_accept_partial_or_wrong_order(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1] / '.test-tmp') as directory:
            path = Path(directory) / 'cohort.json'
            for order in ((53,), (53, 128, 53, 128)):
                path.write_text(json.dumps(dict(schema='ps5-qwen-cache-capacity-cohort-v1',
                    timing_boundary=cohort.TIMING, arms=[dict(active_slots=n) for n in order])), encoding='utf-8')
                with self.subTest(order=order), self.assertRaisesRegex(ValueError, 'order'): cohort.review(path)

    def test_both_capacities_retain_actual_separate_Direct_reserves(self):
        for slots, cache, reserve in ((53, 512 << 20, 1920 << 20), (128, cohort.CACHE_BYTES, 1152 << 20)):
            record = dict(model_loaded=True, expert_cache_requested_bytes=cache,
                remaining_context_workspace_staging_reserve_bytes=reserve,
                device_budget_source='canary-validated native Direct allocator',
                native_Direct_available_bytes=cache + reserve, native_Direct_owned_bytes=8 << 30,
                native_Direct_pool_bytes=(8 << 30) + cache + reserve)
            cohort.validate_after_load(record, slots)
            for key, value in (('native_Direct_available_bytes', cache + reserve - 1),
                    ('remaining_context_workspace_staging_reserve_bytes', reserve - 1),
                    ('native_Direct_pool_bytes', 1), ('expert_cache_requested_bytes', True)):
                bad = dict(record); bad[key] = value
                with self.subTest(slots=slots, key=key), self.assertRaises(ValueError):
                    cohort.validate_after_load(bad, slots)

    def test_policy_normalization_allows_only_priced_geometry_and_run_identity(self):
        profile = json.loads((Path(__file__).resolve().parents[1] / 'config/qualified-performance.json').read_text())
        expected = dict(run_id='a' * 32, candidate_SELF_sha256='b' * 64, model_receipt_sha256='c' * 64)
        control = dict(native_first_generation_validation=dict(**expected, persistent_caches_enabled=False),
            native_padded_expert_cache=copy.deepcopy(profile['selected_native_policy']['native_padded_expert_cache']),
            native_source_schedule=dict(maximum_outstanding_reads=2))
        proof = dict(run_id='d' * 32, pid=900, report_path='/app0/qwen-runtime/plan-' + 'd' * 32 + '.json.padded-layout',
            report_bytes=1000, report_sha256='e' * 64, SELF_sha256='f' * 64)
        expanded = copy.deepcopy(control)
        expanded['native_padded_expert_cache'].update(schema='ps5-qwen-owned-padded-expert-cache-v2',
            active_slots=128, physical_planes=129, cache_cap_bytes=cohort.CACHE_BYTES,
            layout_qualification_SELF_SHA256=proof['SELF_sha256'], layout_qualification_result_SHA256=proof['report_sha256'])
        expanded['native_large_cache_scope'] = dict(schema='ps5-qwen-cache-128-experiment-v1', stage='model',
            active_slots=128, physical_planes=129, cache_request_bytes=cohort.CACHE_BYTES, context_tokens=256,
            context_allowance_bytes=256 << 20, CPU_heap_cap_bytes=512 << 20, device_ledger_cap_bytes=1792 << 20,
            precision_unchanged=True, automatic_retries=0, layout_qualification=proof)
        bound = dict(expected, cache128=dict(layout_qualification=proof))
        key = cohort.comparable_policy(control, expected, 53)
        self.assertEqual(key, cohort.comparable_policy(expanded, bound, 128))
        altered = copy.deepcopy(expanded); altered['native_source_schedule']['maximum_outstanding_reads'] = 1
        self.assertNotEqual(key, cohort.comparable_policy(altered, bound, 128))
        for change in (lambda p: p['native_large_cache_scope'].update(context_tokens=128),
                lambda p: p.update(native_model_free_speculation={}),
                lambda p: p['native_padded_expert_cache'].update(physical_planes=True),
                lambda p: p['native_first_generation_validation'].update(persistent_caches_enabled=True)):
            altered = copy.deepcopy(expanded); change(altered)
            with self.subTest(change=change), self.assertRaises(ValueError): cohort.comparable_policy(altered, bound, 128)


if __name__ == '__main__':
    unittest.main()
