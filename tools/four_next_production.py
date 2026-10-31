# SPDX-License-Identifier: MIT
"""Admit only the normal-qualified placement and native rollback composition."""
import math
from strata_followup_production import DRIVER,MODEL_RECEIPT,PRECISION,POLICY,SELECTED_SELF as CONTROL_SELF
REPORT='docs/four-next-adoption-20261031.json'
SELECTED_SELF='5920b19e54532391bd99ad8100da5f29f40375e90a23010effa2203969a26783'
SELECTED_BYTES=20140343
SOURCE_REVISION='b9893a8d6bbee05efb64091f02600e10920f3473'
NORMAL_CASE=18200
PLACEMENT_CASE=18300

def require_four_next_production(installation,context,report):
 def need(value,message):
  if not value:raise ValueError(message)
 need(report.get('schema')=='ps5-qwen-four-next-adoption-v1'and report.get('completed')is True and report.get('pending_steps')==[],
      'All four dispositions, normal qualification and exact placement required')
 need(report.get('application_SELF')==installation.get('application_SELF')==dict(bytes=SELECTED_BYTES,sha256=SELECTED_SELF)and
      context.get('production_SELF',{}).get('sha256')==SELECTED_SELF,'Exact qualified normal composition required')
 need(report.get('previous_application_SELF',{}).get('sha256')==installation.get('previous_production_SHA256')==CONTROL_SELF and
      context.get('previous_production_SELF',{}).get('sha256')==CONTROL_SELF,'Immediate exact1247 rollback must be preserved')
 need(report.get('application_source_revision')==installation.get('application_source_revision')==SOURCE_REVISION,'Actual clean native relink revision required')
 need(report.get('driver')==installation.get('driver')==DRIVER and report.get('precision')==installation.get('precision')==PRECISION and
      report.get('model_receipt_SHA256')==installation.get('model_receipt_SHA256')==context.get('selected_model_receipt_SHA256')==MODEL_RECEIPT,
      'Unchanged pinned driver, encoded weights and BF16 PLE required')
 need(report.get('policy')==installation.get('speed_followup_policy')==context.get('speed_followup_policy')==POLICY,
      'Original routing, protection, source workers and six-attempt policy required')
 for key,value in dict(active_expert_slots=3072,physical_cache_planes=3073,expert_cache_bytes=4720619520,
  postload_quota_transfer_bytes=3207049216,postload_device_budget_bytes=5216120832,postload_single_buffer_bytes=1677721600,
  additional_application_state_allowance_bytes=130023424,workspace_reservation_bytes=50331648,CPU_heap_limit_bytes=536870912,
  physical_Direct_reserve_bytes=536870912,prefill_tokens=32).items():need(installation.get(key)==value,'Qualified geometry/reserve changed: '+key)
 scope=report.get('four_next_policy',{})
 need(scope==installation.get('four_next_policy')==context.get('four_next_policy')and scope.get('schema')=='ps5-qwen-four-next-normal-v1'and
      all(scope.get(k)==v for k,v in dict(maximum_requests=3,active_cache_slots=3072,physical_cache_planes=3073,cache_bytes=4720619520,
       supplemental_triplets=348,total_placement_keys=768,n_rs_seq=1,additional_application_state_allowance_bytes=130023424,
       postload_device_budget_bytes=5216120832,postload_single_buffer_bytes=1677721600,checkpoint_maximum_bytes=142606336,
       maximum_causal_attempts=6,benchmark_checkpoint_injections=0,automatic_retries=0).items())and
      all(scope.get(k)is True for k in('original_GPU_object','original_single_token_GDN_fusion','complete_speculative_capture_elision',
       'original_physical_Direct_Flexible_OS_minimum_workspace_and_completion','checkpoint_pool_and_batch_policy_preserved','original_model_and_PLE_BF16'))and
      all(scope.get(k)is False for k in('two_token_fusion_selected','Gate_Up_fusion_selected','persistent_caches')),
      'Only measured placement and native rollback winners with explicitly priced recurrent state required')
 candidates=report.get('candidates',{})
 need(candidates.get('candidate_comparisons_completed')is True and candidates.get('placement',{}).get('eligible')is True and
      candidates.get('rollback',{}).get('eligible')is True and candidates.get('two_token',{}).get('eligible')is False and
      candidates.get('gate_up',{}).get('kernel_eligible')is False,'All four actual measured dispositions required')
 need(candidates['rollback'].get('complete_captures_elided')==35 and candidates['rollback'].get('all_memory_rollbacks')==15,
      'Actual complete-memory forced-rejection continuations required')
 normal=report.get('normal',{})
 need(normal.get('case')==installation.get('normal_validation_case')==context.get('normal_performance_case')==NORMAL_CASE and
      normal.get('completed')is True and normal.get('requests')==normal.get('POSTs')==3 and normal.get('actual_native_frames_viewed')==2 and
      all(normal.get(k)is True for k in('all_full_vocabulary_rows_finite','all_counting_tokens_and_bytes_equal','complete_actual_routes_verified',
       'retained_weights_and_empty_request_memory_verified','source_model_GPU_owners_positively_retired','ordinary_close_exact_restore')),
      'Actual three-request API/display qualification with positive retirement required')
 need(normal.get('complete_captures_elided')==normal.get('actual_causal_attempts')==6 and normal.get('all_memory_rollbacks')==normal.get('actual_rejections')==0,
      'Actual six normal attempts must avoid pre-verification captures; forced rejects are covered by matched17600')
 stats=normal.get('checkpoint_pool_stats',[])
 need(len(stats)==5 and stats[2]>0 and stats[3]>0 and normal.get('GDN_pipeline_selections',0)>0 and normal.get('additional_shaders_verified')==1,
      'Original prefix checkpoint batch and single-token shader must execute; speculative pool-hit counts need not survive elision')
 for key,cap in(('CPU_heap_peak_bytes',536870912),('device_ledger_peak_bytes',5216120832),('actual_workspace_capacity_peak_bytes',50331648)):
  need(type(normal.get(key))is int and 0<normal[key]<=cap,'Measured normal application allocation bound exceeded: '+key)
 probe=normal.get('limit_margin_probe',{})
 need(probe.get('OS_minimum_preserved')is True and probe.get('OS_counter_writes')==0 and probe.get('phases',[{},{},{}])[2].get('minimum_selected_padding_pages')==0,
      'Original OS watermark and measured zero inference padding required')
 for kind in('cold_start','request_reset_weights_retained','exact_prefix_repeat'):
  need(all(type(normal.get(kind,{}).get(k))in(int,float)and math.isfinite(normal[kind][k])and normal[kind][k]>0 for k in('total_ms','TTFT_ms','decode_tokens_per_second')),
       'Complete finite actual normal timing required')
 placed=report.get('placement',{})
 need(placed.get('completed')is True and placed.get('case')==installation.get('production_placement_case')==context.get('normal_performance_placement_case')==PLACEMENT_CASE and
      placed.get('normal_case')==NORMAL_CASE and placed.get('verification_files')==12 and placed.get('verified_programs')==2 and
      placed.get('verified_settings')==placed.get('verified_control_settings')==5 and placed.get('title_launches')==placed.get('GPU_calls')==0 and
      all(placed.get(k)is True for k in('native_whole_SHA256_identity_EOF_verified','immediate_control_preserved','fresh_idle_confirmed','runtime_ownership_restored')),
      'Native current/rollback whole SHA256, identity, EOF and fresh inactive ownership required')
 need(context.get('active_cache_slots')==3072 and context.get('selected_routing_policy')==14 and context.get('request_and_KV_state_retained')is False and
      all(context.get(k)is True for k in('retain_Expert_weights_between_requests','parallel_small_rows'))and
      all(context.get(k)is False for k in('native_running','gateway_running','model_loaded'))and context.get('native_owners')==0,
      'Original policy, retained weights, empty request memory and inactive final ownership required')
