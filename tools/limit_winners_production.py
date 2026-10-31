# SPDX-License-Identifier: MIT
"""Admit the measured placement winner, its finite normal case and exact install."""
import math
from speed_followup_production import DRIVER,MODEL_RECEIPT,PRECISION,POLICY,SELECTED_SELF as CONTROL_SELF
REPORT='docs/limit-winners-adoption-20261031.json'
SELECTED_SELF='a5375d766aecf7a2f9c45818d008a6da0fc65dcabe2cf38b2a94fe2eefe7e8c9'
SELECTED_BYTES=20098631

def require_limit_winners_production(installation,context,report):
    def need(value,message):
        if not value:raise ValueError(message)
    need(report.get('schema')=='ps5-qwen-limit-winners-adoption-v1'and report.get('completed')is True and report.get('pending_steps')==[],
         'Complete native comparison, normal qualification and placement required')
    need(report.get('application_SELF')==installation.get('application_SELF')==dict(bytes=SELECTED_BYTES,sha256=SELECTED_SELF)and
         context.get('production_SELF',{}).get('sha256')==SELECTED_SELF and
         report.get('previous_application_SELF',{}).get('sha256')==installation.get('previous_production_SHA256')==CONTROL_SELF,
         'Exact qualified program and immediate5564 rollback required')
    need(report.get('driver')==installation.get('driver')==DRIVER and report.get('precision')==installation.get('precision')==PRECISION and
         report.get('model_receipt_SHA256')==installation.get('model_receipt_SHA256')==context.get('selected_model_receipt_SHA256')==MODEL_RECEIPT,
         'Qualified pinned driver, complete unchanged model and precision required')
    need(report.get('policy')==installation.get('speed_followup_policy')==context.get('speed_followup_policy')==POLICY,
         'Original qualified finite prompt, rows, protection and six-attempt policy required')
    limits=report.get('limit_winner_policy',{})
    need(installation.get('total_bundled_Experts')==context.get('total_bundled_Experts')==676 and
         installation.get('supplemental_Expert_bundles')==context.get('supplemental_Expert_bundles')==256,
         'Current host bundle-count labels must match the compiled selected pack')
    need(limits==installation.get('limit_winner_policy')==context.get('limit_winner_policy')and
         limits.get('supplemental_Expert_triplets')==256 and limits.get('total_bundled_Experts')==676 and
         limits.get('inference_extra_kernel_pages')==0 and limits.get('loading_and_context_predicates_unchanged')is True and
         limits.get('OS_minimum_preserved')is True and limits.get('OS_counter_writes')==0 and type(limits.get('decode_only_GDN'))is bool,
         'Measured byte placement and explicit OS-preserving fixed inference policy required')
    for key,value in dict(active_expert_slots=3072,physical_cache_planes=3073,expert_cache_bytes=4720619520,
        postload_quota_transfer_bytes=3207049216,postload_device_budget_bytes=5086097408,postload_single_buffer_bytes=1677721600,
        workspace_reservation_bytes=50331648,CPU_heap_limit_bytes=536870912,physical_Direct_reserve_bytes=536870912,prefill_tokens=32).items():
        need(installation.get(key)==value,'Qualified physical geometry changed: '+key)
    need(context.get('active_cache_slots')==3072 and context.get('prefill_tokens')==32 and
         all(installation.get(k)is True and context.get(k)is True for k in('retain_Expert_weights_between_requests','parallel_small_rows'))and
         installation.get('request_and_KV_state_retained')is False and context.get('request_and_KV_state_retained')is False,
         'Weight retention, independent KV/request resets and small-row delivery required')
    comparison=report.get('limit_comparison',{})
    need(comparison.get('case')==13000 and comparison.get('completed')is True and comparison.get('requests')==16 and
         comparison.get('placement_eligible')is True and comparison.get('stable_inference_padding_pages')==0 and
         comparison.get('ordinary_close_exact_restore')is True and comparison.get('source_model_GPU_owners_positively_retired')is True and
         (not limits['decode_only_GDN']or comparison.get('decode_GDN_eligible')is True),
         'Actual restored stable-policy comparison and any selected GPU whole-time winner required')
    normal=report.get('normal',{})
    need(normal.get('case')==installation.get('normal_validation_case')==context.get('normal_performance_case')==13100 and
         normal.get('completed')is True and normal.get('POSTs')==3 and normal.get('actual_native_frames_viewed')==2 and
         all(normal.get(k)is True for k in('all_full_vocabulary_rows_finite','all_counting_tokens_and_bytes_equal','complete_actual_routes_verified',
             'retained_weights_and_empty_request_memory_verified','source_model_GPU_owners_positively_retired','ordinary_close_exact_restore')),
         'Complete normal/API/display and owner retirement required')
    for key,cap in(('CPU_heap_peak_bytes',536870912),('device_ledger_peak_bytes',5086097408),('actual_workspace_capacity_peak_bytes',50331648)):
        need(type(normal.get(key))is int and 0<normal[key]<=cap,'Actual allocation bound exceeded: '+key)
    probe=normal.get('limit_margin_probe',{})
    need(probe.get('OS_minimum_preserved')is True and probe.get('OS_counter_writes')==0 and
         probe.get('phases',[{},{},{}])[2].get('minimum_selected_padding_pages')==0 and
         probe['phases'][2].get('padding_reductions')==0,'Fixed zero inference padding must be measured in the actual normal program')
    for kind in('cold_start','request_reset_weights_retained','exact_prefix_repeat'):
        need(all(type(normal.get(kind,{}).get(k))in(int,float)and math.isfinite(normal[kind][k])and normal[kind][k]>0 for k in('total_ms','TTFT_ms','decode_tokens_per_second')),
             'Complete finite measured normal timing required')
    placed=report.get('placement',{})
    need(placed.get('completed')is True and placed.get('case')==installation.get('production_placement_case')==context.get('normal_performance_placement_case')==13200 and
         placed.get('normal_case')==13100 and placed.get('verification_files')==12 and placed.get('verified_programs')==2 and
         placed.get('verified_settings')==placed.get('verified_control_settings')==5 and
         all(placed.get(k)is True for k in('native_whole_SHA256_identity_EOF_verified','immediate_control_preserved','fresh_idle_confirmed','runtime_ownership_restored'))and
         all(placed.get(k)is False for k in('native_title_running','gateway_running','model_loaded')),
         'Exact current/rollback programs, both setting sets and fresh idle required')
    need(context.get('Expert_format')=='Gate_Up_Q2_K_Down_Q2_0_MSE'and context.get('PLE_convolution_weight_type')=='BF16'and
         context.get('remaining_resident_matrix_weight_type')=='Q8_0'and context.get('selected_routing_policy')==14 and
         context.get('graph_reuse_disabled_for_policy')is False and all(context.get(k)is False for k in('native_running','gateway_running','model_loaded')),
         'Qualified precision/routing and inactive final state required')
