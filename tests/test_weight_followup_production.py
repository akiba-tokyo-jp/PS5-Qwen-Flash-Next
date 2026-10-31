# SPDX-License-Identifier: MIT
"""Refuse drift in the measured normal program's deployment admission."""
import copy,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from weight_followup_production import *

class Admission(unittest.TestCase):
    def setUp(self):
        self.r=json.loads((ROOT/REPORT).read_text())
        # Proposed placement is a fixture, never a native completion receipt.
        self.r.update(completed=True,pending_steps=[],placement=dict(completed=True,case=12260,normal_case=12220,
            verification_files=12,verified_programs=2,verified_settings=5,verified_control_settings=5,
            native_whole_SHA256_identity_EOF_verified=True,immediate_control_preserved=True,
            fresh_idle_confirmed=True,runtime_ownership_restored=True,native_title_running=False,gateway_running=False,model_loaded=False))
        self.i=dict(application_SELF=self.r['application_SELF'],previous_production_SHA256=CONTROL_SELF,
            driver=DRIVER,precision=PRECISION,model_receipt_SHA256=MODEL_RECEIPT,
            active_expert_slots=3072,physical_cache_planes=3073,expert_cache_bytes=4720619520,
            postload_quota_transfer_bytes=3207049216,postload_device_budget_bytes=5086097408,
            postload_single_buffer_bytes=1677721600,workspace_reservation_bytes=50331648,
            CPU_heap_limit_bytes=536870912,physical_Direct_reserve_bytes=536870912,
            retain_Expert_weights_between_requests=True,parallel_small_rows=True,request_and_KV_state_retained=False,
            prefill_tokens=32,normal_validation_case=12220,production_placement_case=12260)
        self.c=dict(production_SELF=self.r['application_SELF'],selected_model_receipt_SHA256=MODEL_RECEIPT,
            active_cache_slots=3072,retain_Expert_weights_between_requests=True,parallel_small_rows=True,
            prefill_tokens=32,normal_performance_case=12220,normal_performance_placement_case=12260,
            Expert_format='Gate_Up_Q2_K_Down_Q2_0_MSE',PLE_convolution_weight_type='BF16',
            remaining_resident_matrix_weight_type='Q8_0',selected_routing_policy=14,
            graph_reuse_disabled_for_policy=False,native_running=False,gateway_running=False,model_loaded=False)

    def test_qualified_fixture(self):
        require_weight_followup_production(self.i,self.c,self.r)

    def test_refuses_unsafe_or_unqualified_changes(self):
        changes=[('completed',False),('pending_steps',['placement']),('application_SELF',{}),
            ('driver',{}),('model_receipt_SHA256','0'*64),('policy',{}),('candidate_evidence',{}),
            ('all_five_candidate_dispositions_completed',False)]
        for key,value in changes:
            with self.subTest(key=key),self.assertRaises(ValueError):
                require_weight_followup_production(self.i,self.c,dict(self.r,**{key:value}))
        for section,key,value in [('normal','CPU_heap_peak_bytes',536870913),
            ('normal','device_ledger_peak_bytes',5086097409),('normal','actual_native_frames_viewed',0),
            ('normal','retained_weights_and_empty_request_memory_verified',False),
            ('normal','source_model_GPU_owners_positively_retired',False),
            ('normal','all_full_vocabulary_rows_finite',False),('placement','verification_files',11),
            ('placement','runtime_ownership_restored',False),('placement','model_loaded',True)]:
            r=copy.deepcopy(self.r);r[section][key]=value
            with self.subTest(section=section,key=key),self.assertRaises(ValueError):
                require_weight_followup_production(self.i,self.c,r)
        for key,value in [('physical_Direct_reserve_bytes',0),('request_and_KV_state_retained',True),
            ('postload_single_buffer_bytes',2147483648),('active_expert_slots',1381)]:
            with self.subTest(installation=key),self.assertRaises(ValueError):
                require_weight_followup_production(dict(self.i,**{key:value}),self.c,self.r)

if __name__=='__main__':unittest.main()
