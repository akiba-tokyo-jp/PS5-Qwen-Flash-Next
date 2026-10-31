#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reconcile the installed finite normal cohort and replay its frozen cache on the host."""
import argparse,collections,hashlib,json,math,os,statistics,subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
TRIPLET=1536000

def need(ok,message):
    if not ok:raise ValueError(message)

def load(path):return json.loads(Path(path).read_text(encoding='utf-8'))

def fingerprint(path):
    path=Path(path)
    return dict(bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest())

def save(path,value):Path(path).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')

def quantile(values,probability):return sorted(values)[math.ceil(len(values)*probability)-1]

def latency(row):
    timing=row['cold_request_timing'];a=timing['read_latency_delta'];d=row['completed_performance']['delta']
    need(len(a)==120 and a[3]==0 and a[0]==d['source_physical_read_calls'] and a[1]==d['source_physical_read_bytes'],
         'Every physical call and byte must reconcile with independent syscall counters')
    histogram=a[4:69];need(sum(histogram)==a[0],'Complete latency histogram required')
    quantiles={}
    for q in (.5,.95,.99):
        rank=math.ceil(q*a[0]);seen=0
        for i,count in enumerate(histogram):
            seen+=count
            if seen>=rank:
                quantiles[f'P{int(q*100)}']=dict(lower_ms=i*timing['read_latency_bin_ns']/1e6,
                    upper_ms=(i+1)*timing['read_latency_bin_ns']/1e6 if i<64 else None);break
    sizes=[]
    for i in range(17):
        calls,bytes_,ns=a[69+3*i:72+3*i]
        if calls:sizes.append(dict(bucket=i,lower_KiB=i*64,upper_KiB=(i+1)*64 if i<16 else None,
            calls=calls,bytes=bytes_,mean_KiB=bytes_/calls/1024,mean_syscall_wall_ms=ns/calls/1e6,
            fraction_of_summed_syscall_wall=ns/a[2]))
    need(sum(x['calls']for x in sizes)==a[0] and sum(x['bytes']for x in sizes)==a[1], 'Complete size classes required')
    return dict(calls=a[0],bytes=a[1],mean_individual_syscall_wall_ms=a[2]/a[0]/1e6,quantiles=quantiles,size_classes=sizes,
        mean_request_KiB=a[1]/a[0]/1024,summed_overlapping_syscall_wall_s=a[2]/1e9,
        mean_API_inflight_over_model_process=a[2]/d['process_ns'],
        busy_period_only_concurrency_measured=False,hardware_SSD_queue_or_NAND_latency_measured=False,
        latency_quantiles_include_prefill_and_EOS=True)

def token_analysis(root,row):
    ordinal=row['ordinal'];events=[]
    for line in (root/'passive-observer'/f'request-{ordinal}.stream.private.log').read_text().splitlines():
        if line.startswith('data:'):events.append(json.loads(line[5:].strip()))
    points=[e for e in events if e['type']=='token'];n=row['metrics']['generated_tokens']
    need(len(points)==n and [e['token_id']for e in points]==row['token_ids'] and events[-1]['type']=='finished',
         'Complete native token stream required')
    intervals=[]
    for a,b in zip(points,points[1:]):
        c={k:b['expert_cache'][k]-a['expert_cache'][k]for k in ('hits','misses','uploaded_bytes')}
        need(all(v>=0 for v in c.values()) and c['uploaded_bytes']==c['misses']*TRIPLET,'Token counters must be monotonic and byte-exact')
        intervals.append(dict(output_ordinal=b['ordinal'],elapsed_ms=b['elapsed_ms']-a['elapsed_ms'],**c))
    elapsed=[x['elapsed_ms']for x in intervals];misses=sum(x['misses']for x in intervals);hits=sum(x['hits']for x in intervals)
    need(math.isclose(sum(elapsed),row['metrics']['decode_ms'],rel_tol=1e-9), 'Decode excludes prefill and final EOS')
    out=dict(accepted_decode_transitions=n-1,decode_ms=sum(elapsed),mean_intertoken_ms=statistics.mean(elapsed),
        median_intertoken_ms=statistics.median(elapsed),P95_intertoken_ms=quantile(elapsed,.95),maximum_intertoken_ms=max(elapsed),
        cache_hits=hits,cache_misses=misses,cache_miss_fraction=misses/(hits+misses),
        logical_Expert_GB_per_accepted_decode_transition=misses*TRIPLET/(n-1)/1e9,
        physical_decode_bytes_and_call_counts_measured=False,exact_decode_source_wait_measured=False,intervals=intervals)
    if not row['speculation']['attempts']:
        xs=[x['misses']for x in intervals];ys=elapsed;xm=statistics.mean(xs);ym=statistics.mean(ys)
        slope=sum((x-xm)*(y-ym)for x,y in zip(xs,ys))/sum((x-xm)**2 for x in xs)
        intercept=ym-slope*xm;corr=statistics.correlation(xs,ys)
        out['observational_miss_latency_fit']=dict(samples=len(xs),correlation=corr,R_squared=corr*corr,
            ms_per_additional_miss=slope,intercept_ms=intercept,causal_SSD_latency_or_GPU_compute_isolated=False,
            hypothetical_half_miss_tok_s=1000/(intercept+slope*xm/2),hypothetical_quarter_miss_reduction_tok_s=1000/(intercept+slope*xm*.75))
    else:
        bonus=[x for x in intervals if x['hits']==x['misses']==0]
        out['zero_new_Expert_demand_intervals']=dict(count=len(bonus),total_ms=sum(x['elapsed_ms']for x in bonus),
            mean_ms=statistics.mean(x['elapsed_ms']for x in bonus),individual_ms=[x['elapsed_ms']for x in bonus])
    return out

def accepted_phase_bounds(root,terminal,traces,fills):
    """Bind route groups to emitted-token counters, including speculative EOS work."""
    bounds=[];base_hits=base_misses=0
    for row,trace,fill in zip(terminal['requests'],traces,fills):
        n=trace['process_calls'];groups=[fill['records'][i:i+48]for i in range(0,len(fill['records']),48)]
        cumulative=[(0,0)];hits=misses=0
        for group in groups:
            hits+=sum(x['hits']for x in group);misses+=sum(len(x['misses'])for x in group)
            cumulative.append((hits,misses))
        if row['ordinal']:
            events=[json.loads(s[5:].strip())for s in(root/'passive-observer'/f"request-{row['ordinal']}.stream.private.log").read_text().splitlines()if s.startswith('data:')]
            points=[p for p in events if p['type']=='token']
            positions=[]
            for point in points:
                c=point['expert_cache'];key=(c['hits']-base_hits,c['misses']-base_misses)
                need(key in cumulative,'Every emitted-token cache snapshot must match a completed process boundary')
                positions.append(cumulative.index(key))
            start,end=positions[0],positions[-1]
        else:
            need(not row['speculation']['attempts'] and n==row['metrics']['generated_tokens']+1,
                 'Cold boundary inference requires one prefill, ordinary decode and one EOS process')
            start,end=1,n-1
        need(0<=start<end<n,'A complete accepted-decode and EOS boundary is required')
        bounds.append(dict(before_first_token_processes=start,through_last_token_processes=end,
            accepted_decode_processes=end-start,after_last_token_processes=n-end))
        base_hits+=trace['cache_hits'];base_misses+=trace['cache_misses']
    return bounds

def replay_geometry(traces,fills,bounds):
    output=[];prior_demands=set();previous_decode=set()
    for trace,fill,bound in zip(traces,fills,bounds):
        ordinal=trace['ordinal'];records=trace['records'];n=trace['process_calls']
        need(len(records)==len(fill['records'])==48*n,'Every process must have48 route rows')
        missed=collections.Counter();demands=collections.Counter();phases={p:collections.Counter()for p in ('prefill','decode','EOS')}
        seen_earlier_request=0;decode_demands=set();request_seen=set()
        for index,(r,f)in enumerate(zip(records,fill['records'])):
            need(r['layer']==index%48 and r['layer']==f['layer'],'Original layer order required')
            group=index//48
            stage='prefill'if group<bound['before_first_token_processes']else'decode'if group<bound['through_last_token_processes']else'EOS'
            keys={(r['layer'],expert)for expert in r['ids']};demands.update(keys);request_seen.update(keys)
            if stage=='decode':decode_demands.update(layer*512+expert for layer,expert in keys)
            for item in f['misses']:
                key=(r['layer'],item['expert']);missed[key]+=1;phases[stage][key]+=1
                seen_earlier_request+=int(key in prior_demands)
        need(sum(missed.values())==trace['cache_misses'] and sum(demands.values())==trace['unique_selected_experts'],
             'Replayed native miss and demand counters differ')
        total=sum(missed.values());layer_rows=[]
        for layer in range(48):
            count=sum(v for(k,e),v in missed.items()if k==layer);demand=sum(v for(k,e),v in demands.items()if k==layer)
            layer_rows.append(dict(layer=layer,misses=count,demands=demand,miss_fraction=count/demand,
                decode_misses=sum(v for(k,e),v in phases['decode'].items()if k==layer)))
        initial={x for x in fill['initial_residents']if x>=0};first={x for x in fill['after_process_residents'][0]if x>=0}
        lost=(initial-first)&decode_demands
        output.append(dict(ordinal=ordinal,cache_hits=trace['cache_hits'],cache_misses=total,
            cache_miss_fraction=total/(trace['cache_hits']+total),phase_misses={k:sum(v.values())for k,v in phases.items()},
            misses_for_Experts_seen_in_earlier_requests=seen_earlier_request,
            unique_decode_Expert_keys=len(decode_demands),occupied_slots_after_request=fill['occupied_slots'],
            initial_cached_future_decode_keys=len(initial&decode_demands),after_first_process_cached_future_decode_keys=len(first&decode_demands),
            prefill_evicted_future_decode_keys=len(lost)if ordinal<2 else None,
            prefill_evicted_previous_decode_keys_used_again=len(lost&previous_decode)if ordinal<2 else None,
            future_decode_overlap_is_retrospective_not_an_online_predictor=True,
            top_four_layer_miss_share=sum(x['misses']for x in sorted(layer_rows,key=lambda x:x['misses'],reverse=True)[:4])/total,
            top_100_Expert_miss_share=sum(v for k,v in missed.most_common(100))/total,layers=layer_rows,
            top_20_Experts=[dict(layer=k[0],expert=k[1],misses=v)for k,v in missed.most_common(20)]))
        prior_demands.update(request_seen);previous_decode=decode_demands
    return output

def analyze(cache,workspace,work):
    installation=load(ROOT/'config/production-installation.json');adoption=load(ROOT/installation['qualification_report'])
    number=installation['normal_validation_case'];root=cache/f'hardware-first-generation-{number}'
    terminal_path=root/'native-model-terminal.private.json';terminal=load(terminal_path);closed=load(root/'restored-complete.private.json')
    need(number==12220 and terminal['completed'] and terminal['all_model_source_device_owners_positively_retired'] and
         terminal['device_ledger_live_bytes']==0 and closed['completed'] and not closed['unknown_completion'], 'Exact positively closed installed cohort required')
    need(terminal['candidate_SELF_sha256']==installation['application_SELF']['sha256'] and terminal['model_receipt_sha256']==installation['model_receipt_SHA256'] and
         terminal['active_cache_slots']==installation['active_expert_slots']==3072,'Installed SELF, model and actual cache geometry must match')
    model_record=load(root/'case-inputs.private.json')['model_receipt'];model_path=Path(model_record['path'])
    need(fingerprint(model_path)=={k:model_record[k]for k in ('bytes','sha256')}and model_record['sha256']==installation['model_receipt_SHA256'],
         'Exact selected weight inventory required')
    model=load(model_path)
    native_path=cache/'build'/adoption['application_relink']['native_build']/'receipt.private.json';native=load(native_path)
    source=native['resident_weight_normal']['actual_sources']['cache'];p=Path(source['path'])
    need(fingerprint(p)=={k:source[k]for k in ('bytes','sha256')},'Frozen native cache source changed')
    text=p.read_text();begin=text.index('struct moe_cache_slru {');end=text.index('// gate, up, down or gate_up, down',begin)
    work.mkdir(parents=True,exist_ok=False);(work/'current-cache.private.h').write_text(text[begin:end],newline='\n')
    traces=[load(root/f'native-arm{i}.routes.private.json')for i in range(3)]
    for i,t in enumerate(traces):
        need(t['complete']and t['sidecar_written_after_model_and_source_retirement']and t['pid']==terminal['pid']and t['run_id']==terminal['run_id']and t['ordinal']==i,
             'Complete route ownership required')
    save(work/'routes.private.json',traces)
    host=workspace/'toolchain/msys-clang64/clang64/bin';up=cache/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569'
    env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''))
    commands=[[str(host/'clang++.exe'),'-std=c++17','-O2','-I'+str(work),'-I'+str(ROOT/'native/app'),'-I'+str(up/'vendor'),
        str(ROOT/'tools/replay_retained_expert_cache.cpp'),'-o',str(work/'replay.exe')],
        [str(work/'replay.exe'),str(work/'routes.private.json'),str(work/'fills.private.json')]]
    for i,command in enumerate(commands):
        r=subprocess.run(command,capture_output=True,timeout=180,env=env);(work/f'{i}.private.log').write_bytes(r.stdout+r.stderr)
        need(r.returncode==0,r.stderr.decode(errors='replace')[-3000:])
    fills=load(work/'fills.private.json');bounds=accepted_phase_bounds(root,terminal,traces,fills)
    geometry=replay_geometry(traces,fills,bounds);rows=[]
    for r,t,g,bound in zip(terminal['requests'],traces,geometry,bounds):
        m=r['metrics'];d=r['completed_performance']['delta'];seconds=m['total_ms']/1000;process=d['process_ns']/1e9;wait=d['source_read_ns']/1e9
        need(d['source_chunks']==d['source_completed_windows'] and 0<wait<process<seconds and r['full_F32_finite'],'Completed nested timing and finite vocabulary required')
        evaluated=sum(x['tokens']for x in t['records'])//48;other=d['source_bytes']-t['uploaded_bytes']
        need(other==evaluated*10240,'Expert payload and original non-Expert rows must reconcile')
        latency_row=latency(r);tiny=next(x for x in latency_row['size_classes']if x['bucket']==0)
        need(tiny['calls']==17*evaluated,'Observed small row call geometry changed')
        row=dict(ordinal=r['ordinal'],condition=('model_loaded_Expert_cold','request_KV_reset_weights_retained','exact_prefix_plus_causal_reuse')[r['ordinal']],
            metrics=m,end_to_end_generated_tok_s=m['generated_tokens']/seconds,
            accepted_decode_transitions=m['generated_tokens']-1,EOS_and_completion_tail_ms=m['total_ms']-m['TTFT_ms']-m['decode_ms'],
            nonoverlapping_wall_s=dict(source_producer_wait=wait,model_process_outside_source_wait=process-wait,request_outside_model_process=seconds-process),
            source_wait_fraction_of_model_process=wait/process,source_wait_fraction_of_total_wall=wait/seconds,
            physical_GB=d['source_physical_read_bytes']/1e9,logical_Expert_GB=t['uploaded_bytes']/1e9,
            logical_non_Expert_bytes=other,non_Expert_lookups_per_evaluated_token=17,evaluated_model_tokens_including_prompt_EOS=evaluated,
            source_path_GB_per_producer_wait_s=d['source_physical_read_bytes']/1e9/wait,
            source_alignment_and_envelope_extra_bytes=d['source_physical_read_bytes']-d['source_bytes'],
            latency=latency_row,cache=g,process_phase_boundaries=bound,speculation=r['speculation'],
            diagnostic_timer_ms={k:d[k]/1e6 for k in ('source_handle_ns','source_headroom_ns','source_consumer_ns','checkpoint_ns','work_guard_ns','stage_observer_ns','synchronize_ns')},
            planner_CPU_ms=r['cold_request_timing']['plan_wall_ns']/1e6,routing_rank_CPU_ms=r['routing_policy']['rank_CPU_ns']/1e6,
            legacy_quad_timed_groups=r['cold_request_timing']['quad_batches'],streaming_groups=r['streaming_delivery']['groups'],
            maximum_configured_source_workers=4,actual_busy_period_occupancy_measured=False,
            separate_GPU_compute_CPU_sampling_and_durable_callback_times_measured=False)
        if r['ordinal']:
            row['decode']=token_analysis(root,r)
            need(row['decode']['cache_misses']==g['phase_misses']['decode'], 'Token and replay accepted-decode misses must match exactly')
            row['decode_source_wait_lower_bound_s']=max(0,wait-(seconds-m['decode_ms']/1000))
        rows.append(row)
    evidence=[terminal_path,root/'restored-complete.private.json',native_path,p,model_path,ROOT/'tools/replay_retained_expert_cache.cpp',ROOT/'tools/analyze_current_speed.py',
        ROOT/'native/app/indexed_probation_policy.h',ROOT/'native/app/expert_policy.h',ROOT/'native/app/resident_weight_retention.h',
        *[root/f'native-arm{i}.routes.private.json'for i in range(3)],*[root/'passive-observer'/f'request-{i}.stream.private.log'for i in(1,2)]]
    report=dict(schema='ps5-qwen-current-speed-analysis-v1',completed=True,source_case=number,application_SELF=installation['application_SELF'],
        application_source_revision=installation['application_source_revision'],driver=installation['driver'],model_receipt_SHA256=installation['model_receipt_SHA256'],
        rows=rows,exact_native_planner_replayed=True,all_three_native_hit_miss_upload_sequences_reconciled=True,
        selected_weight_inventory=[{k:t[k]for k in ('name','shape','type','bytes')}for t in model['tensors']
            if t['name']in ('per_layer_token_embd.weight','token_embd.weight','blk.1.ple_conv1d.weight','output.weight')],
        telemetry_corrections=[dict(field='route sidecar cache_slots',recorded=867,actual=3072,basis='Installed policy, terminal, frozen3072-slot replay matching all counters'),
            dict(field='route sidecar cache_reset_before_request for request1',recorded=True,actual=False,basis='Request reset retains Expert banks and counters; exact sequential replay'),
            dict(field='ordinary F32 comparison scope text',recorded='Same-policy independent full F32 and ordered routes',
                 actual='Unlike cache occupancy: finite full vocabulary and complete actual routes; token bytes equal')],
        memory=dict(CPU_heap_peak_bytes=terminal['CPU_heap_peak_bytes'],CPU_heap_limit_bytes=installation['CPU_heap_limit_bytes'],
            transient_device_ledger_peak_bytes=terminal['device_ledger_peak_bytes'],transient_device_ledger_cap_bytes=installation['postload_device_budget_bytes'],
            quota_slack_is_not_observed_free_physical_or_kernel_memory=True),
        limitations=['One finite30-token counting prompt and22 generated tokens; not sustained or broad-input throughput.',
            'Whole request I/O includes prefill and EOS; token Expert bytes are logical uploads, not measured physical decode bytes.',
            'Pread durations overlap and include OS/filesystem/scheduling. They do not measure raw SSD NAND service.',
            'Retained cache and cache-aware ranking can change routes. Fixed-route replay is diagnostic, not a counterfactual model-quality benchmark.',
            'Process remainder is CPU/backend/GPU and unclassified work, not pure GPU compute.',
            'Final request changes prefix reuse, Expert cache state and speculation together; no isolated speculation speedup claim.'],
        new_PS5_operations=0,production_changed=False,CI_runs=0,
        evidence=[dict(label=f'{i}:{x.name}',**fingerprint(x))for i,x in enumerate(evidence)])
    cold,ordinary,prefix=rows
    report['findings']=dict(
        ordinary_TTFT_reduction_vs_cold_fraction=1-ordinary['metrics']['TTFT_ms']/cold['metrics']['TTFT_ms'],
        ordinary_decode_rate_change_vs_cold_fraction=ordinary['metrics']['decode_tokens_per_second']/cold['metrics']['decode_tokens_per_second']-1,
        ordinary_decode_miss_increase_vs_cold_fraction=ordinary['cache']['phase_misses']['decode']/cold['cache']['phase_misses']['decode']-1,
        ordinary_prefill_evicted_future_decode_payload_bytes=ordinary['cache']['prefill_evicted_future_decode_keys']*TRIPLET,
        ordinary_hypothetical_half_source_wait_total_s=ordinary['metrics']['total_ms']/1000-ordinary['nonoverlapping_wall_s']['source_producer_wait']/2,
        ordinary_hypothetical_zero_source_wait_total_s=ordinary['metrics']['total_ms']/1000-ordinary['nonoverlapping_wall_s']['source_producer_wait'],
        prefix_completion_Expert_misses=prefix['cache']['phase_misses']['EOS'],
        prefix_completion_Expert_payload_bytes=prefix['cache']['phase_misses']['EOS']*TRIPLET,
        prefix_completion_processes=prefix['process_phase_boundaries']['after_last_token_processes'],
        prefix_completion_includes_rejected_width_two_then_width_one=True,
        final_comparison_changes_multiple_reuse_conditions=True,
        hypothetical_gains_are_not_adoption_or_causal_speed_claims=True)
    report['improvement_priorities']=[
        dict(priority=1,candidate='Protect recent decode residency during the next prefill, inside the existing3072 slots',
            evidence='Prefill evicts524 future-decode keys;521 were already used in the previous decode. Accepted decode misses rise725 to1115.',
            source_targets=['native/app/indexed_probation_policy.h:observe/victim','native/app/resident_weight_retention.h',
                'tools/build_resident_cache3072.py','tools/build_weight_followup_normal.py'],
            validation='First screen512/1024/1536 recent-decode protection sizes on captured routes, counting added prefill plus saved decode misses. Then qualify any winner on different inputs; cache-aware routes may change.',
            extra_Expert_weight_memory_required=False,causal_speedup_proven=False),
        dict(priority=2,candidate='Bounded immutable small-row cache shared across graph calls and requests',
            evidence='Ordinary884 small calls,14.975MB, mean1.5155ms; prefix408 small calls,6.914MB,37.1% of summed overlapping syscall time.',
            source_targets=['native/app/resident_small_rows.inc:upload_small_rows','tools/build_resident_small_rows.py',
                'native/app/source_read_latency.h'],
            design='Cache exact320-byte PLE and5120-byte token embedding rows by sealed source identity and physical/logical row key. Screen128KiB/512KiB/1MiB logical capacities and price actual allocation separately.',
            validation='Capture bounded row-key reuse first; compare actual calls and request wall time. Require exact full F32/routes/tokens/bytes, immutable-source invalidation and owned buffers. PLE uses n-gram hashes; token ID alone is not a valid PLE cache key.',
            extra_GPU_buffers_required=False,causal_speedup_proven=False),
        dict(priority=3,candidate='Completion-aware speculation budget, initially compare6 versus8 maximum attempts',
            evidence='The seventh attempt rejects after the last emitted token; completion includes two model calls and54 Expert misses,82.944MB logical payload.',
            source_targets=['native/app/causal_expert_sharing.h:next','native/app/llama_engine.cpp:next_with_one_draft/next_once'],
            validation='Compare complete request time and EOS tail, not decode rate alone. Preserve width-one fallback, complete-state restoration, EOS/output equality and owner retirement; a rejected width-two EOS row cannot simply replace the ordinary target.',
            direct_payload_or_time_savings_not_assumed_equal_to_tail=True,causal_speedup_proven=False),
        dict(priority=4,candidate='Measure queue, syscall, ready-to-consume, upload and CPU/GPU intervals on the selected streaming path',
            evidence='Ordinary3.037s of model process and0.967s outside process remain after source wait. Legacy quad timing covers26 groups while740 groups use streaming.',
            source_targets=['native/app/streaming_read_pool.h:worker/run','native/app/source_read_latency.h:completed',
                'native/app/llama_engine.cpp:process_batch_once/next_once','tools/build_cold_streaming.py',
                'tools/build_gpu_kernel_timing.py'],
            validation='Reuse timestamps and bounded counters; instrument actual pread entry/return and consume boundaries on all four lanes. Split prefill/accepted decode/EOS by native token boundaries. Keep monitoring, reserves and positive completion.',
            current_raw_SSD_or_pure_GPU_attribution_available=False),
        dict(priority=5,candidate='Correct stale report labels and qualify cache aging across multiple different requests',
            evidence='Route cache_slots867 and reset labels are stale; actual3072 replay matches all counters. The finite cohort has3024 planner observations, below the4096-observation aging boundary.',
            source_targets=['tools/build_weight_followup_normal.py','native/app/indexed_probation_policy.h:observe'],
            validation='Derive report geometry/reset/precision scope from actual policy. Include the4096-observation boundary in a finite different-input sequence. This analysis changes no runtime labels or model code.',
            direct_speedup_claimed=False)]
    report['low_priority_or_rejected_repeats']=[
        'Current planner10.030ms and ranking3.601ms cannot explain the ordinary7.486s request.',
        'Uniform bundle parallelism, wider queues and independent GPU prepass have already failed whole-request comparisons; require a new trace-specific mechanism before repeating them.',
        'Additional PLE quantization reduces320-byte rows but does not itself remove the current16KiB-aligned physical read calls.',
        'Larger Expert cache allocations are not the first action: preserve physical/kernel reserves and optimize replacement inside the measured budget.']
    return report

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('cache','workspace','work','out'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();need(not a.out.exists(),'Do not overwrite a previous analysis')
    report=analyze(a.cache,a.workspace,a.work);save(a.out,report)
    print(json.dumps(dict(completed=True,case=report['source_case'],native_planner_exact=True,PS5_operations=0,
        cache_misses=[r['cache']['cache_misses']for r in report['rows']],decode_misses=[r['cache']['phase_misses']['decode']for r in report['rows']],
        retained_prefill_evicted_previous_decode_keys_used_again=report['rows'][1]['cache']['prefill_evicted_previous_decode_keys_used_again'])))

if __name__=='__main__':main()
