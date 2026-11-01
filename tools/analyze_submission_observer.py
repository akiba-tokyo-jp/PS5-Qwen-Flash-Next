#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reconcile completed request-bound native driver observations without console access."""
import argparse,json,statistics
from pathlib import Path
from build_submission_observer import NAMES
from build_load_gpu_profile import GROUPS
from expert_q4 import record,require,write_json

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cache',type=Path,required=True);p.add_argument('--case',type=int,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 root=a.cache/f'hardware-first-generation-{a.case}';n=json.loads((root/'native-model-terminal.private.json').read_text());closed=json.loads((root/'restored-complete.private.json').read_text())
 require(n['completed']and n['all_model_source_device_owners_positively_retired']and not n['device_ledger_live_bytes']and closed['completed']and not closed['unknown_completion'],'Positive model completion and ordinary restoration required')
 require(len(n['requests'])==14,'Complete14-request cohort required');rows=[]
 package=json.loads((root/'candidate-package.private.json').read_text());native=json.loads(Path(package['native_link_receipt']['path']).read_text());platform_valid=native.get('submission_observer',{}).get('platform_counters_monotonic',False)
 for r in n['requests']:
  d=r['driver_timing_delta'];require(len(d)==47 and r['throughput_mode']==5 and r['full_F32_finite'],'Complete observation with current production throughput required')
  if not r['driver_timing_enabled']:require(not any(d[:40]),'Disabled driver counters must remain unchanged')
  v=dict(zip(NAMES[:47],d));q=r['actual_queue_and_serial_wait_delta'];m=r['metrics']
  row=dict(ordinal=r['ordinal'],enabled=r['driver_timing_enabled'],metrics=m,counters=v,
           queue_submit_calls=q[8],queue_submit_wall_ms=q[9]/1e6,serialized_fence_calls=q[10],serialized_fence_wall_ms=q[11]/1e6,
           source_wait_ms=r['completed_performance']['delta']['source_read_ns']/1e6,
           maximum_absolute_logit_error=r['maximum_absolute_logit_error'],cross_control_routes_exact=r.get('cross_control_ordered_routes_exact'),
           timing_scopes_overlap_and_must_not_be_added=True)
  if r['driver_timing_enabled']:
   require(v['submit_calls']>=v['copy_calls']>0 and v['marker_poll_calls']>=v['marker_flush_polls'],'Successful native submit/copy and poll accounting required')
   row.update(successful_empty_submit_calls=v['submit_calls']-v['copy_calls'],
              native_submit_ms=v['submit_ns']/1e6,submit_lock_wait_ms=v['submit_lock_ns']/1e6,submit_lock_hold_ms=v['submit_lock_hold_ns']/1e6,
              command_claim_ms=v['claim_ns']/1e6,command_copy_ms=v['copy_ns']/1e6,
              sequence_wait_ms=v['sequence_wait_ns']/1e6,sync_wait_ms=v['sync_wait_ns']/1e6,
              actual_sleep_ms=v['sleep_ns']/1e6,requested_sleep_ms=v['requested_sleep_us']/1e3,
              platform_ms={key:v[key]/1e6 for key in ['platform_flush_ns','platform_AGC_ns','platform_suspend_ns']}if platform_valid else None,
              command_MiB=v['command_words']*4/(1<<20))
  if 'GPU_probe_before'in r:
   before=r['GPU_probe_before'];after=r['GPU_probe_after'];points=r['GPU_probe_token_boundaries']
   require(len(points)==m['generated_tokens'],'Every emitted-token query boundary required')
   first,last=points[0]['counters'],points[-1]['counters']
   row['GPU_ranges']=[dict(group=name,total_ms=(after[2*i]-before[2*i])/1e6,accepted_decode_ms=(last[2*i]-first[2*i])/1e6,intervals=after[2*i+1]-before[2*i+1])for i,name in enumerate(GROUPS)]
  rows.append(row)
 control=[n['requests'][i]for i in [3,9]];candidate=[n['requests'][i]for i in [5,7]]
 require(all(r['metrics']['generated_tokens']==22 and r['maximum_absolute_logit_error']==0 and r['same_tokens_as_independent']for r in control+candidate),'Identical completed counting work required')
 cm=statistics.mean(r['metrics']['total_ms']for r in control);pm=statistics.mean(r['metrics']['total_ms']for r in candidate)
 result=dict(schema='ps5-qwen-submission-observer-analysis-v1',completed=True,case=a.case,SELF_SHA256=n['candidate_SELF_sha256'],model_receipt_SHA256=n['model_receipt_sha256'],rows=rows,
             retained_observation_overhead_ms=pm-cm,retained_observation_overhead_percent=100*(pm/cm-1),
             control_AA_whole_spread_ms=abs(control[1]['metrics']['total_ms']-control[0]['metrics']['total_ms']),
             diagnostic_not_an_optimization_candidate=True,production_changed=False,platform_counters_valid=platform_valid,
             limitations=['Finite tasks, not sustained service.','Native timing intervals overlap; do not add nested sequence/sync/submit/lock/AGC times.','Sequence waiting includes real GPU execution; sleep duration can overlap useful execution.','Platform time counters already existed in the native adapter.','GPU ranges, if present, are diagnostic fused role ranges with separately observed instrumentation overhead.'],
             evidence=[record(root/'native-model-terminal.private.json'),record(root/'restored-complete.private.json')],PS5_operations=0,CI_runs=0)
 if 'GPU_probe_final'in n:
  final=n['GPU_probe_final'];require(final[18]==final[19]and final[18]>0 and not final[24]and final[21]>0,'Every query owner must positively retire with no pending ranges');result['GPU_query_lifetime']=dict(created=final[18],destroyed=final[19],measured_ranges=final[21],pending=final[24])
 write_json(a.out,result);print(json.dumps(dict(completed=True,case=a.case,retained_observation_overhead_ms=pm-cm,candidate=[{k:r[k]for k in ['ordinal','native_submit_ms','sequence_wait_ms','actual_sleep_ms','command_copy_ms','submit_lock_wait_ms','platform_ms']}for r in rows if r['ordinal']in [5,7]])))
if __name__=='__main__':main()
