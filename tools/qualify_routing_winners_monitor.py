#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Qualify the actual normal app before any production placement."""
import argparse,json
from pathlib import Path
from expert_q4 import require,record,write_json
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('case','receipt','prior-installation','selection','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();load=lambda p:json.loads(Path(p).read_text());r=a.case;t=load(r/'native-model-terminal.private.json');closed=load(r/'restored-complete.private.json');observer=load(r/'passive-observer/complete.private.json');visual=load(r/'visual-review.private.json');receipt=load(a.receipt);prior=load(a.prior_installation);selection=load(a.selection)
 require(t['completed']and t['passive_monitor_and_API_completed']and t['all_model_source_device_owners_positively_retired']and t['device_ledger_live_bytes']==0 and t['source_windows']==t['source_completed_windows'],'Actual completed normal model/source/GPU protocol required')
 require(closed['completed']and closed['CPU_title_normally_closed']and closed['exact_prior_configuration_restored']and not closed['unknown_completion']and observer['completed'],'Ordinary close, exact restored control and API/frame evidence required')
 require(visual['actual_native_frames_viewed']==2 and visual['metrics_legible']and visual['no_chat_controls']and visual['Q2_precision_label_correct'],'Actual two passive frames must be viewed')
 bits=receipt['routing_winners_normal']['selected_policy'];require(bits==selection['selected_policy']==t['routing_winners_policy']and t['graph_reuse_disabled_for_policy'],'Actual normal selected policy differs')
 require(len(t['requests'])==3 and all(v['full_F32_finite']and v['request_reset_completed']and v['counting_quality_passed']for v in t['requests']),'Every normal request must finish with finite full vocabulary and correct counting')
 first,final=t['requests'][1:];require(first['maximum_absolute_logit_error']<=1e-5 and first['same_tokens_as_independent'],'Same-policy independent repeat must preserve F32 and tokens')
 require(final['prefix']['request_hit']and final['prefix']['captures']==final['prefix']['restores']==1 and final['prefix']['last_reused_prompt_tokens']==30,'Complete actual prefix reuse required')
 pair=sum(v['metrics']['generated_tokens']for v in(first,final))/sum(v['metrics']['total_ms']/1000 for v in(first,final))
 baseline=prior['external_requests'][0]['decode_tokens_per_second'];old_pair=prior['optimized_normal_comparison']['capture_charged_group_tok_s']
 require(first['metrics']['decode_tokens_per_second']>baseline and pair>old_pair and final['metrics']['TTFT_ms']<first['metrics']['TTFT_ms'],'Normal first decode, capture-charged pair throughput and actual prefix TTFT must improve')
 width_two_rows=0
 for i,v in enumerate(t['requests']):
  route=load(r/f'native-arm{i}.routes.private.json');require(route['complete']and route['uploaded_bytes']==route['cache_misses']*1536000,'Every complete variable-k route must reconcile full Expert payloads')
  prefill_calls=0 if v['prefix']['request_hit']else(v['metrics']['prompt_tokens']+3)//4
  require(len(route['records'])==48*route['process_calls'],'Complete ordered process routes required')
  for index,row in enumerate(route['records']):
   require(row['layer']==index%48 and row['experts']==(10 if index<48*prefill_calls else 6)and len(row['ids'])==row['experts']*row['tokens'],'Actual prefill Top-10 and decode Top-6 required')
   if index>=48*prefill_calls and row['tokens']==2:width_two_rows+=1
  io=v['io_optimization'];policy=v['routing_policy']
  require(io['flags']==5 and io['adjacent_calls_saved']>0 and io['extra_bundled_Experts']>0 and io['quad_batches']>0 and io['maximum_lifetime_quad_inflight']==4,'All previous I/O winners must execute')
  require(policy['bits']==bits and policy['decode_Experts']==6 and policy['preferences_latched_per_target_event'],'Actual event-latched policy required')
  if bits&4:require(policy['rank_calls']>0 and policy['resident_scores']>0,'Actual cached ranking must execute')
 if bits&8:
  s=final['speculation'];c=final['checkpoint']
  require(t['final_prefix_handoff_consumed']and width_two_rows>0 and s['attempts']>1 and s['attempts']==s['accepted']+s['rejected']and s['queued_bonus_samples']==s['accepted']and c['captures']==s['attempts']and c['restores']==s['rejected'],'Every real final-consumer verification/capture/rollback/bonus must reconcile')
 require(t['CPU_heap_peak_bytes']<=512<<20 and t['device_ledger_peak_bytes']<=1792<<20,'Original measured heap/device caps required')
 value=dict(schema='ps5-qwen-routing-winners-normal-qualification-v1',completed=True,all_declared_adoption_criteria_passed=True,production_placement_pending=True,selected_policy=bits,
  first_independent_decode_tok_s=first['metrics']['decode_tokens_per_second'],first_independent_TTFT_ms=first['metrics']['TTFT_ms'],repeat_decode_tok_s=final['metrics']['decode_tokens_per_second'],repeat_TTFT_ms=final['metrics']['TTFT_ms'],capture_charged_pair_generated_tok_s=pair,
  previous_independent_decode_tok_s=baseline,previous_pair_generated_tok_s=old_pair,independent_decode_speedup_fraction=first['metrics']['decode_tokens_per_second']/baseline-1,pair_speedup_fraction=pair/old_pair-1,
  same_policy_independent_full_F32_max_error=first['maximum_absolute_logit_error'],final_approximate_max_F32_difference=final['maximum_absolute_logit_error'],all_counting_tokens_equal=t['all_repeated_Q2_tokens_and_bytes_exact'],final_same_k_width_two_route_rows=width_two_rows,actual_final_speculation=final['speculation'],actual_final_checkpoint=final['checkpoint'],
  CPU_heap_peak_bytes=t['CPU_heap_peak_bytes'],device_ledger_peak_bytes=t['device_ledger_peak_bytes'],normal_source_receipt=record(a.receipt),control_installation=record(a.prior_installation),composition_selection=record(a.selection),
  inputs=[record(r/x)for x in('native-model-terminal.private.json','restored-complete.private.json','passive-observer/complete.private.json','visual-review.private.json')],CI_runs=0)
 write_json(a.out,value);print(json.dumps({k:v for k,v in value.items()if k not in('inputs','normal_source_receipt','control_installation','composition_selection')},indent=2))
if __name__=='__main__':main()
