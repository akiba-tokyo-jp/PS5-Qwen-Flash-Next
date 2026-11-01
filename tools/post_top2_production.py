# SPDX-License-Identifier: MIT
"""Admit the new qualified composition without weakening its historical control."""
import json,math
from pathlib import Path
from next_five_production import DRIVER,POLICY,PRECISION as PREVIOUS_PRECISION,SELECTED_SELF as CONTROL_SELF
ROOT=Path(__file__).resolve().parents[1]
REPORT='docs/post-top2-adoption-20261101.json'
path=ROOT/'config/post-top2-selection.json'
SELECTION=json.loads(path.read_text())if path.is_file()else{}
SELECTED_SELF=SELECTION.get('SELF',{}).get('sha256');SELECTED_BYTES=SELECTION.get('SELF',{}).get('bytes')
SOURCE_REVISION=SELECTION.get('source_revision');NORMAL_CASE=SELECTION.get('normal_case');PLACEMENT_CASE=SELECTION.get('placement_case')
MODEL_RECEIPT='46ceb693e8afd3c562e92532674ff16a336387da4cea91609660cc1fc58fe426'
PRECISION=dict(PREVIOUS_PRECISION,other_weights='109 large resident matrices including output Q4_0; other resident Q8_0 except original BF16 PLE convolution and F32 tensors')
IDS={f'N{i}'for i in range(1,6)}|{f'R{i}'for i in range(1,6)}|{f'C{i}'for i in range(1,5)}|{f'D{i}'for i in range(1,4)}
def require_post_top2_production(installation,context,report):
 def need(v,msg):
  if not v:raise ValueError(msg)
 need(SELECTION and report.get('schema')=='ps5-qwen-post-top2-adoption-v1'and report.get('completed')and report.get('pending_steps')==[],'Complete current campaign selection required')
 scope=SELECTION['normal_scope'];expected=SELECTION['SELF'];normal=report.get('normal',{});placement=report.get('placement',{})
 need(expected==report.get('application_SELF')==installation.get('application_SELF')and context.get('production_SELF',{}).get('sha256')==SELECTED_SELF and context['production_SELF']['bytes']==SELECTED_BYTES,'Exact new program required')
 need(report.get('application_source_revision')==installation.get('application_source_revision')==SOURCE_REVISION,'Exact clean implementation relink revision required')
 need(report.get('driver')==installation.get('driver')==DRIVER and report.get('precision')==installation.get('precision')==PRECISION,'Exact driver and109-matrix/output precision required')
 need(SELECTION.get('model_receipt_SHA256')==report.get('model_receipt_SHA256')==installation.get('model_receipt_SHA256')==context.get('selected_model_receipt_SHA256')==MODEL_RECEIPT,'Native-sealed output-Q4 receipt required')
 need(report.get('next_five_policy')==scope and scope['decode_Experts']==2 and scope['submission_node_cap']==256 and scope['submission_flop_divisor']==40 and scope['output_weight_type']=='Q4_0','Exact qualified execution composition required')
 need(scope['active_cache_slots']==3712 and scope['physical_cache_planes']==3713 and scope['cache_bytes']==5703659520 and scope['Attention_KV']==scope['recurrent_S']=='F32'and scope['PLE_convolution']=='BF16','Exact cache and recurrent precision required')
 gpu=scope['selected_GPU_object_SHA256'];need(len(gpu)==64 and gpu==report.get('application_relink',{}).get('GPU_object_SHA256')and scope['original_GPU_object']is False,'Actual changed GPU provider must be recorded')
 need(report.get('previous_application_SELF',{}).get('sha256')==installation.get('previous_production_SHA256')==context.get('previous_production_SELF',{}).get('sha256')==CONTROL_SELF and installation.get('previous_production_rollback_preserved')is True,'Immediate exact5b control must be preserved')
 need(normal.get('completed')and normal.get('case')==NORMAL_CASE and normal.get('requests')==normal.get('POSTs')==3 and normal.get('actual_native_frames_viewed')==2,'Three actual API responses and two viewed native frames required')
 for k in('all_full_vocabulary_rows_finite','all_actual_API_streams_match_native_results','quality_loss_reported_separately','complete_actual_routes_verified','retained_weights_and_empty_request_memory_verified','source_model_GPU_owners_positively_retired','ordinary_close_exact_restore'):
  need(normal.get(k)is True,'Normal qualification missing: '+k)
 need(len(normal.get('counting_quality_by_request',[]))==3 and all(type(x)is bool for x in normal['counting_quality_by_request']),'Actual approximate-answer quality required')
 for k,maximum in(('CPU_heap_peak_bytes',536870912),('device_ledger_peak_bytes',6199160832),('actual_workspace_capacity_peak_bytes',50331648)):
  need(type(normal.get(k))is int and 0<normal[k]<=maximum,'Actual allocation exceeds selected budget: '+k)
 counters=normal.get('post_top2_submission_counters',[]);need(len(counters)==22 and counters[1]>0 and 16<max(counters[12:14])<=256,'Actual larger submission batches must execute')
 need(normal.get('prior_native_pack_seals_reused',0)>0,'Fresh named-inode/EOF admission of the prior native seal must execute')
 probe=normal.get('limit_margin_probe',{});phases=probe.get('phases',[]);need(len(phases)==4 and probe.get('OS_minimum_preserved')and probe.get('OS_counter_writes')==0,'Original OS minimum and counter integrity required')
 load=phases[0];need(load.get('minimum_selected_padding_pages')==206 and load.get('minimum_free_pages',0)>=898 and phases[2]['minimum_selected_padding_pages']==0,'Qualified loading206 and unchanged inference admission required')
 need(normal.get('GDN_pipeline_selections',0)>0 and normal.get('additional_shaders_verified')==1 and normal.get('complete_captures_elided')==normal.get('actual_causal_attempts')and normal.get('all_memory_rollbacks')==normal.get('actual_rejections')and 0<normal['actual_causal_attempts']<=6,'Actual original GDN and complete rollback accounting required')
 for kind in('cold_start','request_reset_weights_retained','exact_prefix_repeat'):
  need(all(isinstance(normal.get(kind,{}).get(k),(int,float))and math.isfinite(normal[kind][k])and normal[kind][k]>0 for k in('total_ms','TTFT_ms','decode_tokens_per_second')),'Actual finite normal timings required')
 rows=report.get('dispositions',[]);need(len(rows)==17 and {x['id']for x in rows}==IDS and all(x.get('verification_stage_completed')is True and not x.get('remaining_current_plan_steps')for x in rows),'All17 planned candidate stages must be explicitly disposed')
 need(placement.get('completed')and placement.get('case')==installation.get('production_placement_case')==context.get('normal_performance_placement_case')==PLACEMENT_CASE and placement.get('normal_case')==NORMAL_CASE and placement.get('verification_files')==12 and placement.get('verified_programs')==2 and placement.get('verified_settings')==placement.get('verified_control_settings')==5,'Whole current/immediate-control program and settings required')
 need(all(placement.get(k)is True for k in('native_whole_SHA256_identity_EOF_verified','immediate_control_preserved','fresh_idle_confirmed','runtime_ownership_restored')),'Positive native placement and idle ownership proof required')
 need(all(context.get(k)is False for k in('native_running','gateway_running','model_loaded','request_and_KV_state_retained'))and context.get('native_owners')==0,'No live native/model ownership may remain after verification')
