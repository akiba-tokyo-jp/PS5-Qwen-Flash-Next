#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Summarize completed native request counters without adding overlapping time."""
import argparse,json
from pathlib import Path

def latency(delta,bin_ns):
    count,bytes_,summed,errors=delta[:4];bins=delta[4:69]
    def quantile(q):
        if not count:return None
        target=max(1,int(count*q+0.999999));seen=0
        for i,n in enumerate(bins):
            seen+=n
            if seen>=target:return dict(lower_ms=i*bin_ns/1e6,upper_ms=(i+1)*bin_ns/1e6 if i<len(bins)-1 else None,overflow=i==len(bins)-1)
        return None
    return dict(calls=count,bytes=bytes_,errors=errors,mean_ms=summed/count/1e6 if count else None,p50=quantile(.5),p95=quantile(.95),p99=quantile(.99),summed_overlapping_read_wall_seconds=summed/1e9)

def analyze(path):
    terminal=json.loads(path.read_text());assert terminal['completed']and terminal['all_model_source_device_owners_positively_retired'];rows=[]
    for r in terminal['requests']:
        d=r['completed_performance']['delta'];c=r['cold_request_timing'];m=r['metrics'];n=m['generated_tokens'];den=c['quad_batch_wall_ns']
        rows.append(dict(ordinal=r['ordinal'],metrics=m,request_GB=d['source_physical_read_bytes']/1e9,
            request_GB_per_generated_token_including_prefill_and_EOS=d['source_physical_read_bytes']/1e9/n,
            physical_reads=d['source_physical_read_calls'],source_producer_wait_seconds=d['source_read_ns']/1e9,
            source_wait_fraction_of_model_process=d['source_read_ns']/d['process_ns'],plan_wall_ms=c['plan_wall_ns']/1e6,
            plan_calls=c['plan_calls'],source_handle_ms=d['source_handle_ns']/1e6,source_headroom_ms=d['source_headroom_ns']/1e6,source_consumer_ms=d['source_consumer_ns']/1e6,
            quad_batches=c['quad_batches'],quad_batch_wall_ms=den/1e6,
            quad_mean_dispatch_us=c['quad_dispatch_sum_ns']/(4*c['quad_batches'])/1e3 if c['quad_batches']else None,
            quad_tail_idle_capacity_fraction=c['quad_tail_idle_capacity_ns']/(4*den)if den else None,
            read_latency=latency(c['read_latency_delta'],c['read_latency_bin_ns']),
            raw_SSD_service_time_isolated=False,intervals_not_additive=True,
            same_policy_full_F32_error=r['maximum_absolute_logit_error'],tokens=r['token_ids']))
    return dict(completed=True,read_only_analysis=True,rows=rows,CPU_heap_peak_bytes=terminal['CPU_heap_peak_bytes'],device_ledger_peak_bytes=terminal['device_ledger_peak_bytes'])

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--terminal',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    assert not a.out.exists();result=analyze(a.terminal);a.out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
