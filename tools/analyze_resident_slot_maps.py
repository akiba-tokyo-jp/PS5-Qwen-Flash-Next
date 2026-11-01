#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compare completed map-reuse requests; never infer adoption from upload counts alone."""
import argparse,json,statistics
from pathlib import Path
from expert_q4 import record,require,write_json

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--cache',type=Path,required=True);p.add_argument('--case',type=int,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 root=a.cache/f'hardware-first-generation-{a.case}'
 n=json.loads((root/'native-model-terminal.private.json').read_text());closed=json.loads((root/'restored-complete.private.json').read_text())
 require(n['completed']and n['all_model_source_device_owners_positively_retired']and n['device_ledger_live_bytes']==0 and closed['completed']and not closed['unknown_completion'],'Positive model completion and exact ordinary restoration required')
 require(len(n['requests'])==14 and n['full_F32_continuation_and_routes_passed'],'Complete matched/quality cohort required')
 rows=[]
 for r in n['requests']:
  d=r['resident_slot_map_delta'];m=r['metrics'];s=r['completed_performance']['delta'];q=r['actual_queue_and_serial_wait_delta']
  require(len(d)==8 and d[0]==d[3]>0 and d[1]+d[2]==d[3]and d[4]==2048*d[1]and d[5]==2048*d[2],'Every actual map publication and transfer byte must reconcile')
  require(r['resident_slot_map_reuse_enabled']==bool(r['candidate_arm'])and r['full_F32_finite']and r['request_reset_completed'],'Exact executed arm and finite completed work required')
  require(d[2]>0 if r['candidate_arm']else d[2]==0,'Actual reuse/control path required')
  rows.append(dict(ordinal=r['ordinal'],candidate=bool(r['candidate_arm']),metrics=m,map_attempts=d[0],uploads=d[1],reuses=d[2],saved_bytes=d[5],source={k:s[k]for k in('source_bytes','source_physical_read_bytes','source_physical_read_calls','source_read_ns')},queue_submissions=q[8],queue_submit_wall_ms=q[9]/1e6,serialized_wait_calls=q[10],serialized_wait_ms=q[11]/1e6,maximum_absolute_logit_error=r['maximum_absolute_logit_error'],routes_exact=r.get('cross_control_ordered_routes_exact'),quality_passed=r['counting_quality_passed']))
 control=[n['requests'][i]for i in(3,9)];candidate=[n['requests'][i]for i in(5,7)]
 exact=all(r['maximum_absolute_logit_error']==0 and r['same_tokens_as_independent']and r['cross_control_ordered_routes_exact']and r['metrics']['generated_tokens']==22 for r in control+candidate)
 equal_source=all(len({r['completed_performance']['delta'][k]for r in control+candidate})==1 for k in('source_bytes','source_physical_read_bytes','source_physical_read_calls'))
 aa=abs(control[1]['metrics']['total_ms']-control[0]['metrics']['total_ms'])
 paired=[control[i]['metrics']['total_ms']-candidate[i]['metrics']['total_ms']for i in range(2)]
 decode=[control[i]['metrics']['decode_ms']-candidate[i]['metrics']['decode_ms']for i in range(2)]
 quality=json.loads((root/'candidate-contents-decision.private.json').read_text())['all_contents_passed']
 positive=exact and equal_source and quality and min(paired)>aa and min(decode)>0
 result=dict(schema='ps5-qwen-resident-slot-map-analysis-v1',completed=True,case=a.case,SELF_SHA256=n['candidate_SELF_sha256'],rows=rows,all_full_F32_routes_tokens_exact=exact,identical_source_demand=equal_source,fixed_semantic_tasks_passed=quality,paired_whole_time_savings_ms=paired,paired_decode_time_savings_ms=decode,control_AA_whole_spread_ms=aa,retained_decode_rates_control=[r['metrics']['decode_tokens_per_second']for r in control],retained_decode_rates_candidate=[r['metrics']['decode_tokens_per_second']for r in candidate],mean_whole_time_reduction_percent=100*(1-statistics.mean(r['metrics']['total_ms']for r in candidate)/statistics.mean(r['metrics']['total_ms']for r in control)),internal_comparison_qualifies=positive,original_normal_external_qualification_required=True,production_adopted=False,CPU_heap_peak_bytes=n['CPU_heap_peak_bytes'],device_ledger_peak_bytes=n['device_ledger_peak_bytes'],evidence=[record(root/'native-model-terminal.private.json'),record(root/'restored-complete.private.json')],PS5_operations=0,CI_runs=0)
 write_json(a.out,result)
 print(json.dumps({k:result[k]for k in('completed','internal_comparison_qualifies','all_full_F32_routes_tokens_exact','identical_source_demand','fixed_semantic_tasks_passed','paired_whole_time_savings_ms','paired_decode_time_savings_ms','control_AA_whole_spread_ms','retained_decode_rates_control','retained_decode_rates_candidate','mean_whole_time_reduction_percent')}))
if __name__=='__main__':main()
