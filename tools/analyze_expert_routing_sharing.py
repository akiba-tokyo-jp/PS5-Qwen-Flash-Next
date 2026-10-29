#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Analyze positively closed approximate routing and causal target experiments."""
import argparse,json,math,re
from pathlib import Path
from expert_q4 import require,record,write_json
COMPARISONS=[('decode_top8',[1,4],[2,3]),('decode_top6',[4,7],[5,6]),
 ('repeated_causal_width2',[7,10],[8,9])]
def quality(task,text):
 raw=text.strip();content=False;strict=False
 if task==0:
  content='good morning'in raw.casefold();strict=raw.casefold()in ('good morning','good morning.','good morning!')
 elif task==1:
  content=re.search(r'(?<!\d)43(?!\d)',raw)is not None;strict=raw=='43'
 elif task==2:
  target=dict(city='Tokyo',count=3)
  try:strict=json.loads(raw)==target
  except (ValueError,TypeError):pass
  for found in re.finditer(r'\{',raw):
   try:
    value,_=json.JSONDecoder().raw_decode(raw[found.start():])
    if value==target:content=True;break
   except ValueError:pass
 else:raise ValueError('Unknown fixed quality task')
 return dict(answer_content_passed=content,strict_format_passed=strict,
  output_normalized_in_application=False,finite_scope_only=True)

def decode_interval(request,points):
 n=request['metrics']['generated_tokens'];require(n==len(points)and n>=2,'Complete two-or-more-token native interval required')
 require([p['token_id']for p in points]==request['token_ids'],'All actual emitted tokens must be present')
 for i,p in enumerate(points,1):
  require(p['generated_tokens']==i and p['completed_performance']['source_chunks']==p['completed_performance']['source_completed_windows'],'Positive per-token source completion required')
 first,last=points[0],points[-1];a,b=first['completed_performance'],last['completed_performance']
 require(all(b[k]>=v for k,v in a.items()),'Completed cumulative counters moved backwards')
 d={k:b[k]-v for k,v in a.items()};seconds=(last['elapsed_ms']-first['elapsed_ms'])/1000;transitions=n-1
 require(seconds>0 and math.isclose(transitions/seconds,request['metrics']['decode_tokens_per_second'],rel_tol=1e-7),'Measured first-to-last decode interval differs')
 require(d['source_physical_read_calls']==d['individual_read_calls']and d['source_physical_read_bytes']==d['individual_read_bytes']and not d['individual_read_errors'],'Individual pread and source reader bytes/calls must reconcile')
 return dict(ordinal=request['ordinal'],accepted_transitions=transitions,decode_seconds=seconds,
  physical_bytes=d['source_physical_read_bytes'],read_calls=d['source_physical_read_calls'],source_wait_ns=d['source_read_ns'],
  model_process_ns=d['process_ns'],model_process_calls=d['process_calls'],individual_pread_wall_ns=d['individual_read_wall_ns'],
  speculative_and_rejected_work_inside_interval_charged=True,prefill_and_final_EOS_excluded=True)

def aggregate(rows):
 total=lambda k:sum(r[k]for r in rows);n=total('accepted_transitions');s=total('decode_seconds')
 return dict(accepted_transitions=n,decode_tok_s=n/s,physical_GB_per_token=total('physical_bytes')/n/1e9,
  read_calls_per_token=total('read_calls')/n,producer_wait_ms_per_token=total('source_wait_ns')/n/1e6,
  effective_GB_per_producer_wait_second=total('physical_bytes')/total('source_wait_ns'),
  source_wait_fraction_of_model_process=total('source_wait_ns')/total('model_process_ns'),
  mean_individual_pread_ms=total('individual_pread_wall_ns')/total('read_calls')/1e6)

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--case',type=Path,required=True);p.add_argument('--partial-case',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 load=lambda p:json.loads(Path(p).read_text());root=a.case
 terminal=load(root/'native-model-terminal.private.json');closed=load(root/'restored-complete.private.json');proof=load(root/'IO-token-snapshots/complete.private.json')
 require(terminal['schema']=='ps5-qwen-routing-sharing-result-v1'and terminal['completed']and terminal['all_model_source_device_owners_positively_retired']and terminal['device_ledger_live_bytes']==0,'Completed actual model/source/GPU experiment required')
 require(closed['completed']and closed['CPU_title_normally_closed']and closed['exact_prior_configuration_restored']and not closed['unknown_completion'],'Ordinary close and exact restored production required')
 require(proof['completed']and proof['copied_only_after_positive_model_source_retirement'],'Closed token evidence required')
 for r in proof['records']:require(record(r['path'])==r,'Captured evidence changed')
 requests=terminal['requests'];require(len(requests)==26,'All remaining native cases must complete')
 rows=[];quality_rows=[];route_paths=[]
 for request in requests:
  i=request['ordinal'];route_path=root/f'native-arm{i}.routes.private.json';route=load(route_path);route_paths.append(record(route_path))
  require(route['complete']and route['cache_reset_before_request']and route['uploaded_bytes']==route['cache_misses']*1536000 and request['full_F32_finite']and request['request_reset_completed'],'Every actual variable-k route must reconcile full role payloads')
  hist={}
  for row in route['records']:
   k=row['experts'];require(k in (6,8,10)and len(row['ids'])==k*row['tokens'],'Bounded actual routed cardinality required')
   hist[k]=hist.get(k,0)+row['tokens']
  mode=request['mode']
  if mode in (2,3):require(hist.get(8 if mode==2 else 6,0)>0,'The actual reduced-k graph must execute')
  if mode==1:require(request['cache_rank_calls']>0 and request['cache_rank_resident_scores']>0,'Cache-aware selection must actually execute')
  if request['counting']:
   points=[load(root/f'IO-token-snapshots/arm{i}-token-{j}.private.json')for j in range(1,request['metrics']['generated_tokens']+1)]
   measured=decode_interval(request,points)
   measured.update(mode=mode,counting_quality_passed=request['counting_quality_passed'],same_tokens_as_control=request['same_counting_tokens_as_control'],whole_request_misses=route['cache_misses'],actual_k_token_histogram=hist,speculation=request['speculation'],cache_rank_calls=request['cache_rank_calls'],cache_rank_CPU_ns=request['cache_rank_CPU_ns'])
   rows.append(measured)
  else:
   text=bytes(request['output_bytes']).decode('utf-8',errors='replace');judgment=quality(request['quality_task'],text)
   quality_rows.append(dict(ordinal=i,mode=mode,task=request['quality_task'],raw_output=text,stop_reason=request['stop_reason'],metrics=request['metrics'],**judgment))
 require(any(r['mode']==4 and r['speculation']['attempts']>1 for r in rows),'Repeated multi-token verification must be actually exercised')
 partial_proof=load(a.partial_case/'partial-IO-token-snapshots/complete.private.json')
 basis=load(a.partial_case/'self-exit-recovery-basis.private.json');restored=load(a.partial_case/'restored-complete.private.json')
 require(partial_proof['completed']and not partial_proof['full_model_protocol_completed']and basis['OS_exit_idle_confirmed']and basis['app_self_terminated']and restored['completed'],'The partial run must preserve its actual self-exit and CPU-only restoration, not fabricate native retirement')
 for r in partial_proof['records']+partial_proof['request_records']:require(record(r['path'])==r,'Durable partial request evidence changed')
 partial_rows=[]
 for i in range(5):
  request=load(a.partial_case/f'native-arm{i}.result.private.json')
  require(request['request_reset_completed']and request['full_F32_finite'],'Only positively reset native requests may survive a later abort')
  points=[load(a.partial_case/f'partial-IO-token-snapshots/arm{i}-token-{j}.private.json')for j in range(1,request['metrics']['generated_tokens']+1)]
  value=decode_interval(request,points);value.update(mode=request['mode'],counting_quality_passed=request['counting_quality_passed'],same_tokens_as_control=request['same_counting_tokens_as_control'],cache_rank_calls=request['cache_rank_calls'],cache_rank_CPU_ns=request['cache_rank_CPU_ns'])
  partial_rows.append(value)
 require(all(partial_rows[i]['cache_rank_calls']>0 for i in (2,3)),'Cache-aware ranking must actually execute in both completed partial candidates')
 by_id={r['ordinal']:r for r in rows};comparisons=[]
 def compare(name,control,candidate,lookup,case):
  A,B=aggregate([lookup[i]for i in control]),aggregate([lookup[i]for i in candidate])
  every=min(lookup[i]['accepted_transitions']/lookup[i]['decode_seconds']for i in candidate)>max(lookup[i]['accepted_transitions']/lookup[i]['decode_seconds']for i in control)
  return dict(name=name,case=case,control_ordinals=control,candidate_ordinals=candidate,control=A,candidate=B,
   decode_speedup_fraction=B['decode_tok_s']/A['decode_tok_s']-1,read_byte_reduction_fraction=1-B['physical_GB_per_token']/A['physical_GB_per_token'],read_call_reduction_fraction=1-B['read_calls_per_token']/A['read_calls_per_token'],every_candidate_faster_than_every_control=every,
   counting_all_passed=all(lookup[i]['counting_quality_passed']for i in candidate),same_counting_tokens_as_control=all(lookup[i]['same_tokens_as_control']for i in candidate))
 comparisons.append(compare('cache_rank_1_5',[1,4],[2,3],{r['ordinal']:r for r in partial_rows},9440))
 for name,control,candidate in COMPARISONS:
  comparisons.append(compare(name,control,candidate,by_id,int(root.name.rsplit('-',1)[1])))
 result=dict(schema='ps5-qwen-routing-sharing-analysis-v1',completed=True,all_three_families_physically_exercised=True,case=int(root.name.rsplit('-',1)[1]),comparisons=comparisons,counting_requests=rows,partial_counting_requests=partial_rows,quality_requests=quality_rows,
  quality_summary=[dict(mode=m,answer_contents=sum(r['answer_content_passed']for r in quality_rows if r['mode']==m),strict_format=sum(r['strict_format_passed']for r in quality_rows if r['mode']==m),requests=3)for m in range(5)],
  CPU_heap_peak_bytes=terminal['CPU_heap_peak_bytes'],device_ledger_peak_bytes=terminal['device_ledger_peak_bytes'],graph_reuse_disabled_uniformly=True,all_model_source_GPU_owners_positively_retired=True,ordinary_close_and_exact_restoration=True,production_adopted=False,
  partial_run=dict(case=9440,full_native_protocol_completed=False,completed_requests_reused=5,app_self_terminated_during_Top8_CPU_graph_construction=True,native_global_GPU_retirement_terminal_present=False,CPU_only_idle_and_exact_restoration_confirmed=True),
  inputs=[record(root/x)for x in ('native-model-terminal.private.json','restored-complete.private.json','IO-token-snapshots/complete.private.json')]+route_paths+[record(a.partial_case/x)for x in ('partial-IO-token-snapshots/complete.private.json','self-exit-recovery-basis.private.json','restored-complete.private.json')],CI_runs=0,unknown_completion=False)
 write_json(a.out,result)
 print(json.dumps({k:v for k,v in result.items()if k not in ('inputs','counting_requests','partial_counting_requests','quality_requests')},indent=2))
if __name__=='__main__':main()
