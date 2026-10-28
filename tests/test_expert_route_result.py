# SPDX-License-Identifier: MIT
import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from expert_route_result import validate_routes


class RouteResultTests(unittest.TestCase):
    def test_bound_cache128_prefix_requires_all_decode_layers_and_exact_geometry(self):
        record,result=self.fixture()
        result['metrics'].update(prompt_tokens=30,generated_tokens=22)
        rows=[dict(layer=layer,tokens=1,ids=list(range(10)))for _ in range(22)for layer in range(48)]
        record.update(cache_slots=128,cache_reset_before_request=False,records=rows,process_calls=22,
            selected_indices=10*len(rows),unique_selected_experts=10*len(rows),cache_hits=0,
            cache_misses=10*len(rows),uploaded_bytes=9830400*10*len(rows))
        args=dict(width=4,pid=123,run_id='a'*32,cold=False,expected_slots=128,reused_prompt_tokens=30)
        self.assertEqual(validate_routes(record,result,**args)['process_calls'],22)
        for key,value in (('cold',True),('width',2),('expected_slots',53),('reused_prompt_tokens',True),
                          ('reused_prompt_tokens',29),('predictive_cache',True)):
            bad=dict(args);bad[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):validate_routes(record,result,**bad)
        bad=copy.deepcopy(record);bad['records'].pop()
        with self.assertRaises(ValueError):validate_routes(bad,result,**args)
        bad=copy.deepcopy(result);bad['metrics']['prompt_tokens']=29
        with self.assertRaises(ValueError):validate_routes(record,bad,**args)

    def fixture(self,width=4,reason='end_of_generation'):
        result=dict(metrics=dict(prompt_tokens=7,generated_tokens=2),stop_reason=reason)
        tokens=[min(width,7-n)for n in range(0,7,width)]+[1]*(2-(reason=='output_token_limit'))
        rows=[dict(layer=il,tokens=t,ids=list(range(10))*t)for t in tokens for il in range(48)]
        record=dict(schema='ps5-qwen-completed-expert-routes-v1',complete=True,capture_failed=False,pid=123,run_id='a'*32,
            cache_reset_before_request=True,layers_per_process=48,experts=512,experts_per_token=10,cache_slots=53,maximum_records=4608,
            all_existing_downloads_and_synchronizations_returned=True,additional_GPU_downloads=0,routing_and_cache_policy_unchanged=True,
            process_calls=len(tokens),records=rows,selected_indices=sum(10*r['tokens']for r in rows),
            unique_selected_experts=10*len(rows),cache_hits=0,cache_misses=10*len(rows),uploaded_bytes=9830400*10*len(rows),prefetch_advice_bytes=0)
        return record,result

    def validate(self,r,result,width=4):return validate_routes(r,result,width=width,pid=123,run_id='a'*32,cold=True)

    def test_predictive_transfer_is_additional_not_hidden_in_demand(self):
        record,result=self.fixture();extra=3*9830400
        record.update(schema='ps5-qwen-completed-expert-routes-v2',routing_and_cache_policy_unchanged=False,
            original_routing_unchanged=True,predictive_cache_enabled=True,predictive_uploaded_bytes=extra,
            demand_uploaded_bytes=record['uploaded_bytes'],uploaded_bytes=record['uploaded_bytes']+extra)
        args=dict(width=4,pid=123,run_id='a'*32,cold=True,predictive_cache=True)
        self.assertEqual(validate_routes(record,result,**args)['uploaded_bytes'],record['uploaded_bytes'])
        with self.assertRaises(ValueError):self.validate(record,result)
        for key in ('uploaded_bytes','demand_uploaded_bytes','predictive_uploaded_bytes'):
            bad=copy.deepcopy(record);bad[key]+=1
            with self.assertRaises(ValueError):validate_routes(bad,result,**args)

    def test_speculative_rows_count_rejected_branch_and_accepted_union(self):
        record,result=self.fixture();result['metrics']['generated_tokens']=4
        tokens=[4,3,1,2,2,1]  # Two verification batches: one accepted, one rejected.
        rows=[dict(layer=l,tokens=t,ids=list(range(10))*t)for t in tokens for l in range(48)]
        record.update(records=rows,process_calls=len(tokens),selected_indices=sum(10*r['tokens']for r in rows),
            unique_selected_experts=10*len(rows),cache_hits=0,cache_misses=10*len(rows),uploaded_bytes=9830400*10*len(rows))
        count=dict(attempts=2,accepted=1,rejected=1,queued_bonus_samples=1)
        args=dict(width=4,pid=123,run_id='a'*32,cold=True,speculative_validation=count)
        self.assertEqual(validate_routes(record,result,**args)['process_calls'],6)
        bad=copy.deepcopy(record)
        for row in bad['records'][3*48:4*48]:row['tokens']=1;row['ids']=list(range(10))
        with self.assertRaises(ValueError):validate_routes(bad,result,**args)

    def test_partial_batches_single_token_generation_and_output_limit(self):
        for width in (1,2,4):
            for reason in ('end_of_generation','output_token_limit'):
                r,result=self.fixture(width,reason);summary=self.validate(r,result,width)
                self.assertEqual(summary['selected_indices'],480*(7+2-(reason=='output_token_limit')))

    def test_failed_capture_wrong_owner_missing_layers_and_changed_precision_scope(self):
        mutations=[lambda r:r.update(complete=False),lambda r:r.update(capture_failed=True),lambda r:r.update(pid=124),
            lambda r:r.update(additional_GPU_downloads=1),lambda r:r.update(cache_slots=54),lambda r:r.update(cache_reset_before_request=False),
            lambda r:r['records'].pop(),lambda r:r['records'][0].update(layer=1),lambda r:r['records'][0].update(tokens=3),
            lambda r:r['records'][0]['ids'].__setitem__(0,512),lambda r:r['records'][0]['ids'].__setitem__(0,True),
            lambda r:r['records'][0]['ids'].__setitem__(0,1),lambda r:r.update(cache_hits=1),lambda r:r.update(uploaded_bytes=0),
            lambda r:r.update(prefetch_advice_bytes=1),lambda r:r.update(selected_indices=0)]
        record,result=self.fixture()
        for mutate in mutations:
            bad=copy.deepcopy(record);mutate(bad)
            with self.assertRaises(ValueError):self.validate(bad,result)


if __name__=='__main__':unittest.main()
