#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Classify each complete same-model I/O ABBA after positive native restoration."""
import argparse,json
from pathlib import Path
from expert_q4 import require,record,write_json
from analyze_expert_q2_measurements import decode_phase
COMPARISONS=[('extra_bundles',[1,4],[2,3]),('temporal_probation',[5,8],[6,7]),('depth_four',[9,12],[10,11])]
def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--cache',type=Path,required=True);p.add_argument('--case',type=int,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 root=a.cache/f'hardware-first-generation-{a.case}';terminal=json.loads((root/'native-model-terminal.private.json').read_text());close=json.loads((root/'restored-complete.private.json').read_text())
 require(close['completed']and close['CPU_title_normally_closed']and close['exact_prior_configuration_restored']and not close['unknown_completion'],'Complete known native retirement, normal close and exact restoration required')
 require(terminal['completed']and len(terminal['requests'])==13 and terminal['full_F32_continuation_and_routes_passed']and terminal['all_model_source_device_owners_positively_retired'],'Complete independent model comparisons required')
 requests=terminal['requests'];routes=[]
 for ordinal in range(13):
  route=json.loads((root/f'native-arm{ordinal}.routes.private.json').read_text());require(route['complete']and route['cache_reset_before_request'],'Complete cold native routes required');routes.append(route)
 for r in requests[1:]:require(r['maximum_absolute_logit_error']==0 and r['token_ids']==requests[0]['token_ids'],'All full F32 rows and generated tokens must be exact')
 require(all(r['records']==routes[0]['records']for r in routes),'Ordered routes must remain identical')
 results=[]
 for name,control,candidate in COMPARISONS:
  A=decode_phase(root,control);B=decode_phase(root,candidate)
  rate=lambda x:x['accepted_decode_transitions']/sum(r['decode_s']for r in x['requests'])
  old,new=rate(A),rate(B);every=min(requests[i]['metrics']['decode_tokens_per_second']for i in candidate)>max(requests[i]['metrics']['decode_tokens_per_second']for i in control)
  rows=[]
  for ordinal in control+candidate:
   r=requests[ordinal];d=r['completed_performance']['delta'];row=dict(ordinal=ordinal,mode=r['IO_reduction_mode'],decode_tok_s=r['metrics']['decode_tokens_per_second'],misses=routes[ordinal]['cache_misses'],physical_read_calls=d['source_physical_read_calls'],physical_read_bytes=d['source_physical_read_bytes'],quad_batches=d['quad_batches'])
   last=json.loads((root/f"IO-token-snapshots/arm{ordinal}-token-{r['metrics']['generated_tokens']}.private.json").read_text());row['quad_peak_absolute']=last['completed_performance']['quad_peak'];rows.append(row)
  if name=='depth_four':require(all(r['quad_batches']>0 and r['quad_peak_absolute']>=3 for r in rows if r['ordinal']in candidate),'Actual positive four-demand execution must be exercised')
  if name=='extra_bundles':require(all(routes[i]['cache_misses']==routes[control[0]]['cache_misses']for i in control+candidate),'Layout must preserve misses')
  useful=new>old and every
  results.append(dict(name=name,control_ordinals=control,candidate_ordinals=candidate,control_decode_tok_s=old,candidate_decode_tok_s=new,decode_speedup_fraction=new/old-1,every_candidate_faster_than_every_control=every,selected_for_normal_composition=useful,disposition='positive same-model comparison'if useful else 'tested without a consistent speed improvement',control_IO={k:v for k,v in A.items()if k!='requests'},candidate_IO={k:v for k,v in B.items()if k!='requests'},requests=rows))
 report=dict(schema='ps5-qwen-Q2-IO-reduction-results-v1',completed=True,case=a.case,all_three_native_ABBA_completed=True,full_F32_and_ordered_routes_exact=True,comparisons=results,selected_flags=sum(bit for bit,name in [(1,'extra_bundles'),(2,'temporal_probation'),(4,'depth_four')]if next(r for r in results if r['name']==name)['selected_for_normal_composition']),CPU_heap_peak_bytes=terminal['CPU_heap_peak_bytes'],device_ledger_peak_bytes=terminal['device_ledger_peak_bytes'],all_owners_retired_and_exact_production_restored=True,inputs=[record(root/x)for x in ('native-model-terminal.private.json','restored-complete.private.json','IO-token-snapshots/complete.private.json')],CI_runs=0)
 write_json(a.out,report)
 print(json.dumps({k:v for k,v in report.items()if k not in ('comparisons','inputs')},indent=2))
 for r in results:print(json.dumps({k:v for k,v in r.items()if k not in ('control_IO','candidate_IO','requests')}))
if __name__=='__main__':main()
