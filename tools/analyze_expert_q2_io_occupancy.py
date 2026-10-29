#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reconcile observed pread occupancy and adjacent merging after native closure."""
import argparse,json
from pathlib import Path
from expert_q4 import require,record,write_json
from analyze_expert_q2_measurements import decode_phase
from analyze_expert_q2_io_distribution import quantile_interval

def analyze(root,ordinals):
    result=decode_phase(root,ordinals)
    bins=[sum(r['individual_read_latency_histogram'][i]for r in result['requests'])for i in range(65)]
    totals=[0]*7;saved=0
    for request in result['requests']:
        arm=request['request'];n=request['accepted_decode_transitions']+1
        before=json.loads((root/f'IO-token-snapshots/arm{arm}-token-1.private.json').read_text())['completed_performance']
        after=json.loads((root/f'IO-token-snapshots/arm{arm}-token-{n}.private.json').read_text())['completed_performance']
        require(before['source_IO_occupancy_6']==after['source_IO_occupancy_6']==0,'No read may remain in flight at token snapshots')
        delta=[after[f'source_IO_occupancy_{i}']-before[f'source_IO_occupancy_{i}']for i in range(5)]
        require(delta[0]==request['physical_calls'],'Observed pread calls must reconcile with actual source calls')
        for i in range(5):totals[i]+=delta[i]
        totals[5]=max(totals[5],after['source_IO_occupancy_5'])
        saved+=after['adjacent_bundle_calls_saved']-before['adjacent_bundle_calls_saved']
    busy=totals[3]+totals[4];elapsed=sum(totals[2:5]);require(busy>0 and totals[5]<=2,'Two-lane complete occupancy required')
    return dict(result,quantiles={f'P{int(p*100)}':quantile_interval(bins,p)for p in (.5,.95,.99)},
        occupancy=dict(calls=totals[0],overlapping_starts=totals[1],maximum_observed_API_inflight=totals[5],
            idle_ns=totals[2],one_read_ns=totals[3],two_reads_ns=totals[4],
            average_inflight_while_any_read_active=(totals[3]+2*totals[4])/busy,
            fraction_of_busy_time_with_two_reads=totals[4]/busy,
            read_busy_fraction_of_decode_observation=busy/elapsed,
            API_not_hardware_SSD_queue=True),decode_merged_calls_saved=saved)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cache',type=Path,required=True);p.add_argument('--case',type=int,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    root=a.cache/f'hardware-first-generation-{a.case}';terminal=json.loads((root/'native-model-terminal.private.json').read_text())
    require(terminal['completed']and terminal['full_F32_continuation_and_routes_passed']and len(terminal['requests'])==5,'Complete five-request native comparison required')
    requests=terminal['requests'];control=analyze(root,[1,4]);candidate=analyze(root,[2,3])
    for row in requests[1:]:
        require(row['token_ids']==requests[0]['token_ids']and row['maximum_absolute_logit_error']==0,'Same complete F32 and emitted tokens must match')
    require(control['physical_GB_per_decode_token']==candidate['physical_GB_per_decode_token'],'Merging must preserve physical read bytes')
    seconds=lambda r:sum(x['decode_s']for x in r['requests'])
    rate=lambda r:r['accepted_decode_transitions']/seconds(r)
    old=rate(control);new=rate(candidate)
    source_paths=[root/'native-model-terminal.private.json',root/'restored-complete.private.json',root/'IO-token-snapshots/complete.private.json']
    report=dict(schema='ps5-qwen-Q2-native-IO-occupancy-v1',completed=True,case=a.case,
        control=control,candidate=candidate,control_decode_tok_s=old,candidate_decode_tok_s=new,
        decode_speedup_fraction=new/old-1,control_source_calls=sum(x['physical_calls']for x in control['requests']),
        candidate_source_calls=sum(x['physical_calls']for x in candidate['requests']),
        same_physical_bytes_full_F32_and_output_tokens=True,
        original_source_device_owners_retired_and_normal_close=True,
        maximum_API_inflight_two_not_hardware_queue=True,
        inputs=[record(x)for x in source_paths],CI_runs=0)
    write_json(a.out,report)
    print(json.dumps({k:v for k,v in report.items()if k not in ('control','candidate','inputs')},indent=2))
    for name,r in [('control',control),('candidate',candidate)]:print(name,json.dumps(r['occupancy']))
if __name__=='__main__':main()
