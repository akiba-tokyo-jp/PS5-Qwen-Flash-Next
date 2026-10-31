#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Grade closed native comparisons without pooling unlike cache/quality scopes."""
import argparse,hashlib,json,statistics as st
from pathlib import Path
from expert_q4 import require,write_json

def evidence(path):
 data=path.read_bytes();return dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cache',type=Path,required=True);p.add_argument('--GDN-case',type=int,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 proofs={}
 def closed(case):
  d=a.cache/f'hardware-first-generation-{case}';n=json.loads((d/'native-model-terminal.private.json').read_text());r=json.loads((d/'restored-complete.private.json').read_text())
  require(n['completed']and n['all_model_source_device_owners_positively_retired']and n['device_ledger_live_bytes']==0,'Positive native retirement required')
  require(r['completed']and not r['unknown_completion']and r['CPU_title_normally_closed']and r['full_native_readback_SHA256_identity_EOF_verified']and r['exact_prior_configuration_restored'],'Normal close and exact restoration required')
  proofs[str(case)]=dict(native=evidence(d/'native-model-terminal.private.json'),restore=evidence(d/'restored-complete.private.json'));return n,d
 def group(n,ids):
  rows=[n['requests'][i]for i in ids];v=dict(ordinals=ids)
  v['metrics']={k:st.mean(r['metrics'][k]for r in rows)for k in('TTFT_ms','decode_tokens_per_second','total_ms')}
  if'complete_model_checkpoint'in rows[0]:
   v['checkpoint_ms_per_request']={k:st.mean(sum(x[k+'_ns']for x in r['complete_model_checkpoint']['samples'])/1e6 for r in rows)for k in('capture','restore')}
  return v
 cache,cd=closed(14000);cp,cpd=closed(14600);f64,fd=closed(14800);model,md=closed(15400);gdn,gd=closed(a.GDN_case)
 require(len(cache['requests'])==14 and len(model['requests'])==16 and len(gdn['requests'])==14,'Declared request counts required')
 require(cp['save_restore_events']==60 and cp['all_payload_bytes_and_canaries_exact']and cp['full_checked_bytes']>10_000_000_000,'Complete pool/copy fixture required')
 require(f64['GPU_graphs']==144 and f64['F64_reference_all_outputs_passed']and f64['additional_shader_verified']==1,'Complete unchanged-shader F64/full-state qualification required')
 require(all(r['maximum_absolute_logit_error']==0 and r['complete_model_checkpoint']['exact_full_F32_bytes']and r['complete_model_checkpoint']['ordered_routes_exact']for r in model['requests']),'Complete original model state paths must be bit/route exact')
 require(all(len(r['complete_model_checkpoint']['samples'])==(7 if r['ordinal']>=2 else 0)for r in model['requests']),'Seven real state roundtrips per timed request required')
 pool={name:group(model,ids)for name,ids in dict(original_cold=[2,8],original_retained=[3,9],combined_cold=[4,6],combined_retained=[5,7],pooled_cold=[10,14],pooled_retained=[11,15],incremental_combined_cold=[12],incremental_combined_retained=[13]).items()}
 pool_ok=all(pool['pooled_'+kind]['checkpoint_ms_per_request']['capture']<pool['original_'+kind]['checkpoint_ms_per_request']['capture']for kind in('cold','retained'))
 batch_ok=all(sum(pool['incremental_combined_'+kind]['checkpoint_ms_per_request'].values())<sum(pool['pooled_'+kind]['checkpoint_ms_per_request'].values())for kind in('cold','retained'))
 cache_stats={name:group(cache,ids)for name,ids in dict(control_cold=[2,8],candidate_cold=[4,6],control_retained=[3,9],candidate_retained=[5,7]).items()}
 gdn_stats={name:group(gdn,ids)for name,ids in dict(control_cold=[2,8],candidate_cold=[4,6],control_retained=[3,9],candidate_retained=[5,7]).items()}
 exercised=all(r['GDN_candidate_pipeline_selections']>0 for r in gdn['requests'][4:8]);all_grades=json.loads((gd/'quality-content-and-format.private.json').read_text())
 require(all(r['semantic']for r in all_grades['rows'])and all(r['full_F32_finite']for r in gdn['requests']),'All fixed semantic tasks and full finite distributions required')
 require(all(r['maximum_absolute_logit_error']==0 for r in gdn['requests']if r['candidate_arm']==0),'Original fused-off control must remain exact')
 # Decode is the primary GPU-fusion endpoint. Require both temporal directions
 # and an average gain above measured A/A spread; total time may vary within
 # that condition's observed A/A noise, without an invented percentage floor.
 pairs=[(2,4),(8,6),(3,5),(9,7)]
 noise={}
 for kind,controls,candidates in(('cold',[2,8],[4,6]),('retained',[3,9],[5,7])):
  aa=[gdn['requests'][i]['metrics']for i in controls];bb=[gdn['requests'][i]['metrics']for i in candidates]
  decode_spread=abs(aa[0]['decode_tokens_per_second']-aa[1]['decode_tokens_per_second']);total_spread=abs(aa[0]['total_ms']-aa[1]['total_ms'])
  noise[kind]=dict(control_decode_spread=decode_spread,control_total_ms_spread=total_spread,
   decode_gain_exceeds_AA_spread=st.mean(x['decode_tokens_per_second']for x in bb)-st.mean(x['decode_tokens_per_second']for x in aa)>decode_spread,
   whole_mean_nonregressing_within_AA_spread=st.mean(x['total_ms']for x in bb)<=st.mean(x['total_ms']for x in aa)+total_spread)
 gdn_ok=exercised and all(gdn['requests'][b]['metrics']['decode_tokens_per_second']>gdn['requests'][c]['metrics']['decode_tokens_per_second']for c,b in pairs)and all(x['decode_gain_exceeds_AA_spread']and x['whole_mean_nonregressing_within_AA_spread']for x in noise.values())
 result=dict(schema='ps5-qwen-strata-followup-candidates-v1',candidate_comparisons_completed=True,production_placement_completed=False,
  checkpoint_pool_eligible=pool_ok,checkpoint_batch_eligible=batch_ok,GDN_eligible=gdn_ok,GDN_candidate_exercised=exercised,GDN_case=a.GDN_case,
  cache3424_whole_latency_eligible=all(cache_stats['candidate_'+k]['metrics']['total_ms']<cache_stats['control_'+k]['metrics']['total_ms']for k in('cold','retained')),
  cache3424_retained_decode_regression_disclosed=cache_stats['candidate_retained']['metrics']['decode_tokens_per_second']<cache_stats['control_retained']['metrics']['decode_tokens_per_second'],
  cache=cache_stats,checkpoint_injected_actual_model=pool,GDN_ordinary_actual_model=gdn_stats,GDN_AA_noise=noise,
  checkpoint_speed_is_not_ordinary_production_speed=True,checkpoint_fixture=dict(events=60,checked_bytes=cp['full_checked_bytes'],all_bytes_canaries_exact=True),
  GDN_F64_fixture=dict(graphs=144,maximum_absolute_error=max(x['maximum_absolute_error']for x in f64['cases']),all_state_history_weights_and_canaries_passed=True),
  quality=dict(fixed_semantic_requests=4,all_contents_passed=True,complete_F32_finite=True,candidate_maximum_logit_error=max(x['maximum_absolute_logit_error']for x in gdn['requests'])),
  no_arbitrary_percentage_floor=True,unlike_models_or_cache_scopes_not_pooled=True,native_evidence=proofs,
  remaining=['Normal3-request/two-frame qualification','Verified production placement','Private GitHub self-merge'],CI_runs=0,reboots=0,agents=0)
 write_json(a.out,result);print(json.dumps({k:result[k]for k in('candidate_comparisons_completed','checkpoint_pool_eligible','checkpoint_batch_eligible','GDN_candidate_exercised','GDN_eligible')}))
if __name__=='__main__':main()
