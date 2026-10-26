# SPDX-License-Identifier: MIT
import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from model_checkpoint_result import validate_checkpoint,checkpoint_process_geometry
from performance_result import validate_performance
from expert_route_result import validate_routes


class CompleteCheckpointResultTests(unittest.TestCase):
    def fixture(self):
        result=dict(stop_reason='end_of_generation',prefill_batch_tokens=4,token_ids=list(range(22)),
            metrics=dict(prompt_tokens=30,generated_tokens=22))
        record=dict(schema='ps5-qwen-model-checkpoint-validation-result-v1',pid=123,run_id='a'*32,
            captures=25,restores=25,prefill_replays=2,next_replays_including_EOG=23,
            capture_positions=[4,28,30]+list(range(30,52)),original_route_rows_compared=1152,
            absolute_tolerance=1e-5,relative_tolerance=1e-5,
            effective_F32_logits_positions_pending_prompt_and_greedy_state_restored=True,
            all_original_expert_selections_exact=True,all_continuation_tokens_and_bytes_exact=True,emitted_once=True,
            device_ledger_live_bytes=0,all_model_source_and_checkpoint_owners_retired=True,
            performance_adoption_enabled=False,prefix_reuse_qualified=False,speculative_verification_qualified=False,
            maximum_state_payload_bytes=130<<20,maximum_CPU_metadata_bytes=10000,
            device_ledger_peak_bytes=1050<<20,maximum_absolute_logit_error=0.0)
        return record,result

    def test_exact_continuation_geometry_and_no_speed_claim(self):
        record,result=self.fixture();summary=validate_checkpoint(record,result,pid=123,run_id='a'*32)
        tokens=checkpoint_process_geometry(result,record)
        self.assertEqual(len(tokens),54);self.assertEqual(tokens[:10],[4]*8+[2]*2)
        self.assertFalse(summary['speedup_qualified']);self.assertFalse(summary['prefix_reuse_qualified'])
        bad=copy.deepcopy(record);bad['capture_positions']=[4,28]+list(range(30,53))
        with self.assertRaises(ValueError):validate_checkpoint(bad,result,pid=123,run_id='a'*32)

    def test_wrong_owner_partial_states_resources_and_inferred_adoption_refuse(self):
        record,result=self.fixture()
        changes=[('pid',124),('run_id','b'*32),('captures',24),('restores',24),('prefill_replays',1),
            ('next_replays_including_EOG',22),('original_route_rows_compared',1104),('capture_positions',[4,28]),
            ('all_original_expert_selections_exact',False),('emitted_once',False),('device_ledger_live_bytes',1),
            ('maximum_state_payload_bytes',137<<20),('maximum_CPU_metadata_bytes',(1<<20)+1),
            ('device_ledger_peak_bytes',(1792<<20)+1),('maximum_absolute_logit_error',float('nan')),
            ('all_model_source_and_checkpoint_owners_retired',False),('performance_adoption_enabled',True),
            ('prefix_reuse_qualified',True),('speculative_verification_qualified',True)]
        for key,value in changes:
            bad=copy.deepcopy(record);bad[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):validate_checkpoint(bad,result,pid=123,run_id='a'*32)
        for mutation in [lambda r:r.update(stop_reason='output_token_limit'),lambda r:r.update(prefill_batch_tokens=2),
            lambda r:r['metrics'].update(generated_tokens=21),lambda r:r['metrics'].update(prompt_tokens=29)]:
            bad=copy.deepcopy(result);mutation(bad)
            with self.assertRaises(ValueError):validate_checkpoint(record,bad,pid=123,run_id='a'*32)

    def test_replays_cannot_pass_the_normal_performance_or_route_validator(self):
        record,result=self.fixture();tokens=checkpoint_process_geometry(result,record)
        # Reuse the ordinary performance controls; change only the deliberately doubled process count.
        from test_performance_result import PerformanceResultTests
        control=PerformanceResultTests();control.setUp();control.test_batched_prefill_counts_partial_prompt_batch_and_single_token_decode()
        performance=control.record;performance['delta']['process_calls']=54
        validate_performance(performance,result,checkpoint_validation=record)
        with self.assertRaises(ValueError):validate_performance(performance,result)
        performance['delta']['process_calls']=30
        with self.assertRaises(ValueError):validate_performance(performance,result,checkpoint_validation=record)
        rows=[dict(layer=layer,tokens=t,ids=list(range(10))*t)for t in tokens for layer in range(48)]
        route=dict(schema='ps5-qwen-completed-expert-routes-v1',complete=True,capture_failed=False,pid=123,run_id='a'*32,
            cache_reset_before_request=False,layers_per_process=48,experts=512,experts_per_token=10,cache_slots=53,maximum_records=4608,
            all_existing_downloads_and_synchronizations_returned=True,additional_GPU_downloads=0,routing_and_cache_policy_unchanged=True,
            process_calls=54,records=rows,selected_indices=sum(10*r['tokens']for r in rows),unique_selected_experts=10*len(rows),
            cache_hits=0,cache_misses=10*len(rows),uploaded_bytes=9830400*10*len(rows),prefetch_advice_bytes=0)
        validate_routes(route,result,width=4,pid=123,run_id='a'*32,cold=False,checkpoint_validation=record)
        with self.assertRaises(ValueError):validate_routes(route,result,width=4,pid=123,run_id='a'*32,cold=False)
        rows[48]['tokens']=2
        with self.assertRaises(ValueError):validate_routes(route,result,width=4,pid=123,run_id='a'*32,cold=False,checkpoint_validation=record)


if __name__=='__main__':unittest.main()
