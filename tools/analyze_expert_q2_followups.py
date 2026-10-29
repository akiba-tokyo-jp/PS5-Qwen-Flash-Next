#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reconcile closed Q2 reader, copy and exact-prefix comparisons."""
import argparse,json
from pathlib import Path
from expert_q4 import require,record,write_json
from analyze_expert_q2_measurements import decode_phase
def pooled(rows,key='decode'):
 if key=='decode':return sum(x['metrics']['generated_tokens']-1 for x in rows)/sum(x['metrics']['decode_ms']/1000 for x in rows)
 return sum(x['metrics']['generated_tokens']for x in rows)/sum(x['metrics']['total_ms']/1000 for x in rows)
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--kind',choices=('copy','reader','prefix','bundle','speculative'),required=True)
 for k in ('case','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();t=json.loads((a.case/'native-model-terminal.private.json').read_text());closed=json.loads((a.case/'restored-complete.private.json').read_text())
 require(t['completed']and t['all_model_source_device_owners_positively_retired']and t['full_F32_continuation_and_routes_passed']and closed['completed']and not closed['unknown_completion'],'Closed exact-state comparison required')
 rows=t['requests'];require(all(r['maximum_absolute_logit_error']==0 and r['request_reset_completed']for r in rows),'Exact same-format arithmetic required')
 comparisons=[(a.kind,[1,4],[2,3])]if a.kind in ('copy','bundle','speculative')else [('range_hint',[1,4],[2,3]),('parallel_composite',[5,8],[6,7])]if a.kind=='reader'else [('exact_prefix_repeated_request',[2,8],[4,6])]
 summaries=[]
 for name,A,B in comparisons:
  control=[rows[i]for i in A];candidate=[rows[i]for i in B];old,new=pooled(control),pooled(candidate)
  phaseA,phaseB=decode_phase(a.case,set(A)),decode_phase(a.case,set(B),a.kind=='speculative')
  counters=[]
  for r in control+candidate:
   d=r['completed_performance']['delta'];route=json.loads((a.case/f"native-arm{r['ordinal']}.routes.private.json").read_text())
   counters.append(dict(ordinal=r['ordinal'],decode_tok_s=r['metrics']['decode_tokens_per_second'],TTFT_ms=r['metrics']['TTFT_ms'],total_ms=r['metrics']['total_ms'],misses=route['cache_misses'],read_calls=d['source_physical_read_calls'],read_bytes=d['source_physical_read_bytes'],logical_source_bytes=d['source_bytes'],process_ns=d['process_ns'],consumer_ns=d['source_consumer_ns'],streamed_bytes=d.get('mapped_streaming_write_bytes',0),streamed_calls=d.get('mapped_streaming_write_calls',0),range_hint_hits=d.get('range_hint_hits',0),range_lookups=d.get('range_lookups',0),composite_parallel_pairs=d.get('composite_parallel_pairs',0),bundled_Experts=d.get('bundle_Experts',0),speculation=r.get('speculation')))
  values=dict(name=name,control_ordinals=A,candidate_ordinals=B,control_decode_tok_s=old,candidate_decode_tok_s=new,decode_speedup_fraction=new/old-1,
   every_candidate_faster_than_every_control=min(r['metrics']['decode_tokens_per_second']for r in candidate)>max(r['metrics']['decode_tokens_per_second']for r in control),
   control_IO={k:v for k,v in phaseA.items()if k!='requests'and 'classes'not in k},candidate_IO={k:v for k,v in phaseB.items()if k!='requests'and 'classes'not in k},requests=counters)
  if a.kind in ('copy','reader'):require(len({(r['misses'],r['read_calls'],r['read_bytes'])for r in counters})==1,'An independent reader/copy arm changed Expert demand or physical bytes')
  if a.kind=='copy':
   values['candidate_path_exercised']=all(counters[i]['streamed_calls']>0 for i in (2,3))
   values['eligible_for_adoption']=values['candidate_path_exercised']and values['every_candidate_faster_than_every_control']
  elif a.kind=='reader':
   metric='range_hint_hits'if name=='range_hint'else'composite_parallel_pairs'
   values['candidate_path_exercised']=all(r[metric]>0 for r in counters[2:]);values['eligible_for_adoption']=values['candidate_path_exercised']and values['every_candidate_faster_than_every_control']
  elif a.kind in ('bundle','speculative'):
   if a.kind=='bundle':
    require(len({(r['misses'],r['logical_source_bytes'])for r in counters})==1,'A bundle arm changed Expert demand or logical bytes')
    values['candidate_path_exercised']=all(r['bundled_Experts']>0 for r in counters[2:])
   else:
    negative=rows[5]['speculation'];require(rows[5]['forced_rejection_diagnostic']and negative['rejected']==negative['snapshot_restores']==1 and negative['accepted']==0,'Completed same-format full-state rejection control required')
    values['forced_rejection_full_ordinary_F32_and_routes_passed']=True
    values['candidate_path_exercised']=all(r['speculation']['attempts']==1 for r in counters[2:])
    values['same_width_F32_comparison_only']=True
   values['eligible_for_adoption']=values['candidate_path_exercised']and values['every_candidate_faster_than_every_control']
  else:
   cgroup=[rows[i]for i in (1,2,7,8)];bgroup=[rows[i]for i in (3,4,5,6)]
   values.update(repeated_TTFT_control_ms=sum(r['metrics']['TTFT_ms']for r in control)/2,repeated_TTFT_candidate_ms=sum(r['metrics']['TTFT_ms']for r in candidate)/2,
    capture_charged_group_control_tok_s=pooled(cgroup,'total'),capture_charged_group_candidate_tok_s=pooled(bgroup,'total'),
    candidate_path_exercised=all(r['prefix']['request_hit']and r['prefix']['last_reused_prompt_tokens']==30 for r in candidate))
   values['capture_charged_group_speedup_fraction']=values['capture_charged_group_candidate_tok_s']/values['capture_charged_group_control_tok_s']-1
   values['eligible_for_adoption']=values['candidate_path_exercised']and values['capture_charged_group_speedup_fraction']>0
  summaries.append(values)
 report=dict(schema='ps5-qwen-Q2-followup-result-v1',completed=True,kind=a.kind,case=int(a.case.name.rsplit('-',1)[1]),all_full_F32_rows_and_ordered_routes_exact=True,comparisons=summaries,production_adopted=False,CI_runs=0,evidence=[record(a.case/x)for x in ('native-model-terminal.private.json','restored-complete.private.json','IO-token-snapshots/complete.private.json')])
 write_json(a.out,report)
 print(json.dumps(dict(completed=True,kind=a.kind,case=report['case'],comparisons=[{k:v for k,v in s.items()if k not in ('control_IO','candidate_IO','requests')}for s in summaries]),indent=2))
if __name__=='__main__':main()
