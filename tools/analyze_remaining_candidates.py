#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Analyze closed Q8 or placement/common-prefix PS5 comparisons without reruns."""
import argparse,json,statistics
from pathlib import Path
from expert_q4 import require,record,write_json
from analyze_expert_routing_sharing import quality,whole_request,decode_interval,aggregate

def mean(rows,key):return statistics.mean(r['metrics'][key]for r in rows)

def timed(root,rows):
 intervals=[]
 for row in rows:
  points=[json.loads((root/'IO-token-snapshots'/f"arm{row['ordinal']}-token-{i}.private.json").read_text())for i in range(1,row['metrics']['generated_tokens']+1)]
  v=decode_interval(row,points);v['whole_request']=whole_request(row);intervals.append(v)
 return dict(**aggregate(intervals),TTFT_ms_mean=mean(rows,'TTFT_ms'),total_ms_mean=mean(rows,'total_ms'))

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--kind',choices=('Q8','placement-prefix'),required=True)
 for key in ('case','out'):p.add_argument('--'+key,type=Path,required=True)
 a=p.parse_args();root=a.case;load=lambda p:json.loads(Path(p).read_text());t=load(root/'native-model-terminal.private.json');closed=load(root/'restored-complete.private.json')
 require(t['completed']and t['all_model_source_device_owners_positively_retired']and t['device_ledger_live_bytes']==0,'Positive native retirement required')
 require(closed['completed']and closed['CPU_title_normally_closed']and closed['exact_prior_configuration_restored']and not closed['unknown_completion'],'Ordinary close and exact restore required')
 rows=t['requests'];n=11 if a.kind=='Q8'else 20;require(len(rows)==n,'Finite request scope differs');fixed=[]
 for r in rows:
  require(r['request_reset_completed']and r['full_F32_finite'],'Finite complete request required')
  route=load(root/f"native-arm{r['ordinal']}.routes.private.json");require(route['complete'],'Routes must reconcile')
  if 5<=r['ordinal']<11:
   text=bytes(r['output_bytes']).decode('utf-8','strict');fixed.append(dict(mode=r['mode'],task=r['quality_task'],output=text,**quality(r['quality_task'],text)))
 summary={str(mode):timed(root,[r for r in rows[1:5]if r['mode']==mode])for mode in (0,1)}
 controls=[rows[i]for i in (1,4)];candidate=[rows[i]for i in (2,3)]
 separated=max(r['metrics']['total_ms']for r in candidate)<min(r['metrics']['total_ms']for r in controls)
 result=dict(completed=True,kind=a.kind,requests=n,model_loads=1,measured_modes=summary,fixed_quality=fixed,
  ABBA=dict(control_ordinals=[1,4],candidate_ordinals=[2,3],whole_time_reduction_fraction=1-mean(candidate,'total_ms')/mean(controls,'total_ms'),
   decode_speedup_fraction=mean(candidate,'decode_tokens_per_second')/mean(controls,'decode_tokens_per_second')-1,both_candidate_whole_times_below_both_controls=separated),
  source=record(root/'native-model-terminal.private.json'),restoration=record(root/'restored-complete.private.json'),PS5_operations=0,CI_runs=0,production_adopted=False)
 if a.kind=='Q8':
  require(all(r['actual_active_slots']==(997 if r['mode']else 867)and r['output_weight_type']=='Q8_0'for r in rows),'Actual Q8 slot selection differs')
  result.update(saved_resident_payload_bytes=595968000,slot_comparison_at_equal_Q8_output=True,
   BF16_comparison_requires_separate_closed_control=True,all_non_output_and_non_Expert_precision_preserved=True,
   integer_activation_quantization_disabled=True,eligible_for_normal_integration=separated and all(q['answer_content_passed']for q in fixed))
 else:
  require(all(r['maximum_absolute_logit_error']==0 and r['same_counting_tokens_as_control']for r in rows[:5]),'Placement must preserve complete counting logits and tokens')
  hits=sum(r['current_bundle_hits']for r in rows if r['mode']==1);require(hits>0,'Supplemental placement must actually execute')
  result['placement']=dict(current_bundle_hits=hits,complete_triplets=28,all_counting_F32_exact=True,
    eligible_for_normal_integration=separated and all(q['answer_content_passed']for q in fixed))
  groups=[dict(mode=rows[a0]['mode'],ordinals=[a0,b0],total_ms=sum(rows[i]['metrics']['total_ms']for i in (a0,b0)),
     suffix_TTFT_ms=rows[b0]['metrics']['TTFT_ms'])for a0,b0 in ((12,13),(14,15),(16,17),(18,19))]
  A=[g for g in groups if g['mode']==2];B=[g for g in groups if g['mode']==3]
  tasks=[]
  for i in range(11,20):
   r=rows[i];prefix=r['common_prefix'];text=bytes(r['output_bytes']).decode().strip();expected='45'if prefix['pair_second']else '43'
   tasks.append(dict(ordinal=i,output=text,expected=expected,content_passed=expected in text,strict_passed=text==expected,**prefix))
   if r['mode']==3:require(prefix['reused_tokens']==(16 if prefix['pair_second']else 0)and prefix['restores']==int(prefix['pair_second'])and prefix['captures']==int(not prefix['pair_second']),'Complete common-prefix state was not actually captured and restored')
  max_error=max(rows[i]['common_prefix']['suffix_first_full_vocabulary_logit_error']for i in (15,17))
  group_separated=max(g['total_ms']for g in B)<min(g['total_ms']for g in A)
  result['common_prefix']=dict(groups=groups,tasks=tasks,reused_tokens=16,maximum_suffix_first_full_vocabulary_logit_error=max_error,
   capture_charged_pair_time_reduction_fraction=1-statistics.mean(g['total_ms']for g in B)/statistics.mean(g['total_ms']for g in A),
   suffix_TTFT_reduction_fraction=1-statistics.mean(g['suffix_TTFT_ms']for g in B)/statistics.mean(g['suffix_TTFT_ms']for g in A),
   both_candidate_pair_times_below_both_controls=group_separated,
   eligible_for_normal_integration=group_separated and max_error==0 and all(q['content_passed']for q in tasks),
   exact_full_prompt_reuse_is_a_separate_workload=True)
 write_json(a.out,result)
 print(json.dumps({k:v for k,v in result.items()if k not in ('source','restoration','fixed_quality')},indent=2))

if __name__=='__main__':main()
