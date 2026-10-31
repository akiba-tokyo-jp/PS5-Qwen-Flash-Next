# SPDX-License-Identifier: MIT
"""Admit only the measured next-five normal program and verified placement."""
import json,math
from pathlib import Path
from four_next_production import DRIVER,POLICY,PRECISION as PREVIOUS_PRECISION,SELECTED_SELF as CONTROL_SELF
ROOT=Path(__file__).resolve().parents[1]
REPORT='docs/next-five-adoption-20261031.json'
MODEL_RECEIPT='5f991ad0e335993fd2c0d2e97d1d8925e8e95adda013f2549ea923cefd679ec9'
PRECISION=dict(PREVIOUS_PRECISION,other_weights='108 large resident matrices Q4_0; other resident Q8_0 except original BF16 PLE convolution and F32 tensors',quantization='Expert Q2 and mixed resident Q4_0/Q8_0')
selection_path=ROOT/'config/next-five-selection.json'
SELECTION=json.loads(selection_path.read_text())if selection_path.exists()else{}
SELECTED_SELF=SELECTION.get('SELF',{}).get('sha256');SELECTED_BYTES=SELECTION.get('SELF',{}).get('bytes');SOURCE_REVISION=SELECTION.get('source_revision');NORMAL_CASE=SELECTION.get('normal_case');PLACEMENT_CASE=SELECTION.get('placement_case')

def require_next_five_production(installation,context,report):
 def need(ok,message):
  if not ok:raise ValueError(message)
 need(SELECTION and report.get('schema')=='ps5-qwen-next-five-adoption-v1'and report.get('completed')and report.get('pending_steps')==[],'Complete measured next-five selection required')
 expected=SELECTION['SELF'];scope=SELECTION['normal_scope']
 need(expected==report.get('application_SELF')==installation.get('application_SELF')and context.get('production_SELF',{}).get('sha256')==SELECTED_SELF and context['production_SELF']['bytes']==SELECTED_BYTES,'Exact selected native SELF required')
 need(report.get('application_source_revision')==installation.get('application_source_revision')==SOURCE_REVISION,'Exact application relink revision required')
 need(report.get('driver')==installation.get('driver')==DRIVER and report.get('precision')==installation.get('precision')==PRECISION,'Pinned driver and precise mixed resident format required')
 need(report.get('model_receipt_SHA256')==installation.get('model_receipt_SHA256')==context.get('selected_model_receipt_SHA256')==MODEL_RECEIPT,'Native-sealed Q4 model receipt required')
 need(scope['decode_Experts']==2 and scope['active_cache_slots']==3712 and scope['physical_cache_planes']==3713 and scope['cache_bytes']==5703659520 and scope['Attention_KV']==scope['recurrent_S']=='F32'and scope['PLE_convolution']=='BF16','Measured routing, geometry and retained state precision required')
 need(report.get('previous_application_SELF',{}).get('sha256')==installation.get('previous_production_SHA256')==context.get('previous_production_SELF',{}).get('sha256')==CONTROL_SELF and installation.get('previous_production_rollback_preserved')is True,'Immediate exact c2e control must remain preserved')
 need(installation.get('active_expert_slots')==context.get('active_cache_slots')==3712 and installation.get('physical_cache_planes')==3713 and installation.get('expert_cache_bytes')==5703659520 and installation.get('total_bundled_Experts')==scope['placement_keys'],'Actual selected cache and placement required')
 need(report.get('next_five_policy')==scope and report.get('application_relink',{}).get('original_GPU_object_SHA256')=='17cb982ec26903fcee469639592d5acd761acd6f883bc35135b9d665fc4b6ad2','Exact normal contract and original single-token GPU provider required')
 normal=report.get('normal',{})
 if scope.get('expanded_placement_only_first_request'):
  need(scope.get('expanded_placement_prefill_only')and scope.get('decode_placement_keys')==scope.get('later_request_placement_keys')==768 and normal.get('large_bundle_high_index_hits_total',0)>0 and normal.get('large_bundle_high_index_decode_hits_total')==0,'Actual initial-prefill large indices and unchanged decode/later placement required')
 need(installation.get('postload_device_budget_bytes')==6199160832 and installation.get('postload_single_buffer_bytes')==2147483648,'Exact measured Q4 allocation limits required')
 need(normal.get('completed')and normal.get('case')==NORMAL_CASE and normal.get('requests')==normal.get('POSTs')==3 and normal.get('actual_native_frames_viewed')==2,'Three actual API requests and two viewed native frames required')
 for key in ('all_full_vocabulary_rows_finite','all_counting_tokens_and_bytes_equal','complete_actual_routes_verified','retained_weights_and_empty_request_memory_verified','source_model_GPU_owners_positively_retired','ordinary_close_exact_restore'):
  need(normal.get(key)is True,'Normal qualification missing: '+key)
 for key,maximum in(('CPU_heap_peak_bytes',536870912),('device_ledger_peak_bytes',6199160832),('actual_workspace_capacity_peak_bytes',50331648)):
  need(type(normal.get(key))is int and 0<normal[key]<=maximum,'Measured normal allocation exceeded: '+key)
 probe=normal.get('limit_margin_probe',{});need(probe.get('OS_minimum_preserved')and probe.get('OS_counter_writes')==0 and probe['phases'][0]['minimum_selected_padding_pages']==256 and probe['phases'][0]['minimum_free_pages']>=1154 and probe['phases'][2]['minimum_selected_padding_pages']==0,'Original measured loading and inference admission required')
 need(normal.get('complete_captures_elided')==normal.get('actual_causal_attempts')and normal.get('all_memory_rollbacks')==normal.get('actual_rejections')and 0<normal['actual_causal_attempts']<=6,'Actual normal capture elision and rejection accounting required')
 need(normal.get('GDN_pipeline_selections',0)>0 and normal.get('additional_shaders_verified')==1 and normal['checkpoint_pool_stats'][2]>0 and normal['checkpoint_pool_stats'][3]>0,'Original fused shader and prefix batch must execute')
 for kind in('cold_start','request_reset_weights_retained','exact_prefix_repeat'):
  need(all(isinstance(normal.get(kind,{}).get(k),(int,float))and math.isfinite(normal[kind][k])and normal[kind][k]>0 for k in('total_ms','TTFT_ms','decode_tokens_per_second')),'Actual finite normal timing required')
 placed=report.get('placement',{})
 need(placed.get('completed')and placed.get('case')==installation.get('production_placement_case')==context.get('normal_performance_placement_case')==PLACEMENT_CASE and placed.get('normal_case')==NORMAL_CASE and placed.get('verification_files')==12 and placed.get('verified_programs')==2 and placed.get('verified_settings')==placed.get('verified_control_settings')==5 and placed.get('title_launches')==placed.get('GPU_calls')==0,'Whole selected/control program and both five-setting sets required')
 need(all(placed.get(k)is True for k in('native_whole_SHA256_identity_EOF_verified','immediate_control_preserved','fresh_idle_confirmed','runtime_ownership_restored')),'Positive placement and ownership evidence required')
 need(all(context.get(k)is False for k in('native_running','gateway_running','model_loaded','request_and_KV_state_retained'))and context.get('native_owners')==0 and context.get('retain_Expert_weights_between_requests')and context.get('parallel_small_rows'),'Fresh inactive normal owners and independent request state required')
