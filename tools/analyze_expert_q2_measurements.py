#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compare captured Q4/Q2 I/O and fused-graph timings without console access."""
import argparse,json,math,statistics
from pathlib import Path
from expert_q4 import require,record
from analyze_expert_q2_bottleneck import case_summary


def load(path):return json.loads(Path(path).read_text(encoding='utf-8'))


def aggregate_whole(case):
    rows=case['requests'][1:];total=lambda k:sum(r[k]for r in rows)
    physical=total('whole_request_physical_bytes');calls=total('whole_request_physical_calls')
    wait=total('whole_request_source_wait_s');evaluated=total('evaluated_model_tokens')
    return dict(case=case['case'],format=case['Expert_format'],timed_requests=len(rows),
        prompt_tokens_per_request=30,generated_tokens_per_request=22,evaluated_tokens_per_request=evaluated/len(rows),
        whole_request_physical_GB=physical/len(rows)/1e9,whole_request_read_calls=calls/len(rows),
        physical_GB_per_evaluated_token_including_prompt_EOS=physical/evaluated/1e9,
        read_calls_per_evaluated_token_including_prompt_EOS=calls/evaluated,
        amortized_producer_wait_ms_per_physical_call=wait*1000/calls,
        amortized_wait_is_not_individual_call_latency=True,
        effective_GB_per_producer_wait_second=physical/1e9/wait,
        effective_GB_per_total_request_second=physical/1e9/total('total_request_s'),
        mean_physical_read_KiB=physical/calls/1024,
        process_outside_source_wait_s_per_request=(total('model_process_s')-wait)/len(rows))


def decode_phase(root):
    terminal=load(root/'native-model-terminal.private.json');closed=load(root/'restored-complete.private.json')
    proof=load(root/'IO-token-snapshots/complete.private.json')
    require(terminal['completed']and terminal['all_model_source_device_owners_positively_retired']and
        terminal['full_F32_continuation_and_routes_passed']and terminal['device_ledger_live_bytes']==0 and
        closed['completed']and closed['CPU_title_normally_closed']and not closed['unknown_completion']and
        proof['completed']and proof['copied_only_after_positive_model_source_retirement'],
        'Positive diagnostic, full arithmetic, source/device retirement and ordinary close required')
    for row in proof['records']:require(record(row['path'])==row,'Captured token evidence changed')
    rows=[]
    for request in terminal['requests'][1:]:
        ordinal=request['ordinal'];count=request['metrics']['generated_tokens']
        points=[load(root/'IO-token-snapshots'/f'arm{ordinal}-token-{i}.private.json')for i in range(1,count+1)]
        require(count==22 and [p['token_id']for p in points]==request['token_ids']and request['counting_quality_passed'],
            'Complete correct native counting stream required')
        for i,p in enumerate(points,1):
            require(p['generated_tokens']==i and p['completed_performance']['source_chunks']==p['completed_performance']['source_completed_windows'],
                'Only positively completed source boundaries qualify')
        for a,b in zip(points,points[1:]):
            require(b['elapsed_ms']>=a['elapsed_ms']and b['Expert_uploaded_bytes']>=a['Expert_uploaded_bytes']and
                all(b['completed_performance'][k]>=v for k,v in a['completed_performance'].items()),'Cumulative token evidence reversed')
        first,last=points[0],points[-1];d={k:last['completed_performance'][k]-v for k,v in first['completed_performance'].items()}
        transitions=count-1;wall=(last['elapsed_ms']-first['elapsed_ms'])/1000
        require(d['process_calls']==transitions and math.isclose(transitions/wall,request['metrics']['decode_tokens_per_second'],rel_tol=1e-7),
            'First-to-last token interval must exclude prefill and final EOS')
        row=dict(request=ordinal,accepted_decode_transitions=transitions,decode_s=wall,
            physical_bytes=d['source_physical_read_bytes'],physical_calls=d['source_physical_read_calls'],
            source_wait_s=d['source_read_ns']/1e9,model_process_s=d['process_ns']/1e9)
        if 'individual_read_calls'in d:
            require(d['individual_read_calls']==row['physical_calls']and d['individual_read_bytes']==row['physical_bytes']and
                d['individual_read_errors']==0,'Independent pread counter must exactly reconcile with the source reader')
            hist=[d['individual_read_histogram_'+str(i)]for i in range(65)]
            require(sum(hist)==row['physical_calls'],'Every returned physical read needs one latency bin')
            groups=[dict(bucket=i,calls=d['individual_read_size_calls_'+str(i)],
                bytes=d['individual_read_size_bytes_'+str(i)],wall_ns=d['individual_read_size_ns_'+str(i)])for i in range(17)]
            require(sum(g['calls']for g in groups)==row['physical_calls']and sum(g['bytes']for g in groups)==row['physical_bytes']and
                sum(g['wall_ns']for g in groups)==d['individual_read_wall_ns'],'Size classes must reconcile all individual call times and bytes')
            row.update(individual_read_wall_ns=d['individual_read_wall_ns'],individual_read_latency_histogram=hist,
                size_classes=[g for g in groups if g['calls']])
        rows.append(row)
    sums=lambda k:sum(r[k]for r in rows)
    out=dict(completed=True,case=int(root.name.rsplit('-',1)[1]),prefill_and_final_EOS_excluded=True,
        accepted_decode_transitions=sums('accepted_decode_transitions'),requests=rows,
        physical_GB_per_decode_token=sums('physical_bytes')/sums('accepted_decode_transitions')/1e9,
        read_calls_per_decode_token=sums('physical_calls')/sums('accepted_decode_transitions'),
        effective_GB_per_producer_wait_second=sums('physical_bytes')/1e9/sums('source_wait_s'),
        source_wait_fraction_of_model_process=sums('source_wait_s')/sums('model_process_s'))
    if all('individual_read_wall_ns'in r for r in rows):
        histogram=[sum(r['individual_read_latency_histogram'][i]for r in rows)for i in range(65)]
        def percentile(fraction):
            target=math.ceil(sum(histogram)*fraction);accumulated=0
            for i,count in enumerate(histogram):
                accumulated+=count
                if accumulated>=target:return dict(lower_ms=i*.128,upper_ms=(i+1)*.128 if i<64 else None)
            raise ValueError('Latency histogram is incomplete')
        sizes=[]
        for bucket in range(17):
            groups=[g for r in rows for g in r['size_classes']if g['bucket']==bucket]
            if not groups:continue
            count=sum(g['calls']for g in groups);byte_count=sum(g['bytes']for g in groups);ns=sum(g['wall_ns']for g in groups)
            sizes.append(dict(lower_KiB=bucket*64,upper_KiB=(bucket+1)*64 if bucket<16 else None,
                calls=count,mean_returned_KiB=byte_count/count/1024,mean_pread_wall_ms=ns/count/1e6))
        out.update(mean_individual_pread_wall_ms=sums('individual_read_wall_ns')/sums('physical_calls')/1e6,
            individual_pread_p50_interval=percentile(.5),individual_pread_p95_interval=percentile(.95),
            individual_read_size_classes=sizes,
            individual_call_times_overlap_and_are_not_critical_path=True)
    return out


def component_times(cache):
    reports={}
    for number in (7560,8160,8600):
        root=cache/f'hardware-first-generation-{number}';v=load(root/'native-model-terminal.private.json');closed=load(root/'restored-complete.private.json')
        require(v['completed']and v['all_outputs_reference_valid']and v['all_backends_positively_retired']and
            v['source_descriptor_and_scratch_retired']and v['device_ledger_live_bytes']==0 and closed['completed']and
            closed['CPU_title_normally_closed']and not closed['unknown_completion'],'Positively closed native GPU component required')
        reports[number]=v
    output=[]
    for role,columns,number,fmt in (('Gate/Up',2560,8160,'Q2_K'),('Down',640,8600,'Q2_0')):
        means=[]
        for case,quant in ((7560,'Q4_0'),(number,fmt)):
            rows=[r for r in reports[case]['cases']if r['width']==1 and r['columns']==columns]
            values={name:[s['compute_us']for r in rows for arm in r['arms']if arm['format']==name for s in arm['samples']]
                for name in ('BF16',quant)}
            require(len(rows)==(6 if columns==2560 else 3)and all(len(v)==len(rows)*4 and min(v)>0 for v in values.values()),
                'Matched shape, width, group and four native samples per format required')
            means.append(dict(case=case,format=quant,compute_ms=statistics.mean(values[quant])/1000,
                paired_BF16_ms=statistics.mean(values['BF16'])/1000,samples=len(values[quant])))
        old,new=means
        output.append(dict(role=role,width=1,Q4=old,Q2=new,Q2_over_Q4_wall_ratio=new['compute_ms']/old['compute_ms'],
            cross_run_BF16_normalized_ratio=(new['compute_ms']/new['paired_BF16_ms'])/(old['compute_ms']/old['paired_BF16_ms'])))
    return dict(completed=True,source_cases=[7560,8160,8600],separate_dequantization_pass_exists_in_measured_width_one_path=False,
        standalone_dequantization_duration_measured=False,
        scope='Already measured fused quantized matrix graph, submit, synchronize and checkpoint wall time; excludes timed SSD delivery',
        pure_GPU_timestamp=False,groups=output,
        conclusion='No increased fused-graph wall time observed in these finite component samples; not full-model dequant-only timing')


def analyze(cache,measurement):
    old,_=case_summary(cache,7820,2764800);new,_=case_summary(cache,8780,1536000)
    before,after=aggregate_whole(old),aggregate_whole(new)
    q4decode=decode_phase(cache/'hardware-first-generation-8010')
    candidate=cache/f'hardware-first-generation-{measurement}'
    actual=decode_phase(candidate)if(candidate/'restored-complete.private.json').exists()else None
    if actual:
        actual.update(physical_byte_reduction_vs_Q4=1-actual['physical_GB_per_decode_token']/q4decode['physical_GB_per_decode_token'],
            read_call_reduction_vs_Q4=1-actual['read_calls_per_decode_token']/q4decode['read_calls_per_decode_token'])
    return dict(schema='ps5-qwen-Q2-requested-measurements-v1',completed=actual is not None,
        whole_request_controls=[before,after],whole_request_byte_reduction=1-after['whole_request_physical_GB']/before['whole_request_physical_GB'],
        whole_request_call_reduction=1-after['whole_request_read_calls']/before['whole_request_read_calls'],
        Expert_triplet_payload_bytes=dict(Q4=2764800,Q2=1536000,Q2_over_Q4=1536000/2764800),
        exact_Q4_decode=q4decode,exact_Q2_decode=actual,
        additional_measurement=dict(case=measurement,status='completed'if actual else'prepared_not_executed_automatic_review_blocked',
            current_owner_freeze_risk_confirmation_required=actual is None,prepared_SELF_sha256='06b1e2956ebcbcc7a9fd4a25b4c6f5b8fbe097340b1e696afab6ab89b39afa86',
            runtime_counters_static_bytes=960,original_GPU_and_IO_schedule_preserved=True),
        fused_compute=component_times(cache),
        fixed_SSD_command_latency_dominance_causally_identified=False,
        effective_path_rate_is_not_raw_SSD_bandwidth=True,
        original_internal_SSD_nominal_raw_GB_s=5.5,
        nominal_spec_source='https://sonyinteractive.com/en/press-releases/2020/playstation-5-launches-this-november-at-399-for-ps5-digital-edition-and-499-for-ps5-with-ultra-hd-blu-ray-disc-drive/',
        nominal_spec_ratio_is_not_device_utilization=True,actual_mount_device_bandwidth_not_measured=True,
        pure_NAND_OS_and_queue_time_not_separated=True,CI_runs=0,production_changed=False)


def markdown(r):
    a,b=r['whole_request_controls'];gpu=r['fused_compute']['groups'];q4=r['exact_Q4_decode'];q2=r['exact_Q2_decode']
    table='\n'.join(f"| {v['format']} | {v['whole_request_physical_GB']:.6f} | {v['whole_request_read_calls']:,.0f} | {v['physical_GB_per_evaluated_token_including_prompt_EOS']:.6f} | {v['read_calls_per_evaluated_token_including_prompt_EOS']:.3f} | {v['amortized_producer_wait_ms_per_physical_call']:.6f} | {v['effective_GB_per_producer_wait_second']:.6f} |"for v in (a,b))
    compute='\n'.join(f"| {v['role']} | {v['Q4']['compute_ms']:.6f} | {v['Q2']['compute_ms']:.6f} | {100*(v['Q2_over_Q4_wall_ratio']-1):+.3f}% |"for v in gpu)
    phase=(f"Fresh case {q2['case']} completed: physical {q2['physical_GB_per_decode_token']:.6f} GB/decode token, "
        f"{q2['read_calls_per_decode_token']:.3f} physical calls/decode token, "
        f"mean individual pread wall {q2['mean_individual_pread_wall_ms']:.6f} ms. "
        f"Physical bytes decreased {100*q2['physical_byte_reduction_vs_Q4']:.3f}% and calls "
        f"{100*q2['read_call_reduction_vs_Q4']:.3f}% versus the historical Q4 decode cohort. "
        "Per-call times are entry-to-return wall intervals, including OS/filesystem/queue time, not NAND-only latency."
        if q2 else "Exact Q2 decode-only GB/token, calls/token and individual read latency remain unmeasured. "
        "The dedicated measurement SELF is built and import/roundtrip/safety audited, but automatic approval "
        "review rejected the new console launch pending explicit owner freeze-risk confirmation. "
        "No case launch, GPU work or production change occurred for that attempt.")
    return f'''# Requested Q4 versus all-Q2 I/O and compute measurements

## Completed whole-request comparison

These are positively closed PS5 counting cases 7820 and 8780, with the same
30-token prompt and 22 generated output tokens. Each evaluates 52 model input
tokens including prompt and final EOS evaluation. The normalized columns below
include prefill/EOS; **they are not accepted-decode GB/token or calls/token**.

| Format | Physical GB/request | Calls/request | GB/evaluated token, prompt/EOS included | Calls/evaluated token, prompt/EOS included | Amortized producer wait ms/call | Effective GB/source-wait s |
| --- | --- | --- | --- | --- | --- | --- |
{table}

Whole-request physical bytes decrease **{100*r['whole_request_byte_reduction']:.3f}%**, approximately halving.
Physical read calls decrease **{100*r['whole_request_call_reduction']:.3f}%**, much less than half.
The Expert triplet itself shrinks from 2,764,800 to 1,536,000 bytes, a 44.444%
reduction; metadata means the stored format is not exactly half of Q4.
The larger cache and changed routes also affect actual request traffic.

The mean physical read shrinks from {a['mean_physical_read_KiB']:.2f} to {b['mean_physical_read_KiB']:.2f} KiB.
Producer wait per call changes little while bytes fall sharply. This is
consistent with request/granularity overhead becoming more important at these
compressed sizes. It does not isolate a fixed SSD command delay: runs have
different extents, routing and cache layouts, and two I/O lanes overlap.
Producer wait divided by calls is explicitly an amortized critical-path cost,
not the measured duration of one physical read.

## Exact accepted-decode interval

The existing Q4 diagnostic 8010 measures **{q4['physical_GB_per_decode_token']:.6f} GB/token** and
**{q4['read_calls_per_decode_token']:.3f} calls/token**, using token-1 to token-22
completed-counter differences. Prefill and final EOS are excluded.

{phase}

The new observer records 128-microsecond latency histogram bins and 64-KiB
read-size classes, exact returned bytes/counts and each pread entry-to-return
wall time on both existing lanes. It adds no per-read logs, allocations, GPU
queries, new GPU work, source reads, scheduling changes or modified memory
guards. Static counters occupy 960 bytes. The original independent reader
bytes/calls must match these new counters exactly before results qualify.

## Effective bandwidth and latency diagnosis

Whole-request effective delivery per producer-wait second is
**{a['effective_GB_per_producer_wait_second']:.3f} GB/s for Q4** and **{b['effective_GB_per_producer_wait_second']:.3f} GB/s for Q2**.
Sony specifies 5.5 GB/s raw read bandwidth for the original internal PS5 SSD
([official specification]({r['nominal_spec_source']})). The Q2 software-path ratio is
{100*b['effective_GB_per_producer_wait_second']/5.5:.2f}% of that reference number; it is **not device utilization**.
The actual mount/device sequential throughput has not been measured here.
This path is far below the nominal reference, but physical SSD service, kernel,
filesystem and queue/scheduling costs remain combined. A same-extent,
same-byte-volume request-count intervention at actual compressed sizes is
needed to causally separate fixed request/granularity cost from byte cost.

## Quantized compute, including fused decoding

Existing actual-weight PS5 GPU components provide the following width-one
timings. Q4 case 7560, Gate/Up Q2_K case 8160, and fitted-scale Down Q2_0 case
8600 use layers 0/23/47, ten selected IDs with three unique Experts, independent
own-format F64 references and four timed samples per format/group. Each run
also contains its paired BF16 control. These are historical cohorts.

| Projection | Q4 compute ms | Q2 compute ms | Q2 change |
| --- | --- | --- | --- |
{compute}

These times include the fused quantized matrix graph, host submission,
synchronization and the original completion checkpoint. SSD delivery is timed
separately and excluded. They are not pure GPU timestamps or standalone decode
timings. In the measured width-one path, the shaders unpack/scale weights
inside matrix multiplication, so there is no separate dequantization pass to
time independently in that path. This does not classify every other graph width.
No fused-graph wall-time increase is observed in these finite samples.
Whole-model process time outside source wait also falls from
{a['process_outside_source_wait_s_per_request']:.3f} to {b['process_outside_source_wait_s_per_request']:.3f} s/request,
but that remainder includes CPU/framework work and must not be labeled GPU-only.

Sources: `native/app/expert_q4_fixture.cpp`, `expert_q2k_fixture.cpp` and
`expert_q2_fixture.cpp` implement `compute`/`measure`; the pinned Vulkan
`mul_mat_vec.comp` performs dequantization inside the matrix loop. The complete
model and source proofs remain in the staged-Q2 report. This report performs
no console or network operations and runs no CI. Production is unchanged.
'''


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cache',type=Path,required=True);p.add_argument('--measurement-case',type=int,default=8880)
    p.add_argument('--json',type=Path,required=True);p.add_argument('--markdown',type=Path,required=True)
    a=p.parse_args();r=analyze(a.cache,a.measurement_case)
    a.json.write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8',newline='\n')
    a.markdown.write_text(markdown(r),encoding='utf-8',newline='\n')
    print(json.dumps(dict(existing_measurements_aggregated=True,all_requested_measurements_complete=r['completed'],
        whole_byte_reduction=r['whole_request_byte_reduction'],whole_call_reduction=r['whole_request_call_reduction'],
        extra_PS5_operations=0)))


if __name__=='__main__':main()
