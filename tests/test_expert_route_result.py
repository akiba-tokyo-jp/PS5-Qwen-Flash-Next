# SPDX-License-Identifier: MIT
import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from expert_route_result import validate_routes


class RouteResultTests(unittest.TestCase):
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
