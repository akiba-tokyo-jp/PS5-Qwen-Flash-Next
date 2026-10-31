#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Record actual normal/API/display qualification before verified placement."""
import argparse,json,math
from pathlib import Path
from expert_q4 import record,require
from next_five_production import REPORT,DRIVER,PRECISION,MODEL_RECEIPT,CONTROL_SELF
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(Path(p).read_text())
def fingerprint(p):return{k:v for k,v in record(p).items()if k!='path'}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cache',type=Path,required=True);p.add_argument('--case',type=int,required=True);p.add_argument('--placement-case',type=int,required=True);p.add_argument('--native',type=Path,required=True);a=p.parse_args()
 c=a.cache/f'hardware-first-generation-{a.case}';n=load(c/'native-model-terminal.private.json');closed=load(c/'restored-complete.private.json');observer=load(c/'passive-observer/complete.private.json');visual=load(c/'visual-review.private.json');native=load(a.native);scope=native['next_five_normal']['scope'];package=load(c/'candidate-package.private.json')
 require(n['completed']and closed['completed']and not closed['unknown_completion']and observer['completed']and observer['POSTs']==3 and visual['actual_native_frames_viewed']==2,'Actual complete normal/API/viewed frame cohort required')
 require(n['next_five']==scope and n['model_receipt_sha256']==MODEL_RECEIPT and n['candidate_SELF_sha256']==package['SELF']['sha256'],'Exact compiled normal scope, SELF and model required')
 require(n['all_model_source_device_owners_positively_retired']and n['device_ledger_live_bytes']==0 and n['final_prefix_handoff_consumed'],'Positive full source/model/GPU retirement required')
 rows=n['requests'];require(len(rows)==3 and all(x['full_F32_finite']and type(x['counting_quality_passed'])is bool and x['request_reset_completed']for x in rows),'Finite actual complete output and explicit unaltered quality results required')
 require(rows[1]['token_ids']==rows[0]['token_ids']and rows[1]['output_bytes']==rows[0]['output_bytes'],'Independent retained same-model tokens and bytes must agree')
 for i in (1,2):
  streamed=load(c/'passive-observer'/f'request-{i}.positive.private.json')['events'][:-1];require(rows[i]['token_ids']==[x['token_id']for x in streamed]and rows[i]['output_bytes']==[b for x in streamed for b in x['piece_bytes']],'Each actual API stream must match its own native result')
 for i in range(3):
  r=load(c/f'native-arm{i}.routes.private.json');require(r['complete']and r['cache_slots']==scope['active_cache_slots']and r['cache_reset_before_request']==(i==0),'Complete actual selected-capacity routes required')
  counts={x['experts']for x in r['records']};require(2 in counts and counts<={2,6}and all(x['experts']==6 for x in r['records']if x['tokens']>2),'Actual two-Expert decode and unchanged six-Expert large prefill required')
 prior=load(ROOT/'config/production-installation.json');require(prior['application_SELF']['sha256']==CONTROL_SELF,'Immediate c2e control required')
 archive=ROOT/'config/production-installation-four-next-20261031.json'
 if not archive.exists():archive.write_bytes((ROOT/'config/production-installation.json').read_bytes())
 require(load(archive)==prior,'Preserve exact preceding installation')
 attempts=sum(x['speculation']['attempts']for x in rows);rejects=sum(x['speculation']['rejected']for x in rows);four=n['four_next'];s=n['strata_followup'];require(four['complete_captures_elided']==attempts and four['all_memory_rollbacks']==rejects,'Actual compact accounting required')
 normal=dict(case=a.case,completed=True,requests=3,POSTs=3,actual_native_frames_viewed=2,all_full_vocabulary_rows_finite=True,all_counting_tokens_and_bytes_equal=all(x['token_ids']==rows[0]['token_ids']and x['output_bytes']==rows[0]['output_bytes']for x in rows),counting_quality_by_request=[x['counting_quality_passed']for x in rows],all_actual_API_streams_match_native_results=True,quality_loss_reported_separately=True,complete_actual_routes_verified=True,retained_weights_and_empty_request_memory_verified=True,source_model_GPU_owners_positively_retired=True,ordinary_close_exact_restore=True,
  CPU_heap_peak_bytes=n['CPU_heap_peak_bytes'],device_ledger_peak_bytes=n['device_ledger_peak_bytes'],actual_workspace_capacity_peak_bytes=n['actual_workspace_capacity_peak_bytes'],maximum_absolute_logit_error_by_request=[x['maximum_absolute_logit_error']for x in rows],limit_margin_probe=n['limit_margin_probe'],checkpoint_pool_stats=s['checkpoint_pool_stats'],GDN_pipeline_selections=s['GDN_pipeline_selections'],additional_shaders_verified=s['additional_shaders_verified'],complete_captures_elided=four['complete_captures_elided'],all_memory_rollbacks=four['all_memory_rollbacks'],actual_causal_attempts=attempts,actual_rejections=rejects,
  finite_quality_scope='Four fixed semantic tasks pass in complete routing/Q4 cohorts. Normal/API counting correctness and cross-prefix answer changes are reported per request without rewriting output or quarantining returned GPU work. General quality, arbitrary-prompt performance and sustained reboot-free operation are not claimed.')
 if scope.get('expanded_placement_only_first_request'):
  normal.update(large_bundle_high_index_hits_total=n['large_bundle_high_index_hits_total'],large_bundle_high_index_decode_hits_total=n['large_bundle_high_index_decode_hits_total'])
  require(normal['large_bundle_high_index_hits_total']>0 and normal['large_bundle_high_index_decode_hits_total']==0,'Actual cold-prefill-only upper-half source use required')
 old=load(a.cache/'hardware-first-generation-19000/native-model-terminal.private.json');comparisons=[]
 for kind,before,after in zip(('cold_start','request_reset_weights_retained','exact_prefix_repeat'),old['requests'],rows):
  normal[kind]=after['metrics'];comparisons.append(dict(condition=kind,control_case=19000,candidate_case=a.case,matched_ABBA=False,precision_and_decode_Expert_count_changed=True,whole_time_reduction_percent=100*(1-after['metrics']['total_ms']/before['metrics']['total_ms']),decode_change_percent=100*(after['metrics']['decode_tokens_per_second']/before['metrics']['decode_tokens_per_second']-1)))
 selection=dict(schema='ps5-qwen-next-five-selection-v1',SELF={k:package['SELF'][k]for k in('bytes','sha256')},source_revision=native['next_five_normal']['source_revision'],normal_scope=scope,normal_case=a.case,placement_case=a.placement_case)
 (ROOT/'config/next-five-selection.json').write_text(json.dumps(selection,indent=2)+'\n',newline='\n')
 worklog=load(ROOT/'docs/next-five-worklog-20261031.json');report=dict(schema='ps5-qwen-next-five-adoption-v1',completed=False,pending_steps=['verified_production_placement'],application_SELF=selection['SELF'],application_source_revision=selection['source_revision'],previous_application_SELF=prior['application_SELF'],driver=DRIVER,precision=PRECISION,model_receipt_SHA256=MODEL_RECEIPT,next_five_policy=scope,four_next_policy=native['four_next_normal']['scope'],strata_followup_policy=native['strata_followup_normal']['scope'],limit_winner_policy=native['limit_defaults']['scope'],normal=normal,installed_comparison=comparisons,candidate_evidence=worklog['results'],dispositions=worklog['results'],placement=dict(completed=False),
  application_relink=dict(source_revision=selection['source_revision'],image=fingerprint(native['artifact']['path']),original_GPU_object_SHA256=native['lossless_shader_storage']['vulkan_object']['sha256'],actual_sources={k:{x:v[x]for x in('bytes','sha256')}for k,v in native['next_five_normal']['actual_sources'].items()}),
  evidence=[fingerprint(x)for x in(c/'native-model-terminal.private.json',c/'restored-complete.private.json',c/'visual-review.private.json',c/'passive-observer/complete.private.json')],limitations=['Normal19000 and this final normal cohort are sequential, not ABBA; prompt/output/reuse conditions are reported separately.','108 resident matrices change Q8_0 to Q4_0 and decode changes Top6 to Top2; finite task passes do not establish unchanged general model quality.','Failed and CPU-refused attempts remain in the worklog; current-prototype execution failure is not evidence of physical impossibility.','No CI, learned host inference, reboot, forced reset, persistent shader cache or persistent pipeline cache was used.'],CI_runs=0,agents=0,reboots=0,forced_resets=0)
 (ROOT/REPORT).write_text(json.dumps(report,indent=2)+'\n',newline='\n');print(json.dumps(dict(normal_qualified=True,placement_pending=True,source_revision=selection['source_revision'],rates=[x['metrics']['decode_tokens_per_second']for x in rows])))
if __name__=='__main__':main()
