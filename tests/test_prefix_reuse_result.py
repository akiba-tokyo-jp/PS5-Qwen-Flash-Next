# SPDX-License-Identifier: MIT
import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from prefix_reuse_result import validate_prefix,prefix_process_geometry
from performance_result import validate_performance
from expert_route_result import validate_routes


class PrefixResults(unittest.TestCase):
    def fixture(self,enabled=True):
        requests=[dict(pid=123,run_id='a'*32,ordinal=i,prefill_batch_tokens=4,stop_reason='end_of_generation',
            token_ids=list(range(22)),output_bytes=list(b'1,2,3,4,5,6,7,8'),metrics=dict(prompt_tokens=30,generated_tokens=22))for i in(1,2)]
        record=dict(schema='ps5-qwen-exact-prefix-validation-result-v1',pid=123,run_id='a'*32,complete=True,
            prefix_reuse_enabled=enabled,full_F32_logit_arrays_compared=23,all_F32_logit_fingerprints_exact=True,
            original_route_rows_compared=1056 if enabled else 1440,all_original_expert_selections_exact=True,
            all_emitted_tokens_and_bytes_exact=True,emitted_once=True,additional_GPU_downloads=0,device_ledger_live_bytes=0,
            all_model_source_and_snapshot_owners_retired=True,speedup_qualified=False,
            request_logit_SHA256=[[format(n,'064x')for n in range(23)]for _ in(0,1)],
            saved_state_payload_bytes=121171968 if enabled else 0,CPU_metadata_bytes=3828 if enabled else 0,
            device_ledger_peak_bytes=1069547520,requests=[dict(ordinal=i,prefix_hit=enabled and i==2,
                reused_prompt_tokens=30 if enabled and i==2 else 0,cumulative_captures=1 if enabled else 0,
                cumulative_restores=1 if enabled and i==2 else 0,cumulative_capture_ns=1000000 if enabled else 0,
                cumulative_restore_ns=2000000 if enabled and i==2 else 0)for i in(1,2)])
        return record,requests

    def validate(self,record,requests,enabled=True):
        return validate_prefix(record,*requests,pid=123,run_id='a'*32,expected_enabled=enabled)

    def test_both_frozen_switches_count_all_work_without_claiming_speed(self):
        for enabled in(False,True):
            record,requests=self.fixture(enabled);review=self.validate(record,requests,enabled)
            self.assertFalse(review['speedup_qualified'])
            self.assertEqual(len(prefix_process_geometry(requests[0],record)),30)
            self.assertEqual(len(prefix_process_geometry(requests[1],record)),22 if enabled else 30)
            with self.assertRaises(ValueError):self.validate(record,requests,not enabled)

    def test_bad_binding_state_hash_cost_and_emission_cannot_qualify(self):
        record,requests=self.fixture()
        mutations=[lambda r:r.update(pid=124),lambda r:r.update(run_id='b'*32),lambda r:r.update(complete=False),
            lambda r:r.update(full_F32_logit_arrays_compared=22),lambda r:r.update(original_route_rows_compared=1440),
            lambda r:r.update(additional_GPU_downloads=1),lambda r:r.update(device_ledger_live_bytes=1),
            lambda r:r.update(all_model_source_and_snapshot_owners_retired=False),lambda r:r.update(speedup_qualified=True),
            lambda r:r.update(saved_state_payload_bytes=137<<20),lambda r:r.update(CPU_metadata_bytes=(1<<20)+1),
            lambda r:r.update(device_ledger_peak_bytes=(1792<<20)+1),lambda r:r['request_logit_SHA256'][1].__setitem__(0,'f'*64),
            lambda r:r['request_logit_SHA256'][1].pop(),lambda r:r['requests'][0].update(prefix_hit=True),
            lambda r:r['requests'][1].update(reused_prompt_tokens=29),lambda r:r['requests'][1].update(cumulative_captures=2),
            lambda r:r['requests'][0].update(cumulative_capture_ns=0),lambda r:r['requests'][1].update(cumulative_restore_ns=0)]
        for mutation in mutations:
            bad=copy.deepcopy(record);mutation(bad)
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):self.validate(bad,requests)
        for mutation in [lambda r:r[1]['token_ids'].__setitem__(0,55),lambda r:r[1].update(pid=124),
            lambda r:r[1].update(ordinal=True),lambda r:r[1]['metrics'].update(prompt_tokens=30.0),
            lambda r:r[1].update(stop_reason='output_token_limit')]:
            bad=copy.deepcopy(requests);mutation(bad)
            with self.assertRaises(ValueError):self.validate(record,bad)

    def test_shortened_performance_and_routes_require_the_exact_prefix_record(self):
        record,requests=self.fixture();result=requests[1]
        from test_performance_result import PerformanceResultTests
        seed=PerformanceResultTests();seed.setUp();seed.test_batched_prefill_counts_partial_prompt_batch_and_single_token_decode()
        performance=seed.record;performance['delta']['process_calls']=22
        self.assertEqual(validate_performance(performance,result,prefix_validation=record)['prefix_reused_prompt_tokens'],30)
        with self.assertRaises(ValueError):validate_performance(performance,result)
        performance['delta']['process_calls']=30
        with self.assertRaises(ValueError):validate_performance(performance,result,prefix_validation=record)
        tokens=prefix_process_geometry(result,record)
        rows=[dict(layer=il,tokens=t,ids=list(range(10))*t)for t in tokens for il in range(48)]
        route=dict(schema='ps5-qwen-completed-expert-routes-v1',complete=True,capture_failed=False,pid=123,run_id='a'*32,
            cache_reset_before_request=False,layers_per_process=48,experts=512,experts_per_token=10,cache_slots=53,maximum_records=4608,
            all_existing_downloads_and_synchronizations_returned=True,additional_GPU_downloads=0,routing_and_cache_policy_unchanged=True,
            process_calls=22,records=rows,selected_indices=10*len(rows),unique_selected_experts=10*len(rows),cache_hits=0,
            cache_misses=10*len(rows),uploaded_bytes=9830400*10*len(rows),prefetch_advice_bytes=0)
        validate_routes(route,result,width=4,pid=123,run_id='a'*32,cold=False,prefix_validation=record)
        with self.assertRaises(ValueError):validate_routes(route,result,width=4,pid=123,run_id='a'*32,cold=False)
        with self.assertRaises(ValueError):validate_routes(route,result,width=4,pid=124,run_id='a'*32,cold=False,prefix_validation=record)


if __name__=='__main__':unittest.main()
