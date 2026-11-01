# SPDX-License-Identifier: MIT
"""Admit the new qualified composition without weakening its historical control."""
import json,math
from pathlib import Path
from frontier_production import DRIVER,POLICY,PRECISION as PREVIOUS_PRECISION,SELECTED_SELF as CONTROL_SELF
ROOT=Path(__file__).resolve().parents[1]
REPORT='docs/throughput-adoption-20261101.json'
path=ROOT/'config/throughput-selection.json'
SELECTION=json.loads(path.read_text())if path.is_file()else{}
SELECTED_SELF=SELECTION.get('SELF',{}).get('sha256');SELECTED_BYTES=SELECTION.get('SELF',{}).get('bytes')
SOURCE_REVISION=SELECTION.get('source_revision');NORMAL_CASE=SELECTION.get('normal_case');PLACEMENT_CASE=SELECTION.get('placement_case')
MODEL_RECEIPT='46ceb693e8afd3c562e92532674ff16a336387da4cea91609660cc1fc58fe426'
PRECISION=dict(PREVIOUS_PRECISION,output_weight='Q4_0',other_weights='109 large resident matrices including output Q4_0; other resident Q8_0 except original BF16 PLE convolution and F32 tensors')
IDS={'T1','T2','T3','T4'}
def require_throughput_production(installation,context,report):
 def need(v,msg):
  if not v:raise ValueError(msg)
 need(SELECTION and report.get('schema')=='ps5-qwen-throughput-adoption-v1'and report.get('completed')and report.get('pending_steps')==[],'Complete current campaign selection required')
 scope=SELECTION['normal_scope'];expected=SELECTION['SELF'];normal=report.get('normal',{});placement=report.get('placement',{})
 need(expected==report.get('application_SELF')==installation.get('application_SELF')and context.get('production_SELF',{}).get('sha256')==SELECTED_SELF and context['production_SELF']['bytes']==SELECTED_BYTES,'Exact new program required')
 need(report.get('application_source_revision')==installation.get('application_source_revision')==SOURCE_REVISION,'Exact clean implementation relink revision required')
 need(report.get('driver')==installation.get('driver')==DRIVER and report.get('precision')==installation.get('precision')==PRECISION,'Exact driver and109-matrix/output precision required')
 need(SELECTION.get('model_receipt_SHA256')==report.get('model_receipt_SHA256')==installation.get('model_receipt_SHA256')==context.get('selected_model_receipt_SHA256')==MODEL_RECEIPT,'Native-sealed output-Q4 receipt required')
 need(scope.get('serialized_almost_ready_tail_disabled')is True and scope.get('nested_CPU_measurement_enabled')is True and scope.get('GPU_timestamp_diagnostics_enabled')is False,'Qualified tail change and CPU attribution, with no diagnostic GPU queries, required')
 need(report.get('next_five_policy')==scope and scope['decode_Experts']==2 and scope['submission_node_cap']==256 and scope['submission_flop_divisor']==40 and scope['output_weight_type']=='Q4_0','Exact qualified execution composition required')
 need(installation.get('next_five_policy')==context.get('next_five_policy')==scope,'Installed and runtime policy metadata must match the compiled scope')
 need(installation.get('active_expert_slots')==context.get('active_cache_slots')==3712 and installation.get('physical_cache_planes')==context.get('physical_cache_planes')==3713 and installation.get('expert_cache_bytes')==context.get('expert_cache_bytes')==5703659520,'Installed/runtime cache geometry must match actual qualification')
 need(installation.get('CPU_heap_limit_bytes')==536870912 and installation.get('postload_device_budget_bytes')==context.get('postload_device_budget_bytes')==6199160832 and installation.get('postload_single_buffer_bytes')==context.get('postload_single_buffer_bytes')==2147483648,'Qualified actual allocation budgets required')
 need(scope['active_cache_slots']==3712 and scope['physical_cache_planes']==3713 and scope['cache_bytes']==5703659520 and scope['Attention_KV']==scope['recurrent_S']=='F32'and scope['PLE_convolution']=='BF16','Exact cache and recurrent precision required')
 gpu=scope['selected_GPU_object_SHA256'];need(len(gpu)==64 and gpu==report.get('application_relink',{}).get('GPU_object_SHA256')and scope['original_GPU_object']is False,'Actual changed GPU provider must be recorded')
 need(report.get('previous_application_SELF',{}).get('sha256')==installation.get('previous_production_SHA256')==context.get('previous_production_SELF',{}).get('sha256')==CONTROL_SELF and installation.get('previous_production_rollback_preserved')is True,'Immediate exact1a76 control must be preserved')
 need(normal.get('completed')and normal.get('case')==NORMAL_CASE and normal.get('requests')==normal.get('POSTs')==3 and normal.get('actual_native_frames_viewed')==2,'Three measured generations, two actual generation API streams, finish POST and two viewed native frames required')
 need(normal.get('local_cold_self_tests')==normal.get('finish_POSTs')==1 and normal.get('generation_POSTs')==2,'Measured local and external request scopes must be explicit')
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
 p1=report.get('matched_tail_comparison',{});need(p1.get('completed')and p1.get('all_full_F32_routes_tokens_exact')and min(p1.get('paired_whole_time_savings_ms',[0]))>p1.get('AA_spread_ms',float('inf')),'Repeated exact whole-time tail improvement required')
 cpu=normal.get('CPU_nested_by_request',[]);need(len(cpu)==3,'All actual normal CPU timing rows required')
 for ordinal,row in enumerate(cpu):
  need(len(row)==42 and row[39]==1 and all(row[k*3]>0 for k in(0,1,2,3,4,5,6,7,8,9,11)),'Actual normal lifecycle/sampling/validation/persistence measurements required')
  need((row[30]==0 if ordinal==0 else row[30]>0),'Local cold self-test and two actual API publication paths must match the measured scope')
  need(sum(row[k*3+2]for k in range(14))==row[40],'Exclusive CPU caller wall must fully reconcile with the enclosing request span')
 p3=report.get('GPU_range_validation',{});need(p3.get('completed')and p3.get('full_F32_routes_tokens_exact')and p3.get('query_pools_created')==p3.get('query_pools_destroyed')==1 and p3.get('pending_ranges')==0 and p3.get('measured_ranges',0)>0 and p3.get('no_new_queue_wait')is True,'Positive complete GPU diagnostic and query-owner retirement required')
 need(scope.get('service_overhead_mode',0)&1 and scope.get('per_token_fsync_preserved')is True and scope.get('token_record_format')=='bounded_per_request_JSONL','Qualified per-token durable ledger required')
 need(normal.get('service_modes')==[scope['service_overhead_mode']]*3 and normal.get('ledger_readback_complete')is True and normal.get('ledger_readback_count')==3,'All three actual normal ledgers and execution modes must match')
 if scope['service_overhead_mode']&4:need(normal.get('completion_generation_reuses',0)>0,'Selected completion cache must execute in the actual normal application')
 if scope['service_overhead_mode']&16:need(normal.get('HC_no_split_selections',0)>0,'Selected HC kernel path must execute')
 if scope['service_overhead_mode']&64:need(normal.get('HC_split_two_selections',0)>0,'Selected HC parallel split path must execute')
 if scope['service_overhead_mode']&32:need(normal.get('Q4_large_workgroup_selections',0)>0,'Selected Q4 kernel path must execute')
 if not scope['service_overhead_mode']&32:need(normal.get('Q4_large_workgroup_selections')==0,'Unselected Q4 kernel must remain inactive')
 if not scope['service_overhead_mode']&16:need(normal.get('HC_no_split_selections')==0,'Unselected HC no-split policy must remain inactive')
 mode=scope.get('frontier_mode',0);need(mode&3==3 and mode&12 in (4,8),'Qualified owner/HC and one selected split mode required')
 need(normal.get('frontier_modes')==[mode]*3,'All normal requests must execute the exact selected frontier mode')
 need(normal.get('owner_checkpoint_generation_reuses',0)>0 and normal.get('HC_joined_projection_selections',0)>0,'Both selected generation/HC paths must actually execute')
 actual=normal.get('service_GPU_totals_by_request',[]);need(len(actual)==3 and all(len(r)==8 for r in actual),'Actual complete GPU policy counters required')
 selected_K=8 if mode&8 else 4;need(scope.get('HC_prefill_split_K')==selected_K,'Exact selected shape-specific HC split required')
 need(all(r[3]-r[2]==(selected_K-1)*r[6] for r in actual)and actual[-1][6]>0,'Actual GPU split count/sums must prove the selected factor')
 need((normal.get('command_cache_hits',0)>0 if mode&16 else normal.get('command_cache_hits',0)==0),'Recorded command selection must match actual execution')
 evidence=report.get('throughput_verification',{});need(evidence.get('completed')and evidence.get('stages')==4 and evidence.get('selected_semantic_tasks_passed')is True,'Complete ordered throughput verification required')
 rows=report.get('dispositions',[]);need(len(rows)==4 and {x['id']for x in rows}==IDS and all(x.get('verification_stage_completed')is True and not x.get('remaining_current_plan_steps')for x in rows),'All four throughput stages must be explicitly disposed')
 need(placement.get('completed')and placement.get('case')==installation.get('production_placement_case')==context.get('normal_performance_placement_case')==PLACEMENT_CASE and placement.get('normal_case')==NORMAL_CASE and placement.get('verification_files')==12 and placement.get('verified_programs')==2 and placement.get('verified_settings')==placement.get('verified_control_settings')==5,'Whole current/immediate-control program and settings required')
 need(all(placement.get(k)is True for k in('native_whole_SHA256_identity_EOF_verified','immediate_control_preserved','fresh_idle_confirmed','runtime_ownership_restored')),'Positive native placement and idle ownership proof required')
 need(all(context.get(k)is False for k in('native_running','gateway_running','model_loaded','request_and_KV_state_retained'))and context.get('native_owners')==0,'No live native/model ownership may remain after verification')

 # Counters must prove that each selected mechanism ran in the actual normal app.
 mode=scope.get('throughput_mode',0)
 need(type(mode)is int and 0<mode<16,'A measured nonempty throughput selection required')
 need(normal.get('throughput_modes')==[mode]*3,'Exact compiled throughput selection must execute in all requests')
 counters=normal.get('throughput_totals_by_request',[])
 need(len(counters)==3 and all(len(r)==12 for r in counters),'All twelve actual throughput counters required')
 final=counters[-1]
 for bit,index,name in ((1,0,'full Expert bundles'),(2,5,'GDN shared input'),(4,8,'empty retirement certificate'),(8,11,'WAR synchronization')):
  need((final[index]>0 if mode&bit else final[index]==0),'Actual selected/excluded path differs: '+name)
 need(scope.get('per_token_fsync_preserved')is True and scope.get('pending_unpublished_writes_preserved')is True,'Durability and cross-batch visibility must remain')
 if mode&1:
  bundle=report.get('sealed_bundle_coverage',{})
  need(bundle.get('completed')is True and bundle.get('active_Experts')==scope.get('immutable_Expert_bundle_coverage')==22968 and bundle.get('parts')==66 and bundle.get('bytes')==22968*1540096 and bundle.get('original_bits_preserved')is True and scope.get('uncovered_original_reads_preserved')is True,'Exact immutable Expert coverage and original fallback required')
 if mode&8:
  fixture=report.get('synchronization_fixture',{})
  need(fixture.get('completed')is True and fixture.get('graphs')==60 and fixture.get('scenarios')==4 and fixture.get('cross_submission_without_intermediate_host_read')is True and fixture.get('all_full_outputs_and_canaries_exact')is True,'Complete separate-submission synchronization oracle required')
  need(type(normal.get('throughput_sync_tail_flushes'))is int and normal['throughput_sync_tail_flushes']>=0 and fixture.get('actual_cross_submission_publications',0)>0,'Actual cross-batch publication must be observed in the separate-submission oracle')
 if mode&4:
  owner=next(row for row in rows if row['id']=='T3')
  checks=report.get('owner_certificate_mutation_controls',{})
  need(owner.get('original_control_operation_order_preserved')is True and owner.get('extra_control_owner_snapshots')==0,'Ownership selection must use the original control operation order')
  need(checks.get('completed')is True and checks.get('checks')==22,'Allocation, retirement, ABA, fault and owner mutation controls required')
 selected={row['id'] for row in rows if row.get('selected')is True}
 integration=report.get('current_provider_integration',{})
 need(integration.get('completed')is True and integration.get('actual_installed_normal_providers_preserved')is True and integration.get('real_current_seal_and_index_exports_preserved')is True,'Actual installed normal provider integration must be qualified')
 need(integration.get('full_F32_routes_tokens_exact')is True and integration.get('fixed_semantic_tasks_passed')is True and min(integration.get('paired_whole_time_savings_ms',[0]))>integration.get('AA_spread_ms',float('inf')),'Actual installed-provider composition must show exact repeated whole-request improvement')
 need(selected=={'T'+str(i+1)for i in range(4)if mode&(1<<i)},'Disposed selected rows and compiled feature mask differ')
 for row in rows:
  if row.get('selected')is True:
   proof=row.get('matched_comparison',{})
   need(proof.get('completed')is True and proof.get('fixed_semantic_tasks_passed')is True and proof.get('independent_full_F32_routes_exact')is True,'Selected stage lacks full native correctness and quality evidence')
   if row['id']!='T2':need(proof.get('cross_control_full_F32_routes_exact')is True,'Layout, owner and synchronization changes require exact cross-control F32 and routes')
   need(min(proof.get('paired_whole_time_savings_ms',[0]))>proof.get('AA_spread_ms',float('inf')),'Selected stage lacks repeated whole-request improvement beyond A/A spread')
