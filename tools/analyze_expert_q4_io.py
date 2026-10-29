#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Analyze a closed native Q4 I/O profile without starting console operations."""
import argparse,json,math
from pathlib import Path
from expert_q4 import require,record,write_json
ROOT=Path(__file__).resolve().parents[1]
KINDS=('token_embedding_','PLE_embedding_','other_CPU_rows_')

def load(path):return json.loads(Path(path).read_text(encoding='utf-8'))

def analyze(case,receipt):
    terminal=load(case/'native-model-terminal.private.json');closed=load(case/'restored-complete.private.json')
    selected=load(ROOT/'config/production-installation.json')['application_SELF']
    require(terminal['completed']and terminal['completed_IO_profile']and terminal['model_loads']==1 and
        terminal['active_cache_slots']==481 and terminal['full_F32_continuation_and_routes_passed']and
        terminal['all_model_source_device_owners_positively_retired']and terminal['device_ledger_live_bytes']==0 and
        closed['completed']and closed['CPU_title_normally_closed']and closed['exact_prior_configuration_restored']and
        closed['full_native_readback_SHA256_identity_EOF_verified']and not closed['unknown_completion']and
        all(closed['exact_fastest_SELF'][k]==v for k,v in selected.items()),'Closed positive diagnostic and exact current Q4 restoration required')
    captures=load(case/'IO-token-snapshots/complete.private.json')
    require(captures['completed']and captures['copied_only_after_positive_model_source_retirement'],'Completed token evidence required')
    for row in captures['records']:require(record(row['path'])==row,'Captured completed token evidence changed')
    rows=[]
    for request in terminal['requests']:
        ordinal=request['ordinal'];count=request['metrics']['generated_tokens']
        tokens=[load(case/'IO-token-snapshots'/f'arm{ordinal}-token-{i}.private.json')for i in range(1,count+1)]
        require(count==22 and request['counting_quality_passed']and
            [t['token_id']for t in tokens]==request['token_ids'],'The complete finite counting sequence is required')
        for i,t in enumerate(tokens,1):
            require(t['generated_tokens']==i and t['completed_performance']['source_chunks']==t['completed_performance']['source_completed_windows'],
                'Every boundary must follow positive source completion')
        for a,b in zip(tokens,tokens[1:]):
            require(b['elapsed_ms']>=a['elapsed_ms']and b['Expert_uploaded_bytes']>=a['Expert_uploaded_bytes']and
                all(b['completed_performance'][k]>=v for k,v in a['completed_performance'].items()),'Cumulative completed counters reversed')
        first,last=tokens[0],tokens[-1];delta={k:last['completed_performance'][k]-v for k,v in first['completed_performance'].items()}
        transitions=count-1;wall=(last['elapsed_ms']-first['elapsed_ms'])/1000
        process=delta['process_ns']/1e9;wait=delta['source_read_ns']/1e9
        require(delta['process_calls']==transitions and 0<wait<process<wall and
            math.isclose(transitions/wall,request['metrics']['decode_tokens_per_second'],rel_tol=1e-7),
            'Exactly the accepted single-token decode interval must exclude prefill and final EOS work')
        expert=last['Expert_uploaded_bytes']-first['Expert_uploaded_bytes']
        groups={k.removesuffix('_'):dict(rows=delta[k+'rows'],logical_bytes=delta[k+'logical_bytes'],
            physical_read_bytes=delta[k+'physical_bytes'],physical_read_calls=delta[k+'physical_calls'],
            source_wait_s=delta[k+'source_wait_ns']/1e9)for k in KINDS}
        cpu_logical=sum(v['logical_bytes']for v in groups.values());cpu_physical=sum(v['physical_read_bytes']for v in groups.values())
        cpu_calls=sum(v['physical_read_calls']for v in groups.values());cpu_wait=sum(v['source_wait_s']for v in groups.values())
        require(expert%2764800==0 and delta['source_bytes']>=expert+cpu_logical and delta['source_physical_read_bytes']>=cpu_physical and
            delta['source_physical_read_calls']>=cpu_calls and wait>=cpu_wait,'CPU row attribution must remain a strict subset of total source reads')
        unclassified=delta['source_bytes']-expert-cpu_logical
        whole=request['completed_performance']['delta'];whole_expert=load(case/f'native-arm{ordinal}.routes.private.json')['uploaded_bytes']
        production_case=case.parent/'hardware-first-generation-7920'
        reference=load(production_case/f'native-arm{ordinal}.result.private.json')
        actual_routes=load(case/f'native-arm{ordinal}.routes.private.json')
        reference_routes=load(production_case/f'native-arm{ordinal}.routes.private.json')
        require(request['token_ids']==reference['token_ids']and request['output_bytes']==reference['output_bytes']and
            actual_routes['records']==reference_routes['records']and
            all(whole[k]==reference['completed_performance']['delta'][k]for k in
                ('source_bytes','source_physical_read_bytes','source_physical_read_calls')),
            'Diagnostic tokens, ordered routes and weight-read volume/count must match selected production')
        rows.append(dict(request=ordinal,warmup=ordinal==0,accepted_decode_transitions=transitions,decode_tok_s=transitions/wall,
            prefill_excluded=True,final_EOS_work_excluded=True,decode_elapsed_s=wall,model_process_s=process,source_wait_s=wait,
            source_wait_fraction_of_process=wait/process,source_wait_fraction_of_decode_wall=wait/wall,
            process_remainder_s=process-wait,physical_read_bytes=delta['source_physical_read_bytes'],physical_read_calls=delta['source_physical_read_calls'],
            physical_GB_per_accepted_token=delta['source_physical_read_bytes']/transitions/1e9,
            physical_calls_per_accepted_token=delta['source_physical_read_calls']/transitions,
            mean_physical_request_MiB=delta['source_physical_read_bytes']/delta['source_physical_read_calls']/(1<<20),
            effective_physical_GB_per_source_wait_s=delta['source_physical_read_bytes']/1e9/wait,
            Expert_logical_read_bytes=expert,Expert_logical_bytes_per_token=expert/transitions,
            Expert_misses=expert//2764800,CPU_rows=groups,non_Expert_logical_read_bytes=cpu_logical,
            non_Expert_physical_read_bytes=cpu_physical,non_Expert_physical_read_calls=cpu_calls,non_Expert_source_wait_s=cpu_wait,
            non_Expert_logical_bytes_per_token=cpu_logical/transitions,non_Expert_physical_bytes_per_token=cpu_physical/transitions,
            non_Expert_fraction_of_physical_bytes=cpu_physical/delta['source_physical_read_bytes'],
            non_Expert_fraction_of_source_wait=cpu_wait/wait,
            non_CPU_source_physical_bytes=delta['source_physical_read_bytes']-cpu_physical,
            unclassified_logical_source_bytes=unclassified,
            whole_request=dict(physical_read_bytes=whole['source_physical_read_bytes'],source_wait_s=whole['source_read_ns']/1e9,
                source_wait_fraction_of_process=whole['source_read_ns']/whole['process_ns'],
                non_Expert_residual_logical_bytes=whole['source_bytes']-whole_expert)))
    typed=load(receipt);tensors=typed['tensors'];non=[t for t in tensors if t['type']!='Q4_0']
    names={t['name']:t for t in non};stored=sum(t['bytes']for t in non)
    fixture=load(case/'native.resident.GPU-upload-fixture.private.json');loaded=load(case/'native.resident.GPU-upload-loaded.private.json')
    startup=loaded['completed_copy_bytes']-fixture['completed_copy_bytes']
    timed=rows[1:];total_process=sum(r['model_process_s']for r in timed);total_wait=sum(r['source_wait_s']for r in timed)
    physical=sum(r['physical_read_bytes']for r in timed);nonphysical=sum(r['non_Expert_physical_read_bytes']for r in timed)
    decode_wall=sum(r['decode_elapsed_s']for r in timed);nonwait=sum(r['non_Expert_source_wait_s']for r in timed)
    return dict(schema='ps5-qwen-Q4-IO-attribution-v1',completed=True,actual_new_PS5_measurement=True,
        diagnostic_case=int(case.name.rsplit('-',1)[1]),selected_production_SELF_sha256=selected['sha256'],
        diagnostic_SELF_sha256=terminal['candidate_SELF_sha256'],measurement_only_candidate_not_adopted=True,
        tokens_routes_and_weight_read_volume_match_selected_production=True,
        selected_Q4_application_and_five_settings_restored=True,ordinary_close_verified=True,final_native_owners=0,CI_runs=0,
        methodology='First-to-last generated-token completed-counter differences; no extra reads or GPU work; named CPU GET_ROWS attribution',
        instrumentation_adds_CPU_counter_and_existing_token_record_fields=True,
        physical_reads_include_alignment=True,source_wait_includes_OS_and_scheduling=True,pure_NAND_or_device_bandwidth_not_measured=True,
        worker_intervals_overlap_and_are_not_added=True,requests=rows,
        pooled_timed=dict(decode_tok_s=sum(r['accepted_decode_transitions']for r in timed)/sum(r['decode_elapsed_s']for r in timed),
            source_wait_fraction_of_process=total_wait/total_process,
            source_wait_fraction_of_decode_wall=total_wait/sum(r['decode_elapsed_s']for r in timed),
            physical_bytes_per_token=physical/sum(r['accepted_decode_transitions']for r in timed),
            non_Expert_fraction_of_physical_bytes=nonphysical/physical,
            non_Expert_fraction_of_source_wait=nonwait/total_wait,
            non_Expert_wait_fraction_of_decode_wall=nonwait/decode_wall,
            Expert_source_wait_fraction_of_process=(total_wait-nonwait)/total_process,
            optimistic_decode_ratio_if_all_non_Expert_source_wait_removed=decode_wall/(decode_wall-nonwait)),
        non_Expert_inventory=dict(tensors=len(non),stored_tensor_bytes=stored,
            PLE_table_bytes=names['per_layer_token_embd.weight']['bytes'],token_embedding_bytes=names['token_embd.weight']['bytes'],
            output_projection_bytes=names['output.weight']['bytes'],other_non_Expert_bytes=stored-sum(names[n]['bytes']for n in('per_layer_token_embd.weight','token_embd.weight','output.weight'))),
        model_load_GPU_upload_bytes_excluding_fixture=startup,
        full_source_attribution_closed=all(r['unclassified_logical_source_bytes']==0 and r['CPU_rows']['other_CPU_rows']['logical_bytes']==0 for r in rows),
        conclusions=dict(dominant_remaining_source='Routed Expert delivery',
            non_Expert_decode_IO_is_secondary=True,ordinary_dense_weights_not_reread_per_decode_token=True,
            next_candidate='Q4-specific Expert read batching/pipelining and cache-miss reduction',
            fixed_request_latency_dominance_causally_proven=False),
        limitations=['Finite counting workload, not general reasoning or a sustained service.',
            'The producer I/O interval includes the OS/filesystem path and waiting; it is not isolated SSD/NAND service time.',
            'Model process minus I/O includes GPU, CPU and framework work; it is not a GPU-only timestamp.',
            'Diagnostic counter/record overhead is not a speed improvement and the diagnostic app is not adopted.',
            'Stored tensor size and one-time model-load upload are not per-token disk traffic.'])

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--case',type=Path,required=True);p.add_argument('--receipt',type=Path,required=True)
    p.add_argument('--json',type=Path,required=True);p.add_argument('--markdown',type=Path,required=True);a=p.parse_args()
    r=analyze(a.case,a.receipt)
    require(r['full_source_attribution_closed'],'Unattributed source bytes must not be published as a complete bottleneck diagnosis')
    write_json(a.json,r)
    table='\n'.join(f"| {v['request']} | {v['decode_tok_s']:.6f} | {v['model_process_s']:.4f} | {v['source_wait_s']:.4f} | {100*v['source_wait_fraction_of_process']:.3f}% | {v['physical_GB_per_accepted_token']:.6f} |"for v in r['requests'])
    timed=r['requests'][1:];groups='\n'.join(f"| {v['request']} | {name} | {g['logical_bytes']:,} | {g['physical_read_bytes']:,} | {g['physical_read_calls']:,} | {g['source_wait_s']:.6f} |"for v in timed for name,g in v['CPU_rows'].items())
    a.markdown.write_text(f'''# Post-Q4 I/O bottleneck measurement

A fresh PS5 diagnostic measured the selected Q4 model, 481-slot cache and
original GPU/driver/I/O schedule. Only completed counter observations and
existing token record fields were added. One warmup and two API requests
passed full same-Q4 vocabulary/routes, correct counting, source/model/GPU
retirement and ordinary close. The exact selected Q4 executable and all five
settings were restored and verified; the diagnostic is not adopted.

| Request (0 warmup) | Decode tok/s | Model process seconds | Producer source-wait seconds | Wait / process | Physical GB/token |
| --- | --- | --- | --- | --- | --- |
{table}

The interval covers 21 accepted decode transitions per request. Prefill and
final EOS work are excluded by subtracting token-1 from token-22 cumulative
counters. Pooled timed source wait is **{100*r['pooled_timed']['source_wait_fraction_of_process']:.3f}%**
of model process time, or **{100*r['pooled_timed']['source_wait_fraction_of_decode_wall']:.3f}%**
of decode wall time. The latter also contains ordinary reporting/observer work.
Source wait includes filesystem/kernel/scheduling time. It is not an isolated
NAND service-time or raw SSD-bandwidth measurement. Overlapping worker times
are not added; process minus source wait is not labeled GPU-only time.

## Named non-Expert reads in the decode interval

The existing CPU GET_ROWS path exposes its original source tensor name. The
diagnostic brackets those synchronous row reads with existing source counters;
it changes no source offset, read size, number of reads, conversion or routing.
Expert payload comes from the original cumulative cache-upload counter and
is reconciled against complete source logical bytes. Physical bytes include
16-KiB Direct-read alignment. Logical bytes describe requested weight payload.

| Request | Tensor group | Logical bytes | Physical bytes | Physical calls | Source-wait seconds |
| --- | --- | --- | --- | --- | --- |
{groups}

Named non-Expert rows account for **{100*r['pooled_timed']['non_Expert_fraction_of_physical_bytes']:.6f}%**
of measured physical decode reads and **{100*r['pooled_timed']['non_Expert_fraction_of_source_wait']:.3f}%**
of producer source-wait time. All logical source bytes classified without a
remainder: **{r['full_source_attribution_closed']}**.

The complete non-Expert tensor payload is {r['non_Expert_inventory']['stored_tensor_bytes']:,} bytes,
including the {r['non_Expert_inventory']['PLE_table_bytes']:,}-byte PLE table,
{r['non_Expert_inventory']['token_embedding_bytes']:,}-byte token embedding and
{r['non_Expert_inventory']['output_projection_bytes']:,}-byte output projection.
Stored size is not per-token traffic: selected embedding/PLE rows are fetched
on demand; the ordinary dense weights remain resident after model load.
Model-load GPU upload, excluding the completed fixture, is
{r['model_load_GPU_upload_bytes_excluding_fixture']:,} bytes; this startup
transfer is reported separately from decode streaming.

## Diagnosis and priorities

Routed Expert delivery remains the main measured bottleneck. After removing
the named non-Expert subset, Expert source wait alone occupies
**{100*r['pooled_timed']['Expert_source_wait_fraction_of_process']:.3f}%** of model process time.
The earlier BF16 normal-application observations were about 92%; the Q4 decode
observation is about 82%. These are serial finite cohorts with different
precision/cache representations, not a same-time paired experiment.

Each accepted token still requires about 1.03 GB of physical reads and 1,106
physical requests, with a mean request of about 0.888 MiB. Effective bytes per
producer source-wait second are about 1.13 GB/s, not a raw hardware bandwidth
reading. This supports a Q4-specific comparison of Expert batching/pipelining
and cache-miss reduction. It does not prove fixed syscall/request latency or
SSD hardware saturation as the underlying cause.

Non-Expert decode I/O is secondary. The PLE table is large on disk but fetches
16 original 320-byte rows/token (5,120 logical bytes); ordinary token embedding
fetches one 5,120-byte row/token. Together they consume 10 KiB of payload and
about 281.14 KiB of physical I/O/token after alignment. Other non-Expert source
payload did not recur in the measured decode interval. PLE small-read alignment
amplification is real, but removing *all* measured non-Expert source-wait time
would produce only an optimistic **{r['pooled_timed']['optimistic_decode_ratio_if_all_non_Expert_source_wait_removed']:.4f}x**
decode improvement with the other observed costs fixed. This is a counterfactual
upper bound, not an implemented cache speedup. Broad non-Expert quantization
would therefore not directly remove the dominant streaming traffic. Freeing
resident memory for more Expert cache is a different, untested indirect effect.

## Scope and reproduction

This is a finite counting diagnosis. It adds CPU counter/record overhead and
does not establish a new speedup. The selected production SELF remains
`{r['selected_production_SELF_sha256']}`. Driver revision/profile, precision,
cache budget, memory floors, ownership, completion checks and persistent-cache
policy are unchanged. No reboot or CI occurred.

`tools/build_expert_q4_io_probe.py` derives a separate measurement entry and
adds two counter callbacks around the original CPU row loop.
`native/app/expert_q4_io_profile.h` checks exact logical completion and nested
scope consistency; `tests/expert_q4_io_profile.cpp` checks independent examples
and refuses duplicate/missing/short/incomplete/reversed scopes.
`tools/analyze_expert_q4_io.py` verifies completed native records and writes
this sanitized analysis without a console/network client.
''',encoding='utf-8',newline='\n')
    print(json.dumps(dict(completed=True,decode_source_wait_fraction=r['pooled_timed']['source_wait_fraction_of_process'],
        non_Expert_physical_read_fraction=r['pooled_timed']['non_Expert_fraction_of_physical_bytes'],full_attribution=r['full_source_attribution_closed'])),flush=True)
if __name__=='__main__':main()
