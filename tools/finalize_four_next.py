#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Bind four native dispositions to the actual final normal/API/frame run."""
import argparse,json
from pathlib import Path
from finalize_speed_followup import completed,fingerprint,need,load
from expert_q4 import record
from four_next_production import REPORT,CONTROL_SELF,SELECTED_SELF,SELECTED_BYTES,SOURCE_REVISION,NORMAL_CASE,POLICY,DRIVER,PRECISION,MODEL_RECEIPT
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cache',type=Path,required=True);p.add_argument('--comparison',type=Path,required=True);a=p.parse_args()
 target=ROOT/REPORT;need(not target.exists(),'Preserve previous reports');candidates=load(a.comparison)
 need(candidates['candidate_comparisons_completed']and candidates['placement']['eligible']and candidates['rollback']['eligible']and
      not candidates['two_token']['eligible']and not candidates['gate_up']['kernel_eligible'],'All four measured candidate dispositions required')
 for item in candidates['source_evidence']:need(record(item['path'])==item,'Actual candidate evidence changed')
 case,n=completed(a.cache,NORMAL_CASE);package=load(case/'candidate-package.private.json');native=load(package['native_link_receipt']['path']);four=n['four_next'];strata=n['strata_followup'];scope=native['four_next_normal']['scope']
 need(n['candidate_SELF_sha256']==SELECTED_SELF==package['SELF']['sha256']and package['SELF']['bytes']==SELECTED_BYTES and n['model_receipt_sha256']==MODEL_RECEIPT,'Exact final native program/model required')
 need(native['four_next_normal']['source_revision']==SOURCE_REVISION and four['scope']==scope and four['complete_captures_elided']==6 and four['all_memory_rollbacks']==0,'Actual normal elision execution and relink provenance required')
 need(strata['checkpoint_pool_stats'][2]>0 and strata['checkpoint_pool_stats'][3]>0 and strata['GDN_pipeline_selections']>0 and strata['additional_shaders_verified']==1,'Original prefix copy batching and SHA-admitted single-token shader must execute')
 previous=load(ROOT/'config/production-installation.json');need(previous['application_SELF']['sha256']==CONTROL_SELF,'Immediate exact1247 control required')
 archive=ROOT/'config/production-installation-strata-followup-20261031.json'
 if not archive.exists():archive.write_bytes((ROOT/'config/production-installation.json').read_bytes())
 need(load(archive)==previous,'Preserve exact prior installation')
 for i in range(3):
  r=load(case/f'native-arm{i}.routes.private.json');need(r['complete']and r['cache_slots']==3072 and r['cache_reset_before_request']==(i==0),'Complete actual3072-slot routes required')
 spec=n['requests'][2]['speculation'];need(spec['attempts']==spec['accepted']==6 and spec['rejected']==0,'Actual unchanged six-attempt normal controller required')
 normal=dict(case=NORMAL_CASE,completed=True,requests=3,POSTs=3,actual_native_frames_viewed=2,
  all_full_vocabulary_rows_finite=True,all_counting_tokens_and_bytes_equal=True,complete_actual_routes_verified=True,
  retained_weights_and_empty_request_memory_verified=True,source_model_GPU_owners_positively_retired=True,ordinary_close_exact_restore=True,
  CPU_heap_peak_bytes=n['CPU_heap_peak_bytes'],device_ledger_peak_bytes=n['device_ledger_peak_bytes'],actual_workspace_capacity_peak_bytes=n['actual_workspace_capacity_peak_bytes'],
  maximum_absolute_logit_error_by_request=[r['maximum_absolute_logit_error']for r in n['requests']],limit_margin_probe=n['limit_margin_probe'],
  checkpoint_pool_stats=strata['checkpoint_pool_stats'],GDN_pipeline_selections=strata['GDN_pipeline_selections'],additional_shaders_verified=strata['additional_shaders_verified'],
  complete_captures_elided=four['complete_captures_elided'],all_memory_rollbacks=four['all_memory_rollbacks'],actual_causal_attempts=spec['attempts'],actual_rejections=spec['rejected'],
  finite_quality_scope='Placement and rollback: exact compared complete F32 rows/routes/tokens and four fixed semantic tasks. Two-token fusion:216 full-state F64 fixture graphs and14 full-model requests. Gate/Up prototype:108 graphs, three encoded Expert samples repeated across six selected IDs; no whole-model speed claim. Final normal:three identical30-token prompts/22 generated tokens, two viewed native frames. Arbitrary-prompt and sustained-service quality are not claimed.')
 old=load(a.cache/'hardware-first-generation-17000/native-model-terminal.private.json');gains=[]
 for kind,before,after in zip(('cold_start','request_reset_weights_retained','exact_prefix_repeat'),old['requests'],n['requests']):
  normal[kind]=after['metrics'];gains.append(dict(condition=kind,control_case=17000,candidate_case=NORMAL_CASE,matched_ABBA=False,
   complete_time_reduction_percent=100*(1-after['metrics']['total_ms']/before['metrics']['total_ms']),decode_rate_change_percent=100*(after['metrics']['decode_tokens_per_second']/before['metrics']['decode_tokens_per_second']-1)))
 public_candidates={k:v for k,v in candidates.items()if k not in('source_evidence','normal_qualification_pending','production_placement_pending')}
 report=dict(schema='ps5-qwen-four-next-adoption-v1',completed=False,pending_steps=['verified_production_placement'],
  application_SELF=dict(bytes=SELECTED_BYTES,sha256=SELECTED_SELF),application_source_revision=SOURCE_REVISION,previous_application_SELF=previous['application_SELF'],
  driver=DRIVER,precision=PRECISION,model_receipt_SHA256=MODEL_RECEIPT,policy=POLICY,limit_winner_policy=native['limit_defaults']['scope'],
  strata_followup_policy=native['strata_followup_normal']['scope'],four_next_policy=scope,candidates=public_candidates,candidate_evidence=public_candidates,
  normal=normal,installed_comparison=gains,placement=dict(completed=False),
  dispositions=[dict(candidate='768-key placement with348 supplemental triplets',status='adopted_pending_verified_placement'),
   dict(candidate='Two-token convolution/SiLU/QK RMS-scale fusion',status='implemented_tested_not_selected',reason='Retained decode gain0.697% does not exceed A/A spread and is not faster in both temporal directions'),
   dict(candidate='Native one-token all-memory rollback with complete pre-verification capture elision',status='adopted_pending_verified_placement'),
   dict(candidate='Q2 Gate/Up matmul and SwiGLU prototype',status='implemented_tested_not_selected',reason='Actual one/two-token backend-and-synchronization intervals regress26.80%/98.94%; no whole-model expansion justified')],
  application_relink=dict(source_revision=SOURCE_REVISION,native_image=fingerprint(native['artifact']['path']),original_GPU_object={k:native['lossless_shader_storage']['vulkan_object'][k]for k in('bytes','sha256')},
   additional_SHA256_admitted_shader_count=1,actual_sources={k:{x:v[x]for x in('bytes','sha256')}for k,v in native['four_next_normal']['actual_sources'].items()}),
  prior_qualification='docs/strata-followup-adoption-20261031.json',limitations=[
   'Placement arms use the same348-triplet physical file; control activates the original256 keys and candidate348. The common pack reorders existing entries, so it is not a literal old-file versus new-file test.',
   'Placement retained physical calls are4684 versus4388; bytes2968256768 versus2962276608 are whole30-input/22-output request totals, not decode bytes per token. Cold whole differences include opposite temporal signs.',
   'Rollback arms both allocate n_rs_seq1 under an explicit additional124MiB application-ledger allowance. Physical/OS reserves remain unchanged; complete-copy elimination does not eliminate recurrent state storage.',
   'Normal-versus17000 timing is sequential, not matched A/B/B/A. Individual improvements are not added to predict joint speed.',
   'Normal speculative pool reuse can be zero after capture elision; original prefix capture/restore batches remain exercised. No synthetic state work was added to raise counters.',
   'Normal18200 stopped during loading at1146 free pages versus its1154-page predicate and was ordinarily closed/restored. Ancillary18600 selected206-page loading padding but had2110 minimum free pages, so it did not prove admission below the old boundary. It stopped on an obsolete capture-count predicate after22 tokens in the final request and was ordinarily closed/restored. Final normal restores original256-page loading padding and reconciles the actual elision/rollback counters.',
   'Gate/Up numbers include backend dispatch and synchronization, not GPU timestamp-only kernel time; this rejects the tested prototype, not all future fusion designs.',
   'Finite launch binding is consumed; future launches require fresh cases. No indefinite reboot-free service claim.'],
  evidence=[fingerprint(q)for q in(case/'native-model-terminal.private.json',case/'restored-complete.private.json',case/'visual-review.private.json',case/'passive-observer/complete.private.json',a.comparison)],
  CI_runs=0,agents=0,reboots=0,forced_resets=0)
 target.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8',newline='\n');print(json.dumps(dict(normal_qualified=True,placement_pending=True,source_revision=SOURCE_REVISION,normal_rates=[r['metrics']['decode_tokens_per_second']for r in n['requests']])))
if __name__=='__main__':main()
