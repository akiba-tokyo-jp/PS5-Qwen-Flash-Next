# SPDX-License-Identifier: MIT
import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from model_free_speculation_result import validate_speculation
from performance_result import FIELDS,validate_performance
class SpeculativeResultTests(unittest.TestCase):
    def setUp(self):
        self.rows=[dict(ordinal=i+1,controller_enabled=bool(i),request_reset_completed=True,
            attempts=3*i,accepted=2*i,rejected=i,queued_bonus_samples=2*i,
            proposal_checks=4*i,no_draft=i,prompt_proposals=0,generated_proposals=3*i)for i in range(2)]
        self.report=dict(schema='ps5-qwen-causal-width-two-result-v1',pid=123,run_id='a'*32,requests=self.rows,
            all_control_token_IDs_and_bytes_exact=True,all_model_source_and_checkpoint_owners_retired=True,
            device_ledger_live_bytes=0,cache_condition_comparison_is_not_speed_qualification=True,speedup_qualified=False,
            target_width_two_exercised=True,
            complete_checkpoint_qualification_SHA256='e9d0db6bfb5b2d090e021c972cf14728f3a7d96b956c03b08946a60d6fdb50d7')
        self.request=dict(ordinal=2,token_ids=list(range(22)),output_bytes=list(range(65,87)),stop_reason='end_of_generation',
            request_reset_completed=True,prefill_batch_tokens=4,metrics=dict(prompt_tokens=30,generated_tokens=22))
        self.result=dict(pid=123,run_id='a'*32,demonstration=dict(requests=[copy.deepcopy(self.request),copy.deepcopy(self.request)]))
        self.result['demonstration']['requests'][0]['ordinal']=1
        self.perf=dict(schema='ps5-qwen-completed-performance-v6',process_includes_source_and_backend_work=True,
            GPU_timestamp_queries=False,hot_path_logs_added=True,GPU_operations_added=True,
            prefill_batch_tokens=4,ordinary_generated_token_batch_tokens=1,target_verification_batch_tokens=2,
            all_prompt_outputs_requested=True,source_read_ns_is_producer_wait_time=True,maximum_parallel_source_reads=2,
            worker_times_overlap_consumers=True,file_range_schedule_enabled=True,physical_read_bytes_include_alignment=True,
            speculation={k:self.rows[1][k]for k in('attempts','accepted','rejected','queued_bonus_samples')},delta=dict.fromkeys(FIELDS,1))
        self.perf['delta'].update(source_chunks=2,source_completed_windows=2,source_pipeline_batches=0,
            source_worker_read_ns=1,source_worker_dispatch_ns=1,source_parallel_batches=1,source_coalesced_batches=0,
            source_selected_serial_batches=0,source_physical_read_bytes=65536,source_physical_read_calls=2,
            process_calls=29,process_ns=1000,synchronize_ns=0)
    def test_retired_target_comparison_is_not_speed_qualification(self):
        r=validate_speculation(self.report,self.result)
        self.assertTrue(r['native_width_two_exercised']);self.assertTrue(r['native_rejection_exercised'])
        self.assertFalse(r['speedup_qualified'])
    def test_missing_bonus_reset_identity_and_output_are_rejected(self):
        for key,value in (('device_ledger_live_bytes',1),('pid',124),('target_width_two_exercised',False),('speedup_qualified',True)):
            bad=copy.deepcopy(self.report);bad[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):validate_speculation(bad,self.result)
        for key,value in (('queued_bonus_samples',1),('request_reset_completed',False),('controller_enabled',False),('generated_proposals',2)):
            bad=copy.deepcopy(self.report);bad['requests'][1][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):validate_speculation(bad,self.result)
        bad=copy.deepcopy(self.result);bad['demonstration']['requests'][1]['token_ids']=[1,3]
        with self.assertRaises(ValueError):validate_speculation(self.report,bad)
    def test_process_count_includes_rejections_and_saved_bonus_steps(self):
        r=validate_performance(self.perf,self.request,split_sources=True,speculative_validation=self.rows[1])
        self.assertTrue(r['speculative_verification_included'])
        for calls in (28,30):
            bad=copy.deepcopy(self.perf);bad['delta']['process_calls']=calls
            with self.assertRaises(ValueError):validate_performance(bad,self.request,split_sources=True,speculative_validation=self.rows[1])
        with self.assertRaises(ValueError):validate_performance(self.perf,self.request,split_sources=True)
        bad=copy.deepcopy(self.perf);bad['speculation']['rejected']=0
        with self.assertRaises(ValueError):validate_performance(bad,self.request,speculative_validation=self.rows[1])
if __name__=='__main__':unittest.main()
