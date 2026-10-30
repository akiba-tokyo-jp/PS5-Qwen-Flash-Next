#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Analyze finite prefill output/batch comparisons after exact production restore."""
import argparse,json,statistics
from pathlib import Path
from expert_q4 import require,record,write_json
from build_lean_prefill import ORDER,COUNTING
from analyze_expert_routing_sharing import quality,whole_request,decode_interval,aggregate

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--case',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 load=lambda p:json.loads(Path(p).read_text());root=a.case;t=load(root/'native-model-terminal.private.json');closed=load(root/'restored-complete.private.json');proof=load(root/'IO-token-snapshots/complete.private.json')
 require(t['completed']and t['all_model_source_device_owners_positively_retired']and t['device_ledger_live_bytes']==0,'Complete physical model/source/GPU retirement required')
 require(closed['completed']and closed['CPU_title_normally_closed']and closed['exact_prior_configuration_restored']and not closed['unknown_completion'],'Ordinary close and exact production restore required')
 require(proof['completed']and proof['copied_only_after_positive_model_source_retirement'],'Only positively completed token evidence may be analyzed')
 for row in proof['records']:require(record(row['path'])==row,'Durable token evidence changed')
 require([r['mode']for r in t['requests']]==ORDER,'The exact six-mode symmetric order is required')
 rows=[];q=[];route_proofs=[]
 for request in t['requests']:
  i=request['ordinal'];mode=request['mode'];policy=request['prefill_policy'];path=root/f'native-arm{i}.routes.private.json';route=load(path);route_proofs.append(record(path))
  require(request['full_F32_finite']and request['request_reset_completed']and route['complete'],'Finite logits, positive reset and actual routes required')
  require(route['uploaded_bytes']==route['cache_misses']*1536000 and len(route['records'])==48*route['process_calls'],'Every actual Expert role payload must reconcile')
  expected_width=4<<(mode//2);selected_last=bool(mode&1);n=request['metrics']['prompt_tokens'];calls=(n+expected_width-1)//expected_width
  require(policy['width']==expected_width and policy['last_output_only']==selected_last and policy['calls']==calls and policy['input_tokens']==n and policy['output_rows']==(calls if selected_last else n),'Actual prefill calls and output-row counters differ')
  for index,v in enumerate(route['records']):
   layer=index%48;call=index//48
   require(v['layer']==layer and len(v['ids'])==v['tokens']*v['experts'],'Complete ordered variable-width routes required')
   if call<calls:
    width=min(expected_width,n-call*expected_width);wanted=1 if selected_last and layer==47 else width
    require(v['experts']==10 and v['tokens']==wanted,'Actual prefill route width or final-layer output cropping differs')
   else:require(v['tokens']==1 and v['experts']==6,'Original ordinary Top-6 decode must remain selected')
  if request['counting']:
   points=[load(root/f'IO-token-snapshots/arm{i}-token-{j}.private.json')for j in range(1,request['metrics']['generated_tokens']+1)]
   value=decode_interval(request,points);whole=whole_request(request)
   delta=request['completed_performance']['delta'];tail={k:points[-1]['completed_performance'][k]-points[0]['completed_performance'][k] for k in ('source_physical_read_bytes','source_physical_read_calls')}
   value.update(mode=mode,whole_request=whole,TTFT_ms=request['metrics']['TTFT_ms'],prefill_ms=request['metrics']['prefill_ms'],prefill_policy=policy,
    prefill_and_final_EOS_physical_bytes=delta['source_physical_read_bytes']-tail['source_physical_read_bytes'],
    counting_quality_passed=request['counting_quality_passed'],same_tokens_as_control=request['same_counting_tokens_as_control'],
    maximum_absolute_logit_error=request['maximum_absolute_logit_error'],cache_hits=route['cache_hits'],cache_misses=route['cache_misses'])
   rows.append(value)
  else:
   text=bytes(request['output_bytes']).decode('utf-8',errors='replace');q.append(dict(mode=mode,task=request['quality_task'],raw_output=text,**quality(request['quality_task'],text)))
 require(len(rows)==len(COUNTING)and len(q)==18,'All declared finite speed and quality requests must complete')
 measured={};repetitions={}
 for mode in range(6):
  selected=[r for r in rows if r['mode']==mode and r['ordinal']!=0];require(len(selected)==2,'Two symmetric timed repetitions required')
  summary=aggregate(selected);summary.update(prefill_ms_mean=statistics.mean(r['prefill_ms']for r in selected),
   TTFT_ms_mean=statistics.mean(r['TTFT_ms']for r in selected),prefill_ms_repetitions=[r['prefill_ms']for r in selected],
   total_ms_repetitions=[r['whole_request']['total_seconds']*1000 for r in selected],
   counting_contents_passed=sum(r['counting_quality_passed']for r in selected),
   fixed_quality_contents=sum(r['answer_content_passed']for r in q if r['mode']==mode),fixed_quality_strict=sum(r['strict_format_passed']for r in q if r['mode']==mode))
  measured[mode]=summary;repetitions[mode]=selected
 comparisons=[]
 for control,candidate in ((0,1),(0,2),(0,4),(2,3),(4,5),(1,3),(1,5),(0,3),(0,5)):
  A,B=measured[control],measured[candidate];ca,cb=repetitions[control],repetitions[candidate]
  comparisons.append(dict(control_mode=control,candidate_mode=candidate,
   prefill_time_reduction_fraction=1-B['prefill_ms_mean']/A['prefill_ms_mean'],
   decode_speedup_fraction=B['decode_tok_s']/A['decode_tok_s']-1,
   whole_request_speedup_fraction=B['whole_request']['generated_tok_s']/A['whole_request']['generated_tok_s']-1,
   whole_request_byte_reduction_fraction=1-B['whole_request']['physical_GB_per_request']/A['whole_request']['physical_GB_per_request'],
   whole_request_call_reduction_fraction=1-B['whole_request']['read_calls_per_request']/A['whole_request']['read_calls_per_request'],
   both_prefills_faster_than_both_controls=max(r['prefill_ms']for r in cb)<min(r['prefill_ms']for r in ca),
   both_whole_requests_faster_than_both_controls=max(r['whole_request']['total_seconds']for r in cb)<min(r['whole_request']['total_seconds']for r in ca)))
 # Prefill is the intervention's primary endpoint. Adoption still requires
 # independent normal-app prefix/speculation qualification, not this selection.
 eligible=[0]
 for mode in range(1,6):
  match=next(v for v in comparisons if v['control_mode']==0 and v['candidate_mode']==mode)
  if match['both_prefills_faster_than_both_controls']and match['both_whole_requests_faster_than_both_controls']and measured[mode]['counting_contents_passed']==2:eligible.append(mode)
 selected=min(eligible,key=lambda m:measured[m]['prefill_ms_mean'])
 result=dict(schema='ps5-qwen-lean-prefill-analysis-v1',completed=True,case=int(root.name.rsplit('-',1)[1]),
  measured_modes=measured,comparisons=comparisons,selected_for_normal_confirmation=selected,
  selection_criterion='Both prefill repetitions and both whole requests beat both controls; report all finite quality outcomes. Production requires independent normal prefix/speculation verification.',
  quality_requests=q,counting_requests=rows,CPU_heap_peak_bytes=t['CPU_heap_peak_bytes'],device_ledger_peak_bytes=t['device_ledger_peak_bytes'],
  all_model_source_GPU_owners_positively_retired=True,ordinary_close_and_exact_restoration=True,production_adopted=False,
  warmup_scope='One initial mode-0 warmup; first encounters with other shapes remain charged to their first timed repetition.',
  legacy_descriptive_fields_superseded=['completed_performance.all_prompt_outputs_requested: use prefill_policy.output_rows and actual final-layer route geometry',
   'completed_performance.maximum_parallel_source_reads: inherited headless label; bound flags5 and unchanged qualified four-read provider are authoritative'],
  inputs=[record(root/x)for x in ('native-model-terminal.private.json','restored-complete.private.json','IO-token-snapshots/complete.private.json')]+route_proofs,
  source_reference='MaxDevv/lean-qwenflash@fa9a772d9aa9b94a5653a2c6880eeb97af0d2e9d',CI_runs=0)
 write_json(a.out,result)
 print(json.dumps({k:v for k,v in result.items()if k not in ('inputs','counting_requests','quality_requests')},indent=2))
if __name__=='__main__':main()
