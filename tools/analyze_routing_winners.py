#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Select a real composition from complete, restored native evidence."""
import argparse,json
from pathlib import Path
from expert_q4 import require,record,write_json
from analyze_expert_routing_sharing import decode_interval,whole_request,aggregate,quality
ORDER=[2,2,6,14,14,6,2]+[2,6,14]*3
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--case',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 load=lambda p:json.loads(Path(p).read_text());r=a.case;t=load(r/'native-model-terminal.private.json');c=load(r/'restored-complete.private.json');proof=load(r/'IO-token-snapshots/complete.private.json')
 require(t['completed']and t['all_model_source_device_owners_positively_retired']and t['device_ledger_live_bytes']==0 and c['completed']and c['CPU_title_normally_closed']and not c['unknown_completion'],'Complete physical owners, ordinary close and exact restore required')
 require(proof['completed']and proof['copied_only_after_positive_model_source_retirement'],'Only completed durable token evidence may be analyzed')
 for row in proof['records']:require(record(row['path'])==row,'Native token evidence changed')
 require([v['mode']for v in t['requests']]==ORDER,'Exact finite composition order required')
 rows=[];q=[];width_two_rows=0
 for request in t['requests']:
  i=request['ordinal'];route=load(r/f'native-arm{i}.routes.private.json')
  require(route['complete']and route['cache_reset_before_request']and route['uploaded_bytes']==route['cache_misses']*1536000 and request['full_F32_finite']and request['request_reset_completed'],'Actual routes must reconcile all complete role payloads')
  require(any(v['experts']==6 for v in route['records']),'Actual Top-6 decode must execute')
  prefill_calls=(request['metrics']['prompt_tokens']+3)//4
  require(route['layers_per_process']==48 and len(route['records'])==48*route['process_calls'],'Complete ordered model-process routes required')
  for index,v in enumerate(route['records']):
   require(v['experts']in(6,10)and len(v['ids'])==v['experts']*v['tokens'],'Actual bounded variable-k route geometry required')
   require(v['layer']==index%48 and v['experts']==(10 if index<48*prefill_calls else 6),'Prefill and decode must use their respective selected Expert counts')
   if index>=48*prefill_calls and v['tokens']==2 and request['mode']==14:
    require(v['experts']==6,'Both verification rows must use the selected Expert count');width_two_rows+=1
  if request['mode']&4:require(request['cache_rank_calls']>0 and request['cache_rank_resident_scores']>0,'Selected cached ranking must actually execute')
  w=whole_request(request)
  if request['counting']:
   points=[load(r/f'IO-token-snapshots/arm{i}-token-{j}.private.json')for j in range(1,request['metrics']['generated_tokens']+1)]
   value=decode_interval(request,points);value.update(mode=request['mode'],whole_request=w,counting_quality_passed=request['counting_quality_passed'],same_tokens_as_control=request['same_counting_tokens_as_control'],maximum_absolute_logit_error=request['maximum_absolute_logit_error'],speculation=request['speculation'])
   rows.append(value)
  else:
   text=bytes(request['output_bytes']).decode('utf-8',errors='replace');q.append(dict(mode=request['mode'],task=request['quality_task'],raw_output=text,**quality(request['quality_task'],text)))
 require(len(q)==9 and all(sorted(v['task']for v in q if v['mode']==m)==[0,1,2]for m in(2,6,14)),'Every composition needs all three fixed quality tasks')
 require(width_two_rows>0 and all(v['speculation']['attempts']>1 and v['speculation']['attempts']==v['speculation']['accepted']+v['speculation']['rejected']for v in rows if v['mode']==14),'Repeated same-k target verification must actually complete')
 ids={2:[1,6],6:[2,5],14:[3,4]};measured={m:aggregate([rows[i]for i in indices])for m,indices in ids.items()}
 whole_rate=lambda i:rows[i]['whole_request']['generated_tokens']/rows[i]['whole_request']['total_seconds']
 decode_rate=lambda i:rows[i]['accepted_transitions']/rows[i]['decode_seconds']
 judgments={m:dict(contents=sum(v['answer_content_passed']for v in q if v['mode']==m),strict_format=sum(v['strict_format_passed']for v in q if v['mode']==m),requests=3)for m in ids}
 comparisons=[]
 for control,candidate in ((2,6),(6,14),(2,14)):
  A,B=measured[control],measured[candidate]
  comparisons.append(dict(control_policy=control,candidate_policy=candidate,control=A,candidate=B,
   decode_speedup_fraction=B['decode_tok_s']/A['decode_tok_s']-1,whole_request_speedup_fraction=B['whole_request']['generated_tok_s']/A['whole_request']['generated_tok_s']-1,
   both_candidate_decodes_faster_than_both_controls=min(decode_rate(i)for i in ids[candidate])>max(decode_rate(i)for i in ids[control]),
   both_candidate_whole_requests_faster_than_both_controls=min(whole_rate(i)for i in ids[candidate])>max(whole_rate(i)for i in ids[control])))
 eligible=[2];whole_only_eligible=[2]
 for candidate in (6,14):
  match=next(v for v in comparisons if v['control_policy']==2 and v['candidate_policy']==candidate)
  marginal=next(v for v in comparisons if v['control_policy']==(6 if candidate==14 else 2)and v['candidate_policy']==candidate)
  if match['both_candidate_whole_requests_faster_than_both_controls']and marginal['both_candidate_whole_requests_faster_than_both_controls']:whole_only_eligible.append(candidate)
  if match['both_candidate_decodes_faster_than_both_controls']and marginal['both_candidate_decodes_faster_than_both_controls']and match['whole_request_speedup_fraction']>=0 and marginal['whole_request_speedup_fraction']>=0 and all(rows[i]['counting_quality_passed']for i in ids[candidate]):eligible.append(candidate)
 selected=max(eligible,key=lambda m:measured[m]['decode_tok_s'])
 value=dict(schema='ps5-qwen-routing-winners-selection-v1',completed=True,all_quality_tasks_completed=True,all_native_compositions_tested=True,selected_policy=selected,
  criterion='Owner generation-speed priority: both decode repetitions beat both incremental controls, with no aggregate whole-request regression; normal independent confirmation still required',
  selection_criterion_refined_after_exploratory_comparison=True,strict_whole_request_rule_would_select=max(whole_only_eligible,key=lambda m:measured[m]['whole_request']['generated_tok_s']),
  comparisons=comparisons,quality_summary=judgments,quality_requests=q,counting_requests=rows,actual_width_two_Top6_route_rows=width_two_rows,
  CPU_heap_peak_bytes=t['CPU_heap_peak_bytes'],device_ledger_peak_bytes=t['device_ledger_peak_bytes'],all_source_GPU_owners_retired=True,ordinary_close_and_exact_restore=True,production_placement_pending=True,
  inputs=[record(r/x)for x in('native-model-terminal.private.json','restored-complete.private.json','IO-token-snapshots/complete.private.json')],CI_runs=0)
 write_json(a.out,value);print(json.dumps({k:v for k,v in value.items()if k not in('inputs','quality_requests','counting_requests')},indent=2))
if __name__=='__main__':main()
