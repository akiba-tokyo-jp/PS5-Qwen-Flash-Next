#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Analyze positively closed PS5 measurements; no console/network operations."""
import argparse,json,math
from pathlib import Path
from expert_q4 import require,record


def load(path):return json.loads(Path(path).read_text(encoding='utf-8'))


def case_summary(cache,number,triplet):
    root=cache/f'hardware-first-generation-{number}'
    v=load(root/'native-model-terminal.private.json');closed=load(root/'restored-complete.private.json')
    require(v['completed'] and v['model_loads']==1 and v['full_F32_continuation_and_routes_passed'] and
        v['all_model_source_device_owners_positively_retired'] and v['device_ledger_live_bytes']==0 and
        closed['completed'] and closed['CPU_title_normally_closed'] and closed['exact_prior_configuration_restored'] and
        closed['full_native_readback_SHA256_identity_EOF_verified'] and not closed['unknown_completion'],
        'Actual positive inference, source/GPU retirement and ordinary close/restoration required')
    evidence=[root/'native-model-terminal.private.json',root/'restored-complete.private.json'];rows=[]
    for a in v['requests']:
        d=a['completed_performance']['delta'];perf=a['completed_performance'];m=a['metrics']
        if number!=8700:
            require(a['counting_quality_passed'] and m['prompt_tokens']==30 and
                bytes(a['output_bytes']).decode('utf-8')=='1, 2, 3, 4, 5, 6, 7, 8',
                'The historical counting comparison must retain the exact prompt length and output')
        p=root/('native-arm'+str(a['ordinal'])+'.routes.private.json');routes=load(p);evidence.append(p)
        require(routes['complete'] and routes['sidecar_written_after_model_and_source_retirement'] and
            routes['pid']==v['pid'] and routes['run_id']==v['run_id'] and routes['ordinal']==a['ordinal'] and
            routes['layers_per_process']==48 and routes['experts_per_token']==10 and routes['experts']==512,
            'Exact completed native route ownership and geometry required')
        evaluated=sum(r['tokens']for r in routes['records'])
        selected=sum(len(r['ids'])for r in routes['records'])
        unique=sum(len(set(r['ids']))for r in routes['records'])
        require(len(routes['records'])==48*d['process_calls'] and selected==10*evaluated and
            selected==routes['selected_indices'] and unique==routes['unique_selected_experts'] and
            unique==routes['cache_hits']+routes['cache_misses'] and evaluated%48==0,
            'Actual ordered routes must reconcile with process and cache counters')
        require(routes['uploaded_bytes']==routes['cache_misses']*triplet and
            d['source_chunks']==d['source_completed_windows'] and perf['source_read_ns_is_producer_wait_time'] and
            perf['worker_times_overlap_consumers'] and not perf['GPU_timestamp_queries'],
            'Expert transfer bytes and non-overlapping producer wait semantics required')
        expert=routes['uploaded_bytes'];other=d['source_bytes']-expert;tokens=evaluated//48
        # This is a measured residual reconciled to the original row geometry,
        # not a new named physical-I/O/time measurement of those CPU rows.
        require(other==tokens*10240,'Whole source payload must reconcile to Expert uploads and original CPU rows')
        process=d['process_ns']/1e9;wait=d['source_read_ns']/1e9;wall=m['total_ms']/1000;decode=m['decode_ms']/1000
        categories={k:d[k]/1e9 for k in ('source_headroom_ns','source_handle_ns','source_read_ns','source_consumer_ns')}
        transitions=max(0,m['generated_tokens']-1)
        rate_ok=(decode==0 and m['decode_tokens_per_second'] is None) if not transitions else (
            decode>0 and math.isclose(transitions/decode,m['decode_tokens_per_second'],rel_tol=1e-9))
        require(0<wait<process<wall and sum(categories.values())<=process and 0<=decode<wall and rate_ok,
            f'Nested whole-request timers and accepted-decode rate must agree: {number}/{a["ordinal"]}')
        physical=d['source_physical_read_bytes'];calls=d['source_physical_read_calls']
        rows.append(dict(ordinal=a['ordinal'],task=a.get('quality_case'),decode_tok_s=m['decode_tokens_per_second'],
            generated_tokens=m['generated_tokens'],accepted_decode_transitions=transitions,
            decode_s=decode,TTFT_s=m['TTFT_ms']/1000,total_request_s=wall,model_process_s=process,
            whole_request_source_wait_s=wait,whole_request_wait_fraction_of_process=wait/process,
            whole_request_wait_fraction_of_wall=wait/wall,source_categories_s=categories,
            process_outside_profiled_source_categories_s=process-sum(categories.values()),
            whole_request_physical_bytes=physical,whole_request_physical_calls=calls,
            mean_physical_request_KiB=physical/calls/1024,effective_physical_GB_per_producer_wait_s=physical/wait/1e9,
            logical_source_bytes=d['source_bytes'],Expert_uploaded_bytes=expert,
            non_Expert_logical_residual_bytes=other,non_Expert_residual_bytes_per_evaluated_token=other/tokens,
            Expert_fraction_of_logical_payload=expert/d['source_bytes'],alignment_and_envelope_extra_bytes=physical-d['source_bytes'],
            evaluated_model_tokens=tokens,cache_hits=routes['cache_hits'],cache_misses=routes['cache_misses'],
            cache_miss_fraction_of_unique_demands=routes['cache_misses']/unique,
            duplicate_selections_removed_within_batches=selected-unique,
            exact_decode_source_wait_measured=False,
            # W lies inside T; decode occupies a subinterval D. At most T-D
            # seconds of W can lie outside decode. This gives a bound, not
            # the unavailable token-boundary source counter differences.
            decode_source_wait_lower_bound_s=max(0,wait-(wall-decode))))
    timed=rows[1:] if len(rows)==3 else rows
    sums=lambda key:sum(r[key]for r in timed)
    pooled=dict(decode_tok_s=sums('accepted_decode_transitions')/sums('decode_s'),
        whole_request_wait_fraction_of_process=sums('whole_request_source_wait_s')/sums('model_process_s'),
        whole_request_wait_fraction_of_wall=sums('whole_request_source_wait_s')/sums('total_request_s'),
        Expert_fraction_of_logical_payload=sums('Expert_uploaded_bytes')/sums('logical_source_bytes'),
        cache_miss_fraction_of_unique_demands=sums('cache_misses')/(sums('cache_misses')+sums('cache_hits')),
        decode_source_wait_fraction_lower_bound=sums('decode_source_wait_lower_bound_s')/sums('decode_s'))
    return dict(case=number,Expert_format=v.get('Expert_format','Q4_0'),active_cache_slots=v['active_cache_slots'],
        SELF_sha256=v['candidate_SELF_sha256'],model_receipt_sha256=v['model_receipt_sha256'],
        source_GPU_retirement_and_normal_close_verified=True,requests=rows,pooled=pooled),evidence


def analyze(cache):
    cases=[];evidence=[]
    for number,triplet in ((7820,2764800),(8440,1996800),(8780,1536000),(8700,1536000)):
        v,files=case_summary(cache,number,triplet);cases.append(v);evidence+=files
    q4,mixed,current,quality=cases
    receipt=cache/'Expert-all-Q2-receipt-8652.json';model=load(receipt);evidence.append(receipt)
    require(record(receipt)['sha256']==current['model_receipt_sha256']==quality['model_receipt_sha256'],
        'The actual all-Q2 receipt must match both completed native cases')
    require(all(r['generated_tokens']==22 and r['accepted_decode_transitions']==21 for c in cases[:3]for r in c['requests']),
        'Historical counting controls must use the same accepted output length')
    non=[t for t in model['tensors']if t['type']not in ('Q2_K','Q2_0')];names={t['name']:t for t in non}
    fixture=load(cache/'hardware-first-generation-8780/native.resident.GPU-upload-fixture.private.json')
    loaded=load(cache/'hardware-first-generation-8780/native.resident.GPU-upload-loaded.private.json')
    inventory=dict(stored_non_Expert_bytes=sum(t['bytes']for t in non),
        PLE_table_bytes=names['per_layer_token_embd.weight']['bytes'],token_embedding_bytes=names['token_embd.weight']['bytes'],
        output_projection_bytes=names['output.weight']['bytes'],
        one_time_model_upload_bytes=loaded['completed_copy_bytes']-fixture['completed_copy_bytes'])
    return dict(schema='ps5-qwen-all-Q2-bottleneck-v1',completed=True,new_console_launches=0,new_GPU_work=0,
        production_changed=False,CI_runs=0,method='Read-only reconciliation of positively closed native counters, routes and actual model receipt',
        primary_measurement_case=8780,historical_controls_are_not_simultaneous_ABBA=True,
        exact_decode_source_counter_split_available=False,worker_times_not_added=True,
        current=current,historical_controls=[q4,mixed],additional_quality_requests=quality,non_Expert_inventory=inventory,
        conclusion='Expert payload streaming and producer I/O waiting remain dominant after all-Expert Q2',
        separate_SSD_NAND_OS_or_fixed_call_latency_cause_proven=False,
        current_non_Expert_physical_bytes_and_wait_separately_measured=False,
        evidence=[dict(bytes=r['bytes'],sha256=r['sha256'])for r in (record(p)for p in dict.fromkeys(evidence))],
        limitations=['Whole-request source counters include prefill and final EOS; decode rate excludes them.',
            'The decode wait fraction is a conservative timer bound, not a newly measured exact split.',
            'Non-Expert logical residual is exact; its physical bytes and wait are not separately instrumented in this candidate.',
            'Producer I/O wait includes filesystem/kernel/scheduling; effective delivery is not raw SSD bandwidth.',
            'Source-consumer and process remainders are not pure GPU timestamps.',
            'Only finite counting and three repeated fixed quality prompts were measured; normal all-Q2 application qualification remains pending.'])


def markdown(r):
    cur=r['current'];pool=cur['pooled'];timed=cur['requests'][1:]
    table='\n'.join(f"| {a['ordinal']} | {a['decode_tok_s']:.6f} | {a['model_process_s']:.3f} | {a['whole_request_source_wait_s']:.3f} | {100*a['whole_request_wait_fraction_of_process']:.2f}% | {a['whole_request_physical_bytes']/1e9:.6f} | {a['whole_request_physical_calls']:,} |"for a in timed)
    comparison='\n'.join(f"| {c['Expert_format']} | {c['active_cache_slots']} | {c['pooled']['decode_tok_s']:.6f} | {100*c['pooled']['whole_request_wait_fraction_of_process']:.2f}% | {c['requests'][1]['whole_request_physical_bytes']/1e9:.6f} | {100*c['pooled']['cache_miss_fraction_of_unique_demands']:.2f}% |"for c in r['historical_controls']+[cur])
    a=timed[0];cat=a['source_categories_s'];inventory=r['non_Expert_inventory']
    mixed=r['historical_controls'][1];old=mixed['requests'][1]
    return f'''# All-Expert Q2 bottleneck verification

The dominant measured cost remains routed Expert delivery from storage. This
analysis reuses completed PS5 case 8780 and corroborates it with quality case
8700. It starts no helper, title, model or GPU work and changes no production
file. The selected production remains the mixed model; these all-Q2 results
describe the faster tested candidate pending its normal-app qualification.

| Timed request | Decode tok/s | Whole model-process s | Whole source-wait s | Wait / process | Physical GB/request | Physical calls/request |
| --- | --- | --- | --- | --- | --- | --- |
{table}

Pooled source wait occupies **{100*pool['whole_request_wait_fraction_of_process']:.2f}%** of model-process
time and **{100*pool['whole_request_wait_fraction_of_wall']:.2f}%** of complete request wall time. The
whole-request counters include prompt processing and final EOS work. The
**{pool['decode_tok_s']:.6f} decode tok/s** figure instead uses 21 accepted transitions,
excluding prefill and EOS. Do not describe the whole-request wait percentage as
an exact decode-only percentage.

The existing token records do not contain per-token source counters. A
conservative timer bound still proves that at least
**{100*pool['decode_source_wait_fraction_lower_bound']:.2f}% of accepted decode wall time** must be producer
source wait in this cohort: with total wall T, whole source wait W and decode
wall D, decode wait is at least max(0, W - (T - D)). This is a bound derived from
non-overlapping nested producer intervals, not a new exact decode measurement.

## Weight volume and cache

Each timed request reads {a['whole_request_physical_bytes']:,} physical bytes and
requests {a['logical_source_bytes']:,} logical payload bytes. Exactly
{a['Expert_uploaded_bytes']:,} logical bytes reconcile to
{a['cache_misses']:,} Expert cache misses times the 1,536,000-byte triplet.
Expert payload therefore accounts for **{100*pool['Expert_fraction_of_logical_payload']:.6f}%** of logical streaming.
The remaining {a['non_Expert_logical_residual_bytes']:,} bytes equal
{a['evaluated_model_tokens']} evaluated model tokens times the original 10,240-byte
token/PLE row payload. There is no unclassified logical payload.

The 867-slot cache records {a['cache_hits']:,} hits and {a['cache_misses']:,} misses,
a **{100*pool['cache_miss_fraction_of_unique_demands']:.2f}% miss fraction** among unique per-batch demands.
This denominator differs from raw top-10 selections: the batching path already
removes repeated selections within a batch. Physical alignment/envelope overhead
is {a['alignment_and_envelope_extra_bytes']:,} bytes per request. Mean physical request size is
{a['mean_physical_request_KiB']:.2f} KiB. Effective physical bytes per producer wait are
{a['effective_physical_GB_per_producer_wait_s']:.3f} GB/s, including filesystem, kernel and scheduling time.
It does not measure raw NAND/controller bandwidth or isolated per-command latency.

| Historical same-console format | Active slots | Decode tok/s | Whole wait / process | Whole physical GB/request | Unique-demand miss fraction |
| --- | --- | --- | --- | --- | --- |
{comparison}

The counting prompt and 22 generated tokens / 21 accepted transitions match.
Precision, routes and cache representation differ, and controls were collected
earlier. These observations support reduced streaming volume; they are not a
simultaneous ABBA intervention isolating byte volume from cache/route changes.
Relative to the mixed cohort, whole-request physical bytes fall
{100*(1-a['whole_request_physical_bytes']/old['whole_request_physical_bytes']):.2f}% and decode throughput rises
{100*(pool['decode_tok_s']/mixed['pooled']['decode_tok_s']-1):.2f}%. Mean physical requests shrink from
{old['mean_physical_request_KiB']:.2f} KiB to {a['mean_physical_request_KiB']:.2f} KiB, while effective delivery per
producer wait falls from {old['effective_physical_GB_per_producer_wait_s']:.3f} to
{a['effective_physical_GB_per_producer_wait_s']:.3f} GB/s. These observations motivate testing request
granularity and delivery efficiency at the actual compressed sizes; they do not
causally assign the difference to fixed syscall or hardware command latency.

## Other measured costs and non-Expert weights

For timed request 1, source headroom checks total {cat['source_headroom_ns']:.3f} s,
source handle work {cat['source_handle_ns']:.3f} s, and source-consumer intervals
{cat['source_consumer_ns']:.3f} s. After these intervals and source wait,
{a['process_outside_profiled_source_categories_s']:.3f} s remains inside model-process calls.
Neither the consumer interval nor the remainder is a pure GPU/dequantization
measurement. Existing validation/monitoring is retained. Overlapping worker
read times are not added to producer time.

Stored non-Expert tensors total {inventory['stored_non_Expert_bytes']:,} bytes,
including the {inventory['PLE_table_bytes']:,}-byte PLE table and
{inventory['token_embedding_bytes']:,}-byte token embedding. Stored size is not
per-token traffic. The completed model-load upload is
{inventory['one_time_model_upload_bytes']:,} bytes, separately from decode streaming.
Non-Expert logical traffic is tiny; this all-Q2 candidate does not separately
measure its physical-read amplification or wait. Earlier Q4-only percentages
must not be transferred to all-Q2 as new measurements.

## Next optimization targets

1. Reduce Expert cache misses or share already fetched Expert payload across
   useful accepted work; most requested payload remains Expert data.
2. Improve delivery of the remaining miss bytes, including packing, request
   aggregation and real I/O/compute overlap, using a fresh finite comparison.
   The current counters cannot distinguish SSD service from the OS I/O path.
3. Profile GPU dequantization/GEMV separately before treating it as the next
   dominant bottleneck. Shader-only work leaves the measured source wait.
4. Investigate non-Expert resident compression as a way to free Expert-cache
   capacity if desired; it is an indirect hypothesis, not a demonstrated
   reduction of the dominant streaming bytes.

No speed improvement is claimed from this analysis. Normal all-Q2 monitor/API
qualification and final placement remain separate pending work. Driver
872cc1264ad8ba5d6b888b092968fa5858a38c58 / cumulative-idle, disabled persistent
caches, memory/owner/completion guards and all rollbacks remain unchanged.

## Counter and timing definitions

- [Source reader](../native/app/mapped_source.h): `read_window`,
  `read_pair_windows`, `pipeline_windows` and `completed` define producer waits,
  aligned physical envelopes, handle/headroom work and consumer lifetimes.
- [Engine timing](../native/app/llama_engine.cpp): the `llama_process` scope
  encloses source and backend work; synchronization is a separate interval.
- [Request timing](../native/app/first_generation.h): `FirstGeneration::run`
  measures decode from first to last accepted generated token and completes
  final EOS/reset work before recording total request time.
- [Counter aggregation](../native/app/native_main.cpp): `performance_snapshot`
  and `performance_difference` retain producer-wait semantics and explicitly
  identify overlapping worker timings and the absence of GPU timestamps.
- [All-Q2 derivative](../tools/expert_all_q2_model_source.py): `entry_source`
  validates miss bytes against the 1,536,000-byte Expert triplet.

Reproduce with `tools/analyze_expert_q2_bottleneck.py --cache <private-data-root>
--json docs/expert-q2-bottleneck-20261029.json --markdown
docs/expert-q2-bottleneck-20261029.md`. The JSON binds whole captured evidence
digests without publishing private paths, endpoints, PID or run bindings.
'''


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('cache','json','markdown'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();result=analyze(a.cache)
    a.json.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    a.markdown.write_text(markdown(result),encoding='utf-8',newline='\n')
    print(json.dumps(dict(completed=True,PS5_operations=0,**result['current']['pooled'])))


if __name__=='__main__':main()
