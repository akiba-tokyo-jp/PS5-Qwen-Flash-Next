#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Bind closed native winners, final normal frames and the exact placement input."""
import argparse,json
from pathlib import Path
from finalize_speed_followup import completed,fingerprint,need,load
from strata_followup_production import REPORT,CONTROL_SELF,SELECTED_SELF,SELECTED_BYTES,SOURCE_REVISION,POLICY,DRIVER,PRECISION,MODEL_RECEIPT
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cache',type=Path,required=True);p.add_argument('--comparison',type=Path,required=True);p.add_argument('--normal-case',type=int,required=True);a=p.parse_args()
 target=ROOT/REPORT;need(not target.exists(),'Preserve prior final reports');candidates=load(a.comparison)
 need(candidates['candidate_comparisons_completed']and all(candidates[k]for k in('checkpoint_pool_eligible','checkpoint_batch_eligible','GDN_eligible','GDN_candidate_exercised')),'Closed measured actual-model winners required')
 case,n=completed(a.cache,a.normal_case);package=load(case/'candidate-package.private.json');native=load(package['native_link_receipt']['path']);strata=n['strata_followup'];scope=native['strata_followup_normal']['scope']
 need(n['candidate_SELF_sha256']==SELECTED_SELF==package['SELF']['sha256']and package['SELF']['bytes']==SELECTED_BYTES and n['model_receipt_sha256']==MODEL_RECEIPT,'Exact final normal program/model required')
 need(native['strata_followup_normal']['source_revision']==SOURCE_REVISION and strata['scope']==scope and strata['checkpoint_pool_stats'][0]>0 and strata['checkpoint_pool_stats'][2]>0 and strata['GDN_pipeline_selections']>0 and strata['additional_shaders_verified']==1,'Actual normal winner execution and relink provenance required')
 previous=load(ROOT/'config/production-installation.json');need(previous['application_SELF']['sha256']==CONTROL_SELF,'Exact immediate production control required')
 archive=ROOT/'config/production-installation-limit-winners-20261031.json'
 if not archive.exists():archive.write_bytes((ROOT/'config/production-installation.json').read_bytes())
 need(load(archive)==previous,'Preserve exact prior installation')
 for i in range(3):
  r=load(case/f'native-arm{i}.routes.private.json');need(r['complete']and r['cache_slots']==3072 and r['cache_reset_before_request']==(i==0),'Complete actual3072 route evidence required')
 normal=dict(case=a.normal_case,completed=True,requests=3,POSTs=3,actual_native_frames_viewed=2,
  all_full_vocabulary_rows_finite=True,all_counting_tokens_and_bytes_equal=True,complete_actual_routes_verified=True,
  retained_weights_and_empty_request_memory_verified=True,source_model_GPU_owners_positively_retired=True,ordinary_close_exact_restore=True,
  CPU_heap_peak_bytes=n['CPU_heap_peak_bytes'],device_ledger_peak_bytes=n['device_ledger_peak_bytes'],actual_workspace_capacity_peak_bytes=n['actual_workspace_capacity_peak_bytes'],
  maximum_absolute_logit_error_by_request=[r['maximum_absolute_logit_error']for r in n['requests']],limit_margin_probe=n['limit_margin_probe'],
  checkpoint_pool_stats=strata['checkpoint_pool_stats'],GDN_pipeline_selections=strata['GDN_pipeline_selections'],GDN_planner_stats=strata['GDN_planner_stats'],additional_shaders_verified=strata['additional_shaders_verified'],
  finite_quality_scope='Four fixed semantic tasks; complete F64 recurrent state/history/weights/snapshot/canary oracle; exact complete F32/routes/tokens for checkpoint-only changes. Normal delivery is three identical30-token prompts with22 generated tokens. Unlike-cache/arithmetic/width bit equality and arbitrary-prompt/sustained-service quality are not claimed.')
 old=load(a.cache/'hardware-first-generation-13100/native-model-terminal.private.json');gains=[]
 for kind,before,after in zip(('cold_start','request_reset_weights_retained','exact_prefix_repeat'),old['requests'],n['requests']):
  normal[kind]=after['metrics'];gains.append(dict(condition=kind,control_case=13100,candidate_case=a.normal_case,matched_ABBA=False,
   complete_time_reduction_percent=100*(1-after['metrics']['total_ms']/before['metrics']['total_ms']),
   decode_rate_change_percent=100*(after['metrics']['decode_tokens_per_second']/before['metrics']['decode_tokens_per_second']-1)))
 report=dict(schema='ps5-qwen-strata-followup-adoption-v1',completed=False,pending_steps=['verified_production_placement'],
  application_SELF=dict(bytes=SELECTED_BYTES,sha256=SELECTED_SELF),application_source_revision=SOURCE_REVISION,previous_application_SELF=previous['application_SELF'],
  driver=DRIVER,precision=PRECISION,model_receipt_SHA256=MODEL_RECEIPT,policy=POLICY,limit_winner_policy=previous['limit_winner_policy'],strata_followup_policy=scope,
  candidates=candidates,candidate_evidence=candidates,cache3424_disposition='not_selected_for_decode_regression',normal=normal,installed_comparison=gains,
  dispositions=[dict(candidate='3424-slot cache',status='implemented_tested_not_selected',reason='Retained TTFT/whole time improve; retained decode regresses3.46%, so production preserves3072'),
   *[dict(candidate=v,status='adopted_pending_verified_placement')for v in('2MiB checkpoint capacity/metadata reuse','Independent same-operation Vulkan checkpoint copy batching','Single-token F32 convolution/SiLU/QK RMS-scale fusion with planner lifetimes')]],
  application_relink=dict(source_revision=SOURCE_REVISION,native_image=fingerprint(native['artifact']['path']),actual_GPU_object={k:native['lossless_shader_storage']['vulkan_object'][k]for k in('bytes','sha256')},original_shader_pool_unchanged=True,additional_SHA256_admitted_shader_count=1),
  prior_qualification='docs/limit-winners-adoption-20261031.json',placement=dict(completed=False),
  limitations=['Matched16800 GPU decode improvement is1.17% retained and1.74% cold; routing/I/O may change, so it is not a pure-GPU isolation.',
   'Checkpoint-injected15400 throughput is not ordinary model speed.','Normal-versus13100 results are sequential, not matched A-B-B-A.','Finite first-generation binding is consumed after normal close; no reboot-free indefinite service qualification is claimed.'],
  evidence=[fingerprint(q)for q in(case/'native-model-terminal.private.json',case/'restored-complete.private.json',case/'visual-review.private.json',case/'passive-observer/complete.private.json',a.comparison)],CI_runs=0,agents=0,reboots=0,forced_resets=0)
 target.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8',newline='\n');print(json.dumps(dict(normal_qualified=True,placement_pending=True,source_revision=SOURCE_REVISION,selected_SELF=report['application_SELF'],normal_rates=[r['metrics']['decode_tokens_per_second']for r in n['requests']])))
if __name__=='__main__':main()
