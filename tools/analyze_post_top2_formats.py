#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compare Q4 replay timings with bracketing same-controller Q8-format controls."""
import argparse,json,statistics
from pathlib import Path
from expert_q4 import record,require,write_json

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('before','candidate','after','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();cases=[a.before,a.candidate,a.after];rs=[json.loads((x/'native-model-terminal.private.json').read_text())for x in cases]
 for r in rs:require(r['completed']and len(r['requests'])==14 and r['all_model_source_device_owners_positively_retired']and r['device_ledger_live_bytes']==0,'Complete positive cases required')
 for root in cases:require(json.loads((root/'restored-complete.private.json').read_text())['completed'],'Ordinary close and exact restoration required')
 groups={}
 for label,ordinals in [('cold',[2,8]),('retained',[3,9])]:
  baseline=[r['requests'][i]for r in(rs[0],rs[2])for i in ordinals]
  # Q4's two internal labels are the same model/controller and are replays.
  ids=[2,4,6,8]if label=='cold'else[3,5,7,9];candidate=[rs[1]['requests'][i]for i in ids]
  expected=baseline[0]['output_bytes'];require(all(x['output_bytes']==expected and x['token_ids']==baseline[0]['token_ids']for x in baseline+candidate),'Equivalent emitted work required for format timing')
  for row in baseline+candidate:require(row['speculation']['attempts']==6 and row['speculation']['accepted']==6 and row['speculation']['rejected']==0,'Same selected cap6 policy and executed verification sequence required')
  metrics={k:dict(Q8=statistics.mean(x['metrics'][k]for x in baseline),Q4=statistics.mean(x['metrics'][k]for x in candidate))for k in('total_ms','decode_tokens_per_second','TTFT_ms')}
  source_equal=all(row['completed_performance']['delta']['source_physical_read_bytes']==baseline[0]['completed_performance']['delta']['source_physical_read_bytes']and row['completed_performance']['delta']['source_physical_read_calls']==baseline[0]['completed_performance']['delta']['source_physical_read_calls']for row in baseline+candidate)
  route_paths=[(cases[0],i)for i in ordinals]+[(cases[2],i)for i in ordinals]+[(cases[1],i)for i in ids]
  routes=[json.loads((root/f'native-arm{i}.routes.private.json').read_text())['records']for root,i in route_paths]
  route_equal=all(x==routes[0]for x in routes)
  groups[label]=dict(metrics=metrics,equivalent_tokens_and_bytes=True,same_source_bytes_and_calls=source_equal,complete_routes_equal=route_equal,
   Q4_replay_ordinals=ids,Q8_control_ordinals=ordinals,decode_gain_percent=100*(metrics['decode_tokens_per_second']['Q4']/metrics['decode_tokens_per_second']['Q8']-1),
   whole_time_reduction_percent=100*(1-metrics['total_ms']['Q4']/metrics['total_ms']['Q8']),
   slowest_Q4_total_ms=max(x['metrics']['total_ms']for x in candidate),fastest_Q8_total_ms=min(x['metrics']['total_ms']for x in baseline),
   all_Q4_replays_faster_than_all_Q8_controls=max(x['metrics']['total_ms']for x in candidate)<min(x['metrics']['total_ms']for x in baseline))
 grades=json.loads((a.candidate/'quality-content-and-format.private.json').read_text())['rows'];quality=[x['semantic']for x in grades if x['ordinal']>=10]
 eligible=groups['retained']['all_Q4_replays_faster_than_all_Q8_controls']and groups['retained']['complete_routes_equal']and groups['retained']['same_source_bytes_and_calls']
 write_json(a.out,dict(completed=True,kind='bracketed_Q8_Q4_format_comparison',source_cases=[record(x/'native-model-terminal.private.json')for x in cases],
  groups=groups,quality_tasks=quality,resident_output_bytes_saved=317849600,internal_Q4_arm_difference_not_called_format_gain=True,
  matched_full_vocabulary_finite_within_each_format=True,cross_format_full_vocabulary_KL_measured=False,
  broad_quality_preservation_established=False,eligible_for_combination_validation=eligible,production_adopted=False))
 print(json.dumps(dict(completed=True,retained_whole_time_reduction_percent=groups['retained']['whole_time_reduction_percent'],
  retained_decode_gain_percent=groups['retained']['decode_gain_percent'],all_Q4_replays_faster=groups['retained']['all_Q4_replays_faster_than_all_Q8_controls'],eligible_for_combination=eligible)))
if __name__=='__main__':main()
