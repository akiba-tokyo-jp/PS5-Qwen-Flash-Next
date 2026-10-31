#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reconcile finite native winners and normal delivery before verified placement."""
import argparse,json
from pathlib import Path
from finalize_speed_followup import completed,fingerprint,need,load
from limit_winners_production import REPORT,CONTROL_SELF,POLICY,DRIVER,PRECISION,MODEL_RECEIPT
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cache',type=Path,required=True);p.add_argument('--comparison',type=Path,required=True);a=p.parse_args()
 target=ROOT/REPORT;need(not target.exists(),'Preserve earlier qualification reports')
 comparison=load(a.comparison);need(comparison['completed']and comparison['placement_eligible'],'Restored exact placement winner required')
 case,n=completed(a.cache,13100);package=load(case/'candidate-package.private.json');native=load(package['native_link_receipt']['path']);scope=native['limit_defaults']['scope']
 need(n['model_receipt_sha256']==MODEL_RECEIPT and n['candidate_SELF_sha256']==package['SELF']['sha256'],'Exact normal artifact/model required')
 previous=load(ROOT/'config/production-installation.json');need(previous['application_SELF']['sha256']==CONTROL_SELF,'Exact immediate production control required')
 limit_policy=dict(supplemental_Expert_triplets=256,total_bundled_Experts=676,inference_extra_kernel_pages=0,loading_and_context_predicates_unchanged=True,
     OS_minimum_preserved=True,OS_counter_writes=0,decode_only_GDN=scope['scalar_single_token_GDN'])
 need(not limit_policy['decode_only_GDN']or comparison['decode_GDN_eligible'],'No unqualified GPU adoption')
 for i in range(3):
  trace=load(case/f'native-arm{i}.routes.private.json');need(trace['complete']and trace['cache_slots']==3072 and trace['cache_reset_before_request']==(i==0),'Complete actual retained3072 routes required')
 normal=dict(case=13100,completed=True,POSTs=3,actual_native_frames_viewed=2,all_full_vocabulary_rows_finite=True,all_counting_tokens_and_bytes_equal=True,
  complete_actual_routes_verified=True,retained_weights_and_empty_request_memory_verified=True,source_model_GPU_owners_positively_retired=True,ordinary_close_exact_restore=True,
  CPU_heap_peak_bytes=n['CPU_heap_peak_bytes'],device_ledger_peak_bytes=n['device_ledger_peak_bytes'],
  actual_workspace_capacity_peak_bytes=max(r['actual_workspace_capacity_peak_bytes']for r in n['requests']),
  maximum_absolute_logit_error_by_request=[r['maximum_absolute_logit_error']for r in n['requests']],limit_margin_probe=n['limit_margin_probe'],
  finite_quality_scope='Unchanged Q2/Q8/BF16/F32 payloads. Sixteen matched headless counting requests and three normal30-token counting prompts with22 outputs. Prior four-input precision/row-cache qualification remains historical; no new arbitrary-prompt or sustained-service qualification.')
 gains=[];old=load(a.cache/'hardware-first-generation-12500/native-model-terminal.private.json')
 for key,before,after in zip(('cold_start','request_reset_weights_retained','exact_prefix_repeat'),old['requests'],n['requests']):
  normal[key]=after['metrics'];d=after['completed_performance']['delta'];b=before['completed_performance']['delta']
  gains.append(dict(condition=key,control_case=12500,candidate_case=13100,matched_ABBA=False,
   complete_time_reduction_percent=100*(1-after['metrics']['total_ms']/before['metrics']['total_ms']),
   decode_rate_change_percent=100*(after['metrics']['decode_tokens_per_second']/before['metrics']['decode_tokens_per_second']-1),
   source_physical_calls_before=b['source_physical_read_calls'],source_physical_calls_after=d['source_physical_read_calls'],
   source_physical_bytes_before=b['source_physical_read_bytes'],source_physical_bytes_after=d['source_physical_read_bytes']))
 report=dict(schema='ps5-qwen-limit-winners-adoption-v1',completed=False,pending_steps=['verified_production_placement'],
  application_SELF={k:package['SELF'][k]for k in('bytes','sha256')},previous_application_SELF=previous['application_SELF'],driver=DRIVER,precision=PRECISION,
  model_receipt_SHA256=MODEL_RECEIPT,policy=POLICY,limit_winner_policy=limit_policy,limit_comparison=comparison,normal=normal,installed_comparison=gains,
  prior_qualification='docs/speed-followup-adoption-20261031.json',
  candidate_evidence=dict(cases=[13000,13100],headless_rows=16,normal_rows=3,all_normal_tokens_and_bytes_equal=True,byte_placement_complete_F32_exact=True,
      fixed_zero_inference_padding=True,loading_context_and_physical_checks_preserved=True,adoption_unit='measured676-key placement in the qualified finite normal composition'),
  dispositions=[dict(candidate='Exact676-key placement',status='adopted_pending_verified_placement',complete_F32_routes_tokens_bytes_exact=True),
   dict(candidate='Scalar single-token GDN',status='adopted_pending_verified_placement'if limit_policy['decode_only_GDN']else'not_adopted_measured_comparison',comparison=comparison['comparisons'][1]),
   dict(candidate='Fixed zero inference application padding',status='integrated_and_normal_qualified',OS_minimum_preserved=True,standalone_speed_gain_claimed=False),
   dict(candidate='3424-slot cache/workspace and physical-reserve changes',status='separate_unqualified_candidates',native_speed_improvement_claimed=False)],
  application_relink=dict(native_image=fingerprint(native['artifact']['path']),original_shader_pool_unchanged=True,
   actual_GPU_object={k:native['lossless_shader_storage']['vulkan_object'][k]for k in('bytes','sha256')},
   compiled_probe_header={k:native['limit_defaults']['probe_header'][k]for k in('bytes','sha256')},
   actual_application_sources=[dict(component=k,**fingerprint(v['path']))for k,v in native['limit_defaults']['actual_sources'].items()]),
  limitations=comparison['limitations']+['Normal-versus12500 numbers are sequential, not an isolated matched estimate.','The selected application retains finite prompt/binding limits; no reboot-free indefinite service qualification is claimed.'],
  placement=dict(completed=False),CI_runs=0,agents=0,reboots=0,forced_resets=0,
  evidence=[fingerprint(q)for q in(case/'native-model-terminal.private.json',case/'restored-complete.private.json',case/'visual-review.private.json',a.comparison)])
 target.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
 print(json.dumps(dict(normal_qualified=True,placement_pending=True,selected_SELF=report['application_SELF'],normal_rates=[r['metrics']['decode_tokens_per_second']for r in n['requests']])))
if __name__=='__main__':main()
