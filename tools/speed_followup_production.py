# SPDX-License-Identifier: MIT
"""Admit only the qualified finite identical-prompt speed composition."""
import math
from weight_followup_production import DRIVER,MODEL_RECEIPT,PRECISION,POLICY as PREVIOUS_POLICY
REPORT='docs/speed-followup-adoption-20261031.json'
SELECTED_SELF='5564792aa1a8e193d60a13e0ea12f8293900fbc8c2e8ff3c8414c7c8ac212257'
CONTROL_SELF='3066dfe45c32d0586e3bdddb9e9ab31b200b3185a20aa0206e2418f326b2002f'
POLICY=dict(PREVIOUS_POLICY,owned_BF16_row_cache=True,row_cache_payload_bytes=491520,
    row_cache_allocation_bytes=525344,decode_prefill_protection=True,maximum_protected_keys=1536,
    protection_scope='compiled_identical_prompt_finite_normal_only',maximum_speculative_attempts=6,
    bounded_four_lane_delivery_counters=True)

def require_speed_followup_production(installation,context,report):
    def need(v,message):
        if not v:raise ValueError(message)
    need(report.get('schema')=='ps5-qwen-speed-followup-adoption-v1'and report.get('completed')is True and
         report.get('pending_steps')==[]and report.get('all_current_candidate_dispositions_completed')is True,
         'Completed speed dispositions, numerical qualification and placement required')
    need(report.get('application_SELF')==installation.get('application_SELF')==dict(bytes=20089335,sha256=SELECTED_SELF)and
         report.get('previous_application_SELF',{}).get('sha256')==installation.get('previous_production_SHA256')==CONTROL_SELF and
         context.get('production_SELF',{}).get('sha256')==SELECTED_SELF,'Exact new program and immediate3066 control required')
    need(report.get('driver')==installation.get('driver')==DRIVER and report.get('precision')==installation.get('precision')==PRECISION and
         report.get('model_receipt_SHA256')==installation.get('model_receipt_SHA256')==context.get('selected_model_receipt_SHA256')==MODEL_RECEIPT,
         'Qualified driver and unchanged complete model precision/receipt required')
    need(report.get('policy')==POLICY and installation.get('speed_followup_policy')==POLICY and context.get('speed_followup_policy')==POLICY,
         'Exact bounded fixed-prompt policy required; arbitrary prompts are not qualified')
    for key,value in dict(active_expert_slots=3072,physical_cache_planes=3073,expert_cache_bytes=4720619520,
        postload_quota_transfer_bytes=3207049216,postload_device_budget_bytes=5086097408,
        postload_single_buffer_bytes=1677721600,workspace_reservation_bytes=50331648,
        CPU_heap_limit_bytes=536870912,physical_Direct_reserve_bytes=536870912,prefill_tokens=32).items():
        need(installation.get(key)==value,'Original installed geometry or reserve changed: '+key)
    need(context.get('active_cache_slots')==3072 and context.get('prefill_tokens')==32 and
         all(installation.get(k)is True and context.get(k)is True for k in('retain_Expert_weights_between_requests','parallel_small_rows'))and
         installation.get('request_and_KV_state_retained')is False and context.get('request_and_KV_state_retained')is False,
         'Independent request/KV resets and retained weight banks required')
    q=report.get('headless',{})
    need(q.get('case')==12420 and q.get('requests')==q.get('contents_correct')==16 and
         all(q.get(k)is True for k in('completed','matched_row_cache_full_F32_SHA256_routes_tokens_bytes_exact',
             'original_weight_payloads_and_reserves_unchanged','ordinary_close_exact_restore')),
         'Complete finite headless controls and exact byte-cache arithmetic required')
    comparison=report.get('causal_budget_comparison',{})
    need(comparison.get('control_case')==12460 and comparison.get('candidate_case')==12500 and
         comparison.get('attempt_caps')==[8,6]and all(comparison.get(k)is True for k in
             ('same_model_driver_and_providers','all_counting_tokens_and_bytes_equal','both_cases_closed_and_restored'))and
         comparison.get('completion_tail_reduction_ms',0)>0 and comparison.get('complete_request_time_reduction_percent',0)>0,
         'Actual matched-budget completion and whole-request gain required')
    normal=report.get('normal',{})
    need(normal.get('case')==installation.get('normal_validation_case')==context.get('normal_performance_case')==12500 and
         normal.get('completed')is True and normal.get('POSTs')==3 and normal.get('actual_native_frames_viewed')==2 and
         all(normal.get(k)is True for k in('all_full_vocabulary_rows_finite','all_counting_tokens_and_bytes_equal',
             'complete_actual_routes_verified','retained_weights_and_empty_request_memory_verified',
             'source_model_GPU_owners_positively_retired','ordinary_close_exact_restore')),
         'Complete normal/API/display and positive owner retirement required')
    for key,cap in(('CPU_heap_peak_bytes',536870912),('device_ledger_peak_bytes',5086097408),('actual_workspace_capacity_peak_bytes',50331648)):
        need(type(normal.get(key))is int and 0<normal[key]<=cap,'Native allocation cap exceeded')
    for kind in('cold_start','request_reset_weights_retained','exact_prefix_repeat'):
        m=normal.get(kind,{})
        need(all(type(m.get(k))in(int,float)and math.isfinite(m[k])and m[k]>0 for k in('total_ms','TTFT_ms','decode_tokens_per_second')),
             'Actual complete native timings required')
    placement=report.get('placement',{})
    need(placement.get('completed')is True and placement.get('case')==installation.get('production_placement_case')==context.get('normal_performance_placement_case')and
         placement.get('normal_case')==12500 and placement.get('verification_files')==12 and
         placement.get('verified_programs')==2 and placement.get('verified_settings')==placement.get('verified_control_settings')==5 and
         all(placement.get(k)is True for k in('native_whole_SHA256_identity_EOF_verified','immediate_control_preserved','fresh_idle_confirmed','runtime_ownership_restored'))and
         all(placement.get(k)is False for k in('native_title_running','gateway_running','model_loaded')),
         'Both programs, both five-setting sets and fresh idle required')
    need(context.get('Expert_format')=='Gate_Up_Q2_K_Down_Q2_0_MSE'and context.get('PLE_convolution_weight_type')=='BF16'and
         context.get('remaining_resident_matrix_weight_type')=='Q8_0'and context.get('selected_routing_policy')==14 and
         context.get('graph_reuse_disabled_for_policy')is False and
         all(context.get(k)is False for k in('native_running','gateway_running','model_loaded')),
         'Precision, routing and idle owner state changed')
