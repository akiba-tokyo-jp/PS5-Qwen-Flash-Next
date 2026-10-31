#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Prepare adoption evidence from completed native cases; never deploy or launch."""
import argparse,json,hashlib
from pathlib import Path
from speed_followup_production import REPORT,SELECTED_SELF,CONTROL_SELF,POLICY,DRIVER,PRECISION,MODEL_RECEIPT
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def need(v,m):
 if not v:raise ValueError(m)
def fingerprint(p):
 p=Path(p);return dict(label=p.name,bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
def completed(cache,number):
 case=cache/f'hardware-first-generation-{number}';n=load(case/'native-model-terminal.private.json');closed=load(case/'restored-complete.private.json');observer=load(case/'passive-observer/complete.private.json')
 need(n['completed']and n['all_model_source_device_owners_positively_retired']and not n['device_ledger_live_bytes']and closed['completed']and not closed['unknown_completion']and observer['completed']and observer['POSTs']==3,'Complete positive normal cohort and exact restoration required')
 need(load(case/'visual-review.private.json')['actual_native_frames_viewed']==2,'Both actual native frames must have been viewed')
 need(all(r['full_F32_finite']and r['counting_quality_passed']and r['token_ids']==n['requests'][0]['token_ids']and r['output_bytes']==n['requests'][0]['output_bytes']for r in n['requests']),'Every complete finite counting output must match')
 return case,n
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cache',type=Path,required=True);p.add_argument('--out',type=Path,default=ROOT/REPORT);a=p.parse_args();need(not a.out.exists(),'Preserve previous reports')
 control_case,control=completed(a.cache,12460);case,n=completed(a.cache,12500);_,previous=completed(a.cache,12220)
 need(n['candidate_SELF_sha256']==SELECTED_SELF and previous['candidate_SELF_sha256']==CONTROL_SELF and n['model_receipt_sha256']==MODEL_RECEIPT,'Exact selected/current program and complete model required')
 packages=[load(q/'candidate-package.private.json')for q in(control_case,case)];native=[load(Path(q['native_link_receipt']['path']))for q in packages]
 need(native[0]['speed_normal']['scope']['maximum_speculative_attempts']==8 and native[1]['speed_normal']['scope']['maximum_speculative_attempts']==6 and
      native[0]['speed_normal']['source_provider']==native[1]['speed_normal']['source_provider']and native[0]['linked_driver']==native[1]['linked_driver'],'Matched native providers and exact budget delta required')
 for i in(0,1):
  need(load(control_case/f'native-arm{i}.routes.private.json')['records']==load(case/f'native-arm{i}.routes.private.json')['records'],'Ordinary routes must be identical across attempt-budget variants')
 for number,root in((12460,control_case),(12500,case)):
  for i in range(3):
   trace=load(root/f'native-arm{i}.routes.private.json');need(trace['cache_slots']==3072 and trace['cache_reset_before_request']==(i==0),'New route metadata must reflect actual3072-slot retained geometry')
 tail=lambda r:r['metrics']['total_ms']-r['metrics']['TTFT_ms']-r['metrics']['decode_ms']
 a8,a6=control['requests'][2],n['requests'][2]
 need(a8['speculation']['accepted']==a6['speculation']['accepted']==6 and a8['speculation']['rejected']==1 and a6['speculation']['rejected']==0,'Exactly the unproductive seventh verification must be removed')
 budget=dict(control_case=12460,candidate_case=12500,attempt_caps=[8,6],same_model_driver_and_providers=True,all_counting_tokens_and_bytes_equal=True,both_cases_closed_and_restored=True,
  complete_request_time_reduction_percent=100*(1-a6['metrics']['total_ms']/a8['metrics']['total_ms']),completion_tail_reduction_ms=tail(a8)-tail(a6),control_tail_ms=tail(a8),candidate_tail_ms=tail(a6),
  physical_calls_saved=a8['completed_performance']['delta']['source_physical_read_calls']-a6['completed_performance']['delta']['source_physical_read_calls'],
  physical_bytes_saved=a8['completed_performance']['delta']['source_physical_read_bytes']-a6['completed_performance']['delta']['source_physical_read_bytes'],matched_ABBA=False)
 need(budget['complete_request_time_reduction_percent']>0 and budget['completion_tail_reduction_ms']>0,'Positive complete-request and targeted-tail gain required')
 headless=load(ROOT/'docs/speed-followup-headless-corrected-20261031.json');need(headless['completed']and headless['contents_correct']==16,'Completed corrected headless comparisons required')
 normal=dict(case=12500,completed=True,POSTs=3,actual_native_frames_viewed=2,all_full_vocabulary_rows_finite=True,all_counting_tokens_and_bytes_equal=True,complete_actual_routes_verified=True,
  retained_weights_and_empty_request_memory_verified=True,source_model_GPU_owners_positively_retired=True,ordinary_close_exact_restore=True,
  CPU_heap_peak_bytes=n['CPU_heap_peak_bytes'],device_ledger_peak_bytes=n['device_ledger_peak_bytes'],actual_workspace_capacity_peak_bytes=max(r['actual_workspace_capacity_peak_bytes']for r in n['requests']),
  maximum_absolute_logit_error_by_request=[r['maximum_absolute_logit_error']for r in n['requests']],
  finite_quality_scope='Four fixed headless tasks; normal application is three identical compiled30-token counting prompts with22 generated tokens. Complete finite vocabulary; unlike-cache or unlike-width F32 equality is not claimed.')
 gains=[]
 for key,old,new in zip(('cold_start','request_reset_weights_retained','exact_prefix_repeat'),previous['requests'],n['requests']):
  normal[key]=new['metrics'];d=new['completed_performance']['delta'];old_d=old['completed_performance']['delta']
  gains.append(dict(condition=key,current_case=12220,candidate_case=12500,generated_tokens=22,
   complete_time_reduction_percent=100*(1-new['metrics']['total_ms']/old['metrics']['total_ms']),decode_rate_change_percent=100*(new['metrics']['decode_tokens_per_second']/old['metrics']['decode_tokens_per_second']-1),
   source_physical_calls_before=old_d['source_physical_read_calls'],source_physical_calls_after=d['source_physical_read_calls'],source_physical_bytes_before=old_d['source_physical_read_bytes'],source_physical_bytes_after=d['source_physical_read_bytes'],
   source_wait_ms_before=old_d['source_read_ns']/1e6,source_wait_ms_after=d['source_read_ns']/1e6,source_wait_fraction_of_total=d['source_read_ns']/1e6/new['metrics']['total_ms']))
 profile=native[1]['speed_normal']['scope'];need(profile['owned_rows']and profile['prefill_decode_protection'],'Exact composed normal candidate required')
 report=dict(schema='ps5-qwen-speed-followup-adoption-v1',completed=False,pending_steps=['verified_production_placement'],all_current_candidate_dispositions_completed=True,
  application_SELF=packages[1]['SELF']|{},previous_application_SELF=load(ROOT/'config/production-installation-weight-followup-20261031.json')['application_SELF'],
  driver=DRIVER,precision=PRECISION,model_receipt_SHA256=MODEL_RECEIPT,policy=POLICY,normal=normal,causal_budget_comparison=budget,
  headless={k:headless[k]for k in('completed','case','requests','contents_correct','matched_row_cache_full_F32_SHA256_routes_tokens_bytes_exact','original_weight_payloads_and_reserves_unchanged','ordinary_close_exact_restore','comparisons')},
  candidate_evidence=dict(cases=[12360,12420,12460,12500],headless_rows=16,normal_rows=6,all_normal_tokens_and_bytes_equal=True,
   original_weights_driver_and_reserves_unchanged=True,changed_JSON_output_length_disclosed=True,
   protection_arbitrary_prompt_speedup_qualified=False,row_cache_standalone_2_percent_target_met=False,adoption_unit='measured compiled-identical-prompt normal composition'),
  installed_comparison=gains,application_relink=dict(native_build='Speed-normal-12402',SELF_build='Speed-normal-SELF-12406',native_receipt=fingerprint(Path(packages[1]['native_link_receipt']['path'])),package_receipt=fingerprint(case/'candidate-package.private.json'),
   exact_native_sources={k:{x:v[x]for x in('bytes','sha256')}for k,v in native[1]['resident_weight_normal']['actual_sources'].items()},selected_driver_revision=DRIVER['revision'],selected_profile=DRIVER['profile'],
   linked_driver=dict(native_archive_SHA256=native[1]['linked_driver']['archive_sha256'],native_platform_manifest_SHA256=native[1]['linked_driver']['manifest_sha256'],
    shared_profile_archive_SHA256=native[1]['driver']['archive_sha256'],shared_profile_manifest_SHA256=native[1]['driver']['profile_manifest_sha256'],
    native_adapter_source_inputs=[dict(path=Path(v['path']).relative_to(ROOT).as_posix(),bytes=v['bytes'],sha256=v['sha256'])for v in native[1]['linked_driver']['source_inputs']])),
  dispositions=[dict(candidate='S1 recent decode protection',status='adopted_in_fixed_identical_prompt_composition_only',arbitrary_prompt_speedup_proven=False,changed_JSON_output_length_disclosed=True),
   dict(candidate='S2 owned immutable BF16 rows',status='adopted_in_measured_composition',standalone_reverse_gain_percent=headless['comparisons']['row_cache_reverse_time_reduction_percent'],independent_2_percent_claim=False,exact_full_F32_routes_tokens_bytes=True),
   dict(candidate='S3 cap6 completion budget',status='adopted',matched_budget_comparison=budget),dict(candidate='S4 selected four-lane diagnostics',status='implemented_and_measured',raw_SSD_or_pure_GPU_latency_claimed=False)],
  host_checks=dict(actual_reader_bytes_leases_reset_and_canaries=True,short_read_consumer_admission_failure_drain=True,aligned_BF16_storage_bytes=525344,
   native_control_replays_exact=True,protected_fallback_and_4096_boundary=True,actual3072_slot_aging_trace_observations=13200,native_sustained_aging_qualification_claimed=False,
   VM_sample_capacity_bound_to_request_count=True,corrected16_request_case_completed=True),
  limitations=headless['limitations']+['Normal gains against12220 are sequential observations, not matched ABBA.','The8/6 budget comparison is one matched finite pair, with both ordinary controls and all output bytes equal.','The selected program is a finite fixed-prompt application, not a sustained arbitrary-prompt service.'],
  placement=dict(completed=False),CI_runs=0,agents=0,reboots=0,
  evidence=[fingerprint(q)for root in(control_case,case)for q in(root/'native-model-terminal.private.json',root/'restored-complete.private.json',root/'visual-review.private.json')])
 report['application_SELF']={k:report['application_SELF'][k]for k in('bytes','sha256')}
 a.out.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n');print(json.dumps(dict(native_qualification_complete=True,placement_pending=True,budget=budget,installed_comparison=gains)))
if __name__=='__main__':main()
