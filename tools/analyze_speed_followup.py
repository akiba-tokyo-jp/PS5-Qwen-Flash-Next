#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reconcile finite native speed comparisons without new console operations."""
import argparse,hashlib,json,math
from pathlib import Path

def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def need(v,m):
 if not v:raise ValueError(m)
def evidence(p):
 p=Path(p);return dict(label=p.name,bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
def content(r):
 value=bytes(r['output_bytes']).decode().strip();task=r['quality_task']
 if task==0:return value=='1, 2, 3, 4, 5, 6, 7, 8'
 if task==1:return value in('猫','ねこ','ネコ')
 if task==2:return value=='42'
 lines=value.splitlines()
 if len(lines)>=3 and lines[0]in('```','```json')and lines[-1]=='```':value='\n'.join(lines[1:-1])
 try:return json.loads(value)==dict(city='Tokyo',count=3)
 except ValueError:return False
def row_summary(r):
 d=r['completed_performance']['delta'];m=r['metrics'];s=r['delivery_timing_delta'];n=m['generated_tokens'];tokens=r['token_physical_snapshots'];reads=r['cold_request_timing']['read_latency_delta']
 need(len(s)==16 and s[1]==s[2]and not s[13]and not s[15]and sum(s[8:13])==s[7],'All queued calls and active-lane wall intervals must reconcile without errors')
 need(s[2]<=reads[0]==d['source_physical_read_calls']and reads[1]==d['source_physical_read_bytes'],'Actual pool calls must be a subset of all physical source reads')
 need(r['request_reset_completed']and r['full_F32_finite']and len(tokens)==n,'Complete finite request and every output boundary required')
 for a,b in zip(tokens,tokens[1:]):need(a['physical_calls']<=b['physical_calls']and a['physical_bytes']<=b['physical_bytes'],'Token physical counters must be monotonic')
 payload=d['source_bytes']-(m['prompt_tokens']+n)*10240;need(payload>=0 and payload%1536000==0,'Original non-Expert row bytes and complete Expert triplets required')
 first,last=tokens[0],tokens[-1];decode={k:last[k]-first[k]for k in('physical_calls','physical_bytes')};busy=sum(s[9:13])
 phases=dict(prefill={k:first[k]for k in('physical_calls','physical_bytes')},accepted_decode=decode,
  EOS={k:d['source_physical_read_'+('calls'if k=='physical_calls'else'bytes')]-last[k]for k in('physical_calls','physical_bytes')})
 return dict(ordinal=r['ordinal'],phase=r['phase'],arm=r['candidate_arm'],task=r['quality_task'],metrics=m,
  content_correct=content(r),raw_counting_validator=r['counting_quality_passed'],full_F32_finite=True,
  exact_full_row_SHA256_compared=r['independent_repeat'],Expert_misses=payload//1536000,physical_calls=reads[0],physical_bytes=reads[1],
  owned_rows=r['owned_row_cache'],source_wait_ms=d['source_read_ns']/1e6,
  process_outside_source_wait_ms=(d['process_ns']-d['source_read_ns'])/1e6,request_outside_process_ms=m['total_ms']-d['process_ns']/1e6,
  mean_pread_wall_ms=reads[2]/reads[0]/1e6,physical_phases=phases,accepted_decode_transitions=n-1,
  decode_GB_per_transition=decode['physical_bytes']/(n-1)/1e9 if n>1 else None,
  decode_calls_per_transition=decode['physical_calls']/(n-1)if n>1 else None,
  delivery=dict(runs=s[0],calls=s[2],mean_queued_to_start_us=s[3]/s[1]/1e3,
   mean_read_function_wall_ms=s[4]/s[2]/1e6,mean_ready_to_producer_us=s[5]/s[2]/1e3,
   producer_consumer_ms=s[6]/1e6,run_wall_ms=s[7]/1e6,occupancy_ns=s[8:13],
   mean_API_inflight_while_any_read_active=sum(i*s[8+i]for i in range(1,5))/busy,
   mean_API_inflight_over_pool_run=sum(i*s[8+i]for i in range(1,5))/s[7],hardware_queue_depth_measured=False),
  latency_histogram=reads[4:69],latency_bin_ns=128000)
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for key in('cache','out'):p.add_argument('--'+key,type=Path,required=True)
 a=p.parse_args();need(not a.out.exists(),'Preserve previous reports');old=a.cache/'hardware-first-generation-12360';case=a.cache/'hardware-first-generation-12420'
 terminal=load(case/'native-model-terminal.private.json');closed=load(case/'restored-complete.private.json')
 need(terminal['completed']and len(terminal['requests'])==16 and terminal['all_model_source_device_owners_positively_retired']and not terminal['device_ledger_live_bytes']and closed['completed']and not closed['unknown_completion'],'Complete corrected cohort, positive owners and exact restoration required')
 failed=load(old/'native-model-terminal.private.json');need(failed['message']=='Bounded context reuse observations exhausted'and load(old/'restored-complete.private.json')['completed'],'Preserved initial harness failure and exact restoration required')
 rows=[row_summary(r)for r in terminal['requests']];need(all(r['content_correct']for r in rows),'Every finite task must pass content grading')
 routes=[load(case/f'native-arm{i}.routes.private.json')for i in range(16)]
 for i in range(4):
  need(routes[i]['records']==routes[i+8]['records']==routes[i+12]['records'],'Control and both row-cache phases require exact ordered routes')
  need(terminal['requests'][i]['token_ids']==terminal['requests'][i+8]['token_ids']==terminal['requests'][i+12]['token_ids']and terminal['requests'][i]['output_bytes']==terminal['requests'][i+8]['output_bytes']==terminal['requests'][i+12]['output_bytes'],'Control and row-cache tokens and bytes must be exact')
 phases=[]
 for phase in range(4):
  group=rows[phase*4:phase*4+4];phases.append(dict(phase=phase,arm=group[0]['arm'],total_ms=sum(r['metrics']['total_ms']for r in group),Expert_misses=sum(r['Expert_misses']for r in group),physical_calls=sum(r['physical_calls']for r in group),physical_bytes=sum(r['physical_bytes']for r in group),row_hits=sum(r['owned_rows']['hits']for r in group)))
 initial=[row_summary(load(old/f'completed-arm{i}.private.json'))for i in range(8)]
 before=sum(r['metrics']['total_ms']for r in initial[:4]);after=sum(r['metrics']['total_ms']for r in initial[4:])
 comparisons=dict(row_cache_forward_time_reduction_percent=100*(1-after/before),row_cache_reverse_time_reduction_percent=100*(1-phases[2]['total_ms']/phases[3]['total_ms']),
  protection_forward_time_reduction_percent=100*(1-phases[1]['total_ms']/phases[0]['total_ms']),protection_reverse_time_reduction_percent=100*(1-phases[1]['total_ms']/phases[2]['total_ms']),
  row_cache_physical_call_reduction=phases[3]['physical_calls']-phases[2]['physical_calls'],protection_miss_reduction=phases[2]['Expert_misses']-phases[1]['Expert_misses'])
 equality=[terminal['requests'][i+4]['token_ids']==terminal['requests'][i+8]['token_ids']and terminal['requests'][i+4]['output_bytes']==terminal['requests'][i+8]['output_bytes']for i in range(4)]
 matched=[i for i in range(4)if equality[i]]
 comparisons['protection_equal_output_tasks']=matched
 comparisons['protection_equal_output_warm_time_reduction_percent']=100*(1-sum(rows[i+4]['metrics']['total_ms']for i in matched)/sum(rows[i+8]['metrics']['total_ms']for i in matched))
 comparisons['protection_generated_token_counts']=[rows[i+4]['metrics']['generated_tokens']for i in range(4)]
 comparisons['row_cache_generated_token_counts']=[rows[i+8]['metrics']['generated_tokens']for i in range(4)]
 comparisons['protection_aggregate_is_not_equal_work_throughput']=not all(equality)
 report=dict(schema='ps5-qwen-speed-followup-headless-v1',completed=True,case=12420,requests=16,contents_correct=16,
  full_vocabulary_finite=True,matched_row_cache_full_F32_SHA256_routes_tokens_bytes_exact=True,protection_cross_policy_F32_equality_claimed=False,
  original_weight_payloads_and_reserves_unchanged=True,ordinary_close_exact_restore=True,rows=rows,phases=phases,comparisons=comparisons,
  initial_case=dict(case=12360,completed_cohort=False,positively_reset_requests_preserved=19,reason=failed['message'],whole_owner_retirement_unknown_before_normal_close=True,exact_control_restored=True),
  limitations=['Finite four-input tasks; no broad reasoning or sustained-service qualification.','Protection changes JSON output length from24 to18 tokens. The aggregate reduction is not proof of faster equal-work inference; matched-output tasks must be assessed separately.','Forward row-cache timing includes the first pipeline-cold request and uses the earlier byte-identical but not explicitly aligned row-store prototype; use the corrected reverse comparison and normal qualification for adoption.','Fixed-route replay omits cache-aware ranking feedback; native demands can change under protection.','Read-function and overlapping syscall intervals include OS and scheduling, not raw SSD NAND service.','CPU/GPU work inside the model-process residual remains unseparated.'],
  production_adopted=False,CI_runs=0,evidence=[evidence(x)for x in(case/'native-model-terminal.private.json',case/'restored-complete.private.json',old/'native-model-terminal.private.json',old/'restored-complete.private.json',Path(__file__))])
 a.out.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n');print(json.dumps(dict(completed=True,comparisons=comparisons,contents_correct=16)))
if __name__=='__main__':main()
