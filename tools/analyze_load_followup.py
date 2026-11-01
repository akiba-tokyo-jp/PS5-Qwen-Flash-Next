#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reconcile matched tail improvement, nested CPU caller wall and actual GPU ranges."""
import argparse,json,statistics
from pathlib import Path
from expert_q4 import record,require,write_json
from build_load_gpu_profile import GROUPS
CPU=['epoch_begin','epoch_complete','checkpoint','stage','logit_access','sampler','finite_scan','full_validation','token_render','token_persistence','publication','model_process','work_guard','request_run']
def load(p):return json.loads(Path(p).read_text())
def cpu_rows(rows):
 out=[]
 for row in rows:
  values=row['CPU_nested_calls_inclusive_exclusive_ns'];require(len(values)==42,'Complete CPU schema required');groups=[dict(group=name,calls=values[i*3],inclusive_ms=values[i*3+1]/1e6,exclusive_ms=values[i*3+2]/1e6)for i,name in enumerate(CPU)]
  if values[39]:require(values[39]==1 and sum(values[i*3+2]for i in range(14))==values[40],'All exclusive caller intervals must reconcile with enclosing request wall')
  out.append(dict(ordinal=row['ordinal'],metrics=row['metrics'],groups=groups,exclusive_partition_complete=bool(values[39]),inclusive_spans_must_not_be_added=True,wall_not_pure_CPU_cycles=True))
 return out
def analyze(cache,normal_case=None):
 p1=cache/'hardware-first-generation-46100';p3=cache/'hardware-first-generation-46500';a=load(p1/'native-model-terminal.private.json');b=load(p3/'native-model-terminal.private.json');speed=load(p1/'speed-analysis.private.json')
 for root,r in[(p1,a),(p3,b)]:
  require(r['completed']and len(r['requests'])==14 and r['all_model_source_device_owners_positively_retired']and r['device_ledger_live_bytes']==0 and load(root/'restored-complete.private.json')['completed'],'Complete14-request native cohort with positive retirement/close/restoration required')
  require(all(x['full_F32_finite']and x['maximum_absolute_logit_error']==0 and x['same_tokens_as_independent']for x in r['requests']),'Every full target row/token/reference must be exact')
 final=b['GPU_probe_final'];require(final[18]==final[19]==1 and final[24]==0 and final[21]==sum(final[i]for i in range(1,18,2))and final[22]>0,'Actual query creation, every measured range and positive retirement required')
 groups=[]
 for j,name in enumerate(GROUPS):
  timed=[]
  for i in(5,7):
   row=b['requests'][i];start=row['GPU_probe_before'];end=row['GPU_probe_after'];tokens=row['GPU_probe_token_boundaries'];require(len(tokens)==row['metrics']['generated_tokens'],'Every emitted token query snapshot required');first=tokens[0]['counters'];last=tokens[-1]['counters'];ns=end[j*2]-start[j*2]
   pre=first[j*2]-start[j*2];dec=last[j*2]-first[j*2];tail=end[j*2]-last[j*2];require(ns==pre+dec+tail and min(pre,dec,tail)>=0,'GPU phase counters must reconcile')
   timed.append(dict(ordinal=i,total_ns=ns,intervals=end[j*2+1]-start[j*2+1],prefill_and_first_token_ns=pre,accepted_decode_ns=dec,EOS_and_completion_ns=tail))
  groups.append(dict(group=name,mean_total_ms=statistics.mean(x['total_ns']for x in timed)/1e6,mean_decode_ms=statistics.mean(x['accepted_decode_ns']for x in timed)/1e6,mean_intervals=statistics.mean(x['intervals']for x in timed),rows=timed))
 total=sum(g['mean_total_ms']for g in groups)
 for g in groups:g['fraction_of_measured_selected_ranges_percent']=100*g['mean_total_ms']/total
 control=[a['requests'][i]for i in(3,9)];candidate=[a['requests'][i]for i in(5,7)]
 qcontrol=statistics.mean(x['actual_queue_and_serial_wait_delta'][0]for x in control);qcandidate=statistics.mean(x['actual_queue_and_serial_wait_delta'][8]for x in candidate)
 base_ms=statistics.mean(b['requests'][i]['metrics']['total_ms']for i in(3,9));profile_ms=statistics.mean(b['requests'][i]['metrics']['total_ms']for i in(5,7))
 result=dict(schema='ps5-qwen-load-followup-results-v1',completed=normal_case is not None,production_changed=False,
  P1=dict(completed=True,case=46100,all_full_F32_routes_tokens_exact=True,whole_time_reduction_percent=speed['retained_whole_time_reduction_percent'],decode_gain_percent=speed['retained_decode_gain_percent'],paired_whole_time_savings_ms=speed['temporal_whole_time_reductions_ms'],AA_spread_ms=speed['control_AA_whole_time_spread_ms'],actual_queue_calls_before=qcontrol,actual_queue_calls_after=qcandidate,actual_queue_reduction_percent=100*(1-qcandidate/qcontrol),serial_wait_calls_before=statistics.mean(x['actual_queue_and_serial_wait_delta'][2]for x in control),serial_wait_calls_after=statistics.mean(x['actual_queue_and_serial_wait_delta'][10]for x in candidate),whole_time_proof=speed),
  P2=dict(completed=False,headless_CPU=cpu_rows(b['requests'][i]for i in(3,5,7,9)),normal_CPU_pending=normal_case is None),
  P3=dict(completed=True,case=46500,full_F32_routes_tokens_exact=True,query_pools_created=final[18],query_pools_destroyed=final[19],pending_ranges=final[24],measured_ranges=final[21],timestamp_valid_bits=final[22],timestamp_period_ps=final[23],no_new_queue_wait=True,ordinary_speed_comparison_valid=False,mean_selected_range_total_ms=total,groups=groups,instrumented_whole_overhead_percent=100*(profile_ms/base_ms-1),
   groups_are_role_based_not_unconditionally_single_precisions=True,output_group_includes_final_output_related_HC_projections=True,Q2_unpack_inside_matmul_not_separately_isolated=True,all_GPU_operations_not_covered=True,timestamp_intervals_include_fused_ranges_and_dependencies=True),
  evidence=[record(p)for p in(p1/'native-model-terminal.private.json',p1/'restored-complete.private.json',p1/'speed-analysis.private.json',p3/'native-model-terminal.private.json',p3/'restored-complete.private.json')],CI_runs=0,reboots=0,learned_host_inference=False)
 if normal_case is not None:
  root=cache/f'hardware-first-generation-{normal_case}';n=load(root/'native-model-terminal.private.json');require(n['completed']and len(n['requests'])==3 and n['all_model_source_device_owners_positively_retired']and n['device_ledger_live_bytes']==0 and load(root/'restored-complete.private.json')['completed'],'Positive actual normal cohort required');result['P2'].update(completed=True,normal_CPU_pending=False,case=normal_case,normal_CPU=cpu_rows(n['requests']));result['normal_rates']=[x['metrics']['decode_tokens_per_second']for x in n['requests']]
 return result
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cache',type=Path,required=True);p.add_argument('--normal-case',type=int);p.add_argument('--out',type=Path,required=True);a=p.parse_args();r=analyze(a.cache,a.normal_case);write_json(a.out,r);print(json.dumps(dict(P1_whole_reduction=r['P1']['whole_time_reduction_percent'],P2_normal_completed=r['P2']['completed'],P3_GPU_ranges=r['P3']['measured_ranges'],GPU_groups=[(x['group'],x['mean_total_ms'])for x in sorted(r['P3']['groups'],key=lambda x:x['mean_total_ms'],reverse=True)])))
if __name__=='__main__':main()
