# SPDX-License-Identifier: MIT
"""Admit only the measured, normal-qualified Strata follow-up installation."""
import math
from speed_followup_production import DRIVER,MODEL_RECEIPT,PRECISION,POLICY
from limit_winners_production import SELECTED_SELF as CONTROL_SELF
REPORT='docs/strata-followup-adoption-20261031.json'
SELECTED_SELF='1247c365144f9226ee5d62973256faf49f4aab7579b8493c4d26b7e8a9451eb3'
SELECTED_BYTES=20133559
SOURCE_REVISION='36a44bb1008895430d562e5904232a60efb284fa'

def require_strata_followup_production(installation,context,report):
 def need(value,message):
  if not value:raise ValueError(message)
 need(report.get('schema')=='ps5-qwen-strata-followup-adoption-v1'and report.get('completed')is True and report.get('pending_steps')==[],
  'Complete matched comparisons, normal qualification and placement required')
 need(report.get('application_SELF')==installation.get('application_SELF')==dict(bytes=SELECTED_BYTES,sha256=SELECTED_SELF)and context.get('production_SELF',{}).get('sha256')==SELECTED_SELF,
  'Exact normal-qualified Strata program required')
 need(report.get('previous_application_SELF',{}).get('sha256')==installation.get('previous_production_SHA256')==CONTROL_SELF and context.get('previous_production_SELF',{}).get('sha256')==CONTROL_SELF,
  'Immediate exactA537 control must be preserved')
 need(report.get('application_source_revision')==installation.get('application_source_revision')==SOURCE_REVISION,
  'Actual clean normal relink revision required, independently of later metadata commits')
 need(report.get('driver')==installation.get('driver')==DRIVER and report.get('precision')==installation.get('precision')==PRECISION and
  report.get('model_receipt_SHA256')==installation.get('model_receipt_SHA256')==context.get('selected_model_receipt_SHA256')==MODEL_RECEIPT,
  'Pinned cumulative-idle driver, exact unchanged model and precision required')
 need(report.get('policy')==installation.get('speed_followup_policy')==context.get('speed_followup_policy')==POLICY,
  'Original finite prompt, routing/protection, source-worker and six-attempt policy required')
 for k,v in dict(active_expert_slots=3072,physical_cache_planes=3073,expert_cache_bytes=4720619520,
  postload_quota_transfer_bytes=3207049216,postload_device_budget_bytes=5086097408,postload_single_buffer_bytes=1677721600,
  workspace_reservation_bytes=50331648,CPU_heap_limit_bytes=536870912,physical_Direct_reserve_bytes=536870912,prefill_tokens=32).items():
  need(installation.get(k)==v,'Original qualified geometry/reserve changed: '+k)
 scope=report.get('strata_followup_policy',{})
 need(scope==installation.get('strata_followup_policy')==context.get('strata_followup_policy')and scope.get('schema')=='ps5-qwen-strata-followup-normal-v1'and
  scope.get('active_cache_slots')==3072 and scope.get('physical_cache_planes')==3073 and scope.get('checkpoint_pool_capacity_quantum_bytes')==2097152 and
  scope.get('checkpoint_maximum_bytes')==142606336 and scope.get('maximum_requests')==3 and scope.get('benchmark_checkpoint_injections')==0 and
  scope.get('persistent_caches')is False and scope.get('automatic_retries')==0 and all(scope.get(k)is True for k in(
   'checkpoint_metadata_arena_reuse','independent_same_operation_copy_batch','convolution_SiLU_QK_RMS_scale_fusion','fusion_single_token_F32_only',
   'independent_single_token_QK_normalizations_before_head_repeats','Vulkan_fusion_span_and_external_input_allocation_dependencies',
   'original_PLE_BF16_and_all_model_payloads','original_driver_physical_OS_minimum_workspace_and_completion','unknown_owner_retention')),
  'Exactly the three measured winners and original3072 normal limits required')
 candidates=report.get('candidates',{})
 need(candidates.get('candidate_comparisons_completed')is True and all(candidates.get(k)is True for k in('checkpoint_pool_eligible','checkpoint_batch_eligible','GDN_eligible','GDN_candidate_exercised'))and
  candidates.get('GDN_case')==16800 and report.get('cache3424_disposition')=='not_selected_for_decode_regression',
  'Actual exercised matched winners and explicit larger-cache tradeoff required')
 normal=report.get('normal',{})
 need(normal.get('case')==installation.get('normal_validation_case')==context.get('normal_performance_case')==17000 and normal.get('completed')is True and
  normal.get('requests')==3 and normal.get('POSTs')==3 and normal.get('actual_native_frames_viewed')==2 and
  all(normal.get(k)is True for k in('all_full_vocabulary_rows_finite','all_counting_tokens_and_bytes_equal','complete_actual_routes_verified',
   'retained_weights_and_empty_request_memory_verified','source_model_GPU_owners_positively_retired','ordinary_close_exact_restore')),
  'Actual normal/API/display/full finite coverage, close and restoration required')
 counters=normal.get('checkpoint_pool_stats',[])
 need(len(counters)==5 and counters[0]>0 and counters[2]>0 and counters[3]>0 and normal.get('GDN_pipeline_selections',0)>0 and normal.get('additional_shaders_verified')==1,
  'Both checkpoint winners and SHA-admitted fused shader must execute in the normal app')
 for k,cap in(('CPU_heap_peak_bytes',536870912),('device_ledger_peak_bytes',5086097408),('actual_workspace_capacity_peak_bytes',50331648)):
  need(type(normal.get(k))is int and 0<normal[k]<=cap,'Normal application allocation bound exceeded: '+k)
 probe=normal.get('limit_margin_probe',{})
 need(probe.get('OS_minimum_preserved')is True and probe.get('OS_counter_writes')==0 and probe.get('phases',[{},{},{}])[2].get('minimum_selected_padding_pages')==0,
  'Original OS watermark and measured zero inference padding required')
 for kind in('cold_start','request_reset_weights_retained','exact_prefix_repeat'):
  need(all(type(normal.get(kind,{}).get(k))in(int,float)and math.isfinite(normal[kind][k])and normal[kind][k]>0 for k in('total_ms','TTFT_ms','decode_tokens_per_second')),
   'Complete finite actual normal timing required')
 placed=report.get('placement',{})
 need(placed.get('completed')is True and placed.get('case')==installation.get('production_placement_case')==context.get('normal_performance_placement_case')==17100 and
  placed.get('normal_case')==17000 and placed.get('verification_files')==12 and placed.get('verified_programs')==2 and
  placed.get('verified_settings')==placed.get('verified_control_settings')==5 and placed.get('title_launches')==placed.get('GPU_calls')==0 and
  all(placed.get(k)is True for k in('native_whole_SHA256_identity_EOF_verified','immediate_control_preserved','fresh_idle_confirmed','runtime_ownership_restored')),
  'Native whole current/rollback program/settings identity/SHA256/EOF and fresh idle required')
 need(context.get('active_cache_slots')==3072 and context.get('selected_routing_policy')==14 and context.get('request_and_KV_state_retained')is False and
  all(context.get(k)is True for k in('retain_Expert_weights_between_requests','parallel_small_rows'))and
  all(context.get(k)is False for k in('native_running','gateway_running','model_loaded'))and context.get('native_owners')==0,
  'Original routing/weight retention, empty request memory and inactive final ownership required')
