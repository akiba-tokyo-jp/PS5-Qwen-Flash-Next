#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reconcile limit provenance, native operating points and historical refusals."""
import argparse,hashlib,json,math
from pathlib import Path

def load(path):return json.loads(Path(path).read_text('utf-8-sig'))
def need(value,message):
    if not value:raise ValueError(message)
def evidence(path,root):
    path=Path(path);data=path.read_bytes()
    return dict(label=path.relative_to(root).as_posix(),bytes=len(data),sha256=hashlib.sha256(data).hexdigest())

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('cache','index','capacity_screen','out'):p.add_argument('--'+key.replace('_','-'),type=Path,required=True)
    a=p.parse_args();root=Path(__file__).resolve().parents[1];production=load(root/'config/production-installation.json')
    index=load(a.index);case=a.cache/'hardware-first-generation-12840';timing=a.cache/'hardware-first-generation-12900'
    t=load(case/'native-model-terminal.private.json');g=load(timing/'native-model-terminal.private.json');cap=load(a.capacity_screen)
    for directory,terminal in ((case,t),(timing,g)):
        restored=load(directory/'restored-complete.private.json')
        need(terminal['completed'] and terminal['all_model_source_device_owners_positively_retired'] and terminal['device_ledger_live_bytes']==0,'Complete native resources required')
        need(restored['completed'] and restored['CPU_title_normally_closed'] and not restored['unknown_completion'] and restored['exact_fastest_SELF']['sha256']==production['application_SELF']['sha256'],'Exact ordinary close/restoration required')
    need(len(t['requests'])==10 and t['model_loads']==1,'One model load and ten completed requests required')
    need(t['full_F32_continuation_and_routes_passed'] and t['all_repeated_Q2_tokens_and_bytes_exact'],'Full byte-placement quality proof required')
    for r in t['requests']:
        need(r['full_F32_finite'] and r['maximum_absolute_logit_error']==0 and r['same_tokens_as_independent'] and r['metrics']['generated_tokens']==22,'Every full-row/token/byte control required')
    probe=t['limit_margin_probe'];need(probe['OS_minimum_preserved'] and probe['OS_counter_writes']==0 and probe['last_selected_padding_pages']==0,'Declared padding probe required')
    need(probe['phases'][0]['minimum_free_pages']>=1154 and probe['phases'][2]['minimum_selected_padding_pages']==0,
         'Separate the unchanged load frontier from the observed zero-padding inference point')
    io=[]
    for retained in (False,True):
        k=int(retained);aa,b,c,dd=(t['requests'][i*2+k] for i in (1,2,3,4))
        calls=lambda r:r['completed_performance']['delta']['source_physical_read_calls']
        size=lambda r:r['completed_performance']['delta']['source_physical_read_bytes']
        io.append(dict(weights_retained=retained,forward_whole_reduction_percent=100*(1-b['metrics']['total_ms']/aa['metrics']['total_ms']),
            reverse_whole_reduction_percent=100*(1-c['metrics']['total_ms']/dd['metrics']['total_ms']),
            forward_calls_saved=calls(aa)-calls(b),reverse_calls_saved=calls(dd)-calls(c),
            forward_bytes_saved=size(aa)-size(b),reverse_bytes_saved=size(dd)-size(c),
            control_calls=calls(aa),candidate_calls=calls(b),
            candidate_mean_decode_tok_s=(b['metrics']['decode_tokens_per_second']+c['metrics']['decode_tokens_per_second'])/2))
    need(g['GPU_graphs']==288 and len(g['cases'])==8 and g['model_loads']==0,'Complete no-model timing fixture required')
    timing_rows=[];total=0;checks=0
    for r in g['cases']:
        need(r['F64_reference_all_outputs_passed'] and r['canary_passed'] and r['snapshot_unwritten_slots_preserved'] and r['maximum_absolute_error']<=1e-6,'Every timing shape must remain numerically qualified')
        arms=r['arms'];need([x['candidate'] for x in arms]==[False,True,True,False],'ABBA order required')
        for arm in arms:
            for names in (('samples_us','mean_us'),('backend_samples_us','backend_mean_us'),('checkpoint_samples_us','checkpoint_mean_us')):
                values=arm[names[0]];need(len(values)==8 and all(math.isfinite(x)and x>0 for x in values)and abs(sum(values)/8-arm[names[1]])<1e-6,'Raw timing components must reconcile')
            need(all(abs(x-y-z)<1e-5 for x,y,z in zip(arm['samples_us'],arm['backend_samples_us'],arm['checkpoint_samples_us'])),'Whole timing must equal its measured components')
            total+=arm['mean_us'];checks+=arm['checkpoint_mean_us']
        backend=[x['backend_mean_us']for x in arms]
        timing_rows.append(dict(vector_gate=r['vector_gate'],tokens=r['tokens'],snapshots=r['snapshots'],
            backend_us=backend,completion_check_us=[x['checkpoint_mean_us']for x in arms],
            backend_forward_reduction_percent=100*(1-backend[1]/backend[0]),
            backend_reverse_reduction_percent=100*(1-backend[2]/backend[3]),
            maximum_F64_error=r['maximum_absolute_error']))
    memory=load(a.cache/'limit-audit-12804/closed-runtime-12840/memory.private.json')
    after=load(a.cache/'limit-audit-12804/closed-runtime-12840/memory.after-load.private.json')
    kernel=[];quota=[]
    for row in index['resource_refusals']:
        message=row['message'] or '';back=row['backpressure']
        if 'Native kernel free pages' in message or (back.get('last_qualified')is False and back.get('pressure_events',0)>0):
            kernel.append(dict(case=row['case'],message=message,observed_free_pages=back.get('kernel_free_pages',row['min_kernel_pages']),
                terminal=row['terminal'],hardware_exhaustion_demonstrated=False))
        elif 'Complete checkpoint cannot retain original reserves' in message:
            quota.append(dict(case=row['case'],message=message,terminal=row['terminal'],hardware_exhaustion_demonstrated=False))
    need(len(kernel)==22 and len(quota)==5 and cap['completed'],'Exact audited historical classification required')
    historical_heap=max(x['peak_CPU_heap_bytes']for x in index['cases']if x['completed'])
    scopes=[
      dict(id='K1',kind='unmeasured_application_padding',value='minimum+max(reserved,256) during load;minimum+64 after load',
           observed='Inference selects0 padding and completes;load minimum2312 pages never reaches the old load floor',physical_limit=False),
      dict(id='K2',kind='measured_components_with_padding',value='context entry1005;observed transient41+unmeasured2+steady64',observed='Context completes;phase minimum2267,so a low context-entry boundary is not established',physical_limit=False),
      dict(id='K3',kind='measured_components_with_padding',value='GPU entry1185;CPU entry1410;new source allocation19 extra pages',observed='Component observations exist;no universal minimum is qualified',physical_limit=False),
      dict(id='K4',kind='retired_global_interval_estimates',value='Old10142/8159-page prelaunch estimates;universal100MiB interpretation',observed='Later phase-local execution and current3072-slot model supersede them',physical_limit=False),
      dict(id='D1',kind='unmeasured_physical_pool_padding',value_bytes=512<<20,name='Direct reserve',observed='No minimum-reserve sweep;do not confuse it with kernel free pages',physical_limit=False),
      dict(id='D2',kind='unmeasured_physical_pool_padding',value_bytes=256<<20,name='Additional Direct platform margin',observed='Separate from CPU/staging;no marginal necessity measurement',physical_limit=False),
      dict(id='F1',kind='unmeasured_separate_quota_padding',value_bytes=256<<20,name='Flexible reserve',observed_available_bytes=memory['Flexible_available_bytes'],physical_limit=False),
      dict(id='F2',kind='unmeasured_separate_quota_padding',value_bytes=8<<20,name='Source Flexible metadata margin',observed='Read window is already Direct-backed;8MiB Flexible metadata necessity not established',physical_limit=False),
      dict(id='C1',kind='software_heap_cap',value_bytes=512<<20,successful_normal_mapped_peak_bytes=historical_heap,
           current_headless_peak_bytes=t['CPU_heap_peak_bytes'],physical_limit=False),
      dict(id='C2',kind='conservative_growth_accounting',value='Full512MiB CPU cap is charged against a Direct-free query that already excludes allocated CPU extents',
           observed='Before-load MemoryBudget uses cpu_working in full;the older after-load pricing helper correctly subtracts already-mapped CPU. Exact simultaneous overpricing needs a same-point heap sample.',physical_limit=False),
      dict(id='W1',kind='fixed_accounting_reservation',value_bytes=48<<20,observed_rounded_capacity_peak_bytes=t['actual_workspace_capacity_peak_bytes'],
           legacy_terminal_label_bytes=t['workspace_fixed_reservation_bytes'],observed_accounting_gap_bytes=(48<<20)-t['actual_workspace_capacity_peak_bytes'],physical_limit=False),
      dict(id='B1',kind='software_single_buffer_cap',value_bytes=1600<<20,reported_batch_limit_bytes=memory['device_buffer_batch_limit_bytes'],
           separately_demonstrated_allocated_buffer_bytes=2<<30,physical_limit=False),
      dict(id='B2',kind='software_live_byte_quota',value_bytes=memory['maximum_aggregate_postload_device_buffer_bytes'],
           current_normal_peak_bytes=5068816384,current_headless_peak_bytes=t['device_ledger_peak_bytes'],physical_limit=False),
      dict(id='B3',kind='evidence_and_entry_capacities',value='8192 live ledger entries;bounded VM sample vectors;finite route/request arrays',
           observed='12360 exhausts diagnostic VM observations after19 requests;not device RAM exhaustion',physical_limit=False),
      dict(id='I1',kind='performance_selected_range',value='4 source workers;2MiB scratch per lane;8MiB total;12 known reads/group',
           observed='2/3/4 lane comparisons exist;no hardware concurrency or larger-window optimum established',physical_limit=False),
      dict(id='I2',kind='tested_but_not_absolute_optimum',value='prefill32;1536 protected keys;6 causal attempts;3072 Expert slots',
           observed='Finite alternatives are measured;these are workload selections rather than hardware limits',physical_limit=False),
      dict(id='T1',kind='unmeasured_recovery_horizon',value='20s boundary/60s process wait;100ms poll;20min load deadline',
           observed='Timeouts bound an experiment;they do not establish memory capacity',physical_limit=False),
      dict(id='P1',kind='chosen_adoption_threshold',value_percent=2,observed='I/O whole time improves in both orders below2%;the cutoff is not hardware- or variance-derived',physical_limit=False),
      dict(id='P2',kind='measurement_scope_constraint',value='Mandatory completion check included in old isolated graph stopwatch',
           observed_completion_fraction_percent=100*checks/total,observed='Decode and prefill effects differ once components are separated',physical_limit=False),
      dict(id='H1',kind='reported_runtime_resource_envelope',Direct_pool_bytes=after['native_Direct_pool_bytes'],
           Direct_largest_before_load_bytes=memory['Direct_largest_available_bytes'],buffer_batch_limit_bytes=memory['device_buffer_batch_limit_bytes'],
           observed='Runtime pool and selected backend limit;no allocation-to-failure physical maximum claim'),
      dict(id='H2',kind='correctness_and_ownership_invariants',value='Alignment,source/hash/shape identity,complete output,positive GPU completion and ordinary close',
           observed='These are not arbitrary padding and are not relaxed by this audit')]
    additional=[dict(case=12360,cause='diagnostic_VM_observation_capacity',later_disposition='corrected12420 completes16;already resolved'),
        dict(case=3174,cause='estimated_initial_CPU_interval_price',later_disposition='old53/128 scope superseded by later qualified capacities and3072;do not replay obsolete format'),
        dict(candidate='Gate/Up Q2_0 format',cases=[12060,12080],cause='application1154-page load predicate;old1360 prose arithmetic corrected',
             later_disposition='eligible for new measured-margin format comparison;no new quality/speed claim'),
        dict(candidate='Current-miss676-triplet placement',cases=[12640,12680,12840],cause='earlier load predicate;fresh12840 completes10',
             later_disposition='Exact full-row/route/token proof and positive1.5-1.9% retained timing;adaptive margin state and finite sample size remain separate adoption qualifications'),
        dict(candidate='GDN128 four-column specialization',cases=[12720,12900],cause='guard-inclusive timing obscures shape effects',
             later_disposition='Reopen decode-only specialization;unconditional variant still regresses on32-token scalar cases'),
        dict(candidate='Fully completed losing/quality-failing variants',cases=[11420,11720,11880],cause='measured slowdown or output difference',
             later_disposition='Memory-margin audit does not overturn these distinct failures')]
    ev=[evidence(a.index,a.cache),evidence(a.capacity_screen,a.cache),
        evidence(a.cache/'limit-audit-12804/preprocess-proof.private.json',a.cache),
        evidence(a.cache/'hardware-first-generation-3643/native-CPU-terminal.private.json',a.cache)]
    ev.extend(evidence(a.cache/name,a.cache)for name in (
        'limit-audit-12804/closed-runtime-12840/memory.private.json',
        'limit-audit-12804/closed-runtime-12840/memory.after-load.private.json',
        'limit-overlay-proof-12815/complete.private.json','limit-probe-host-12810/complete.private.json',
        'build/Limit-margin-12814/receipt.private.json','build/Limit-margin-SELF-12816/receipt.private.json',
        'build/GDN-timing-12880/receipt.private.json','build/GDN-timing-SELF-12882/receipt.private.json'))
    ev.extend(evidence(d/name,a.cache)for d in (case,timing)for name in ('native-model-terminal.private.json','restored-complete.private.json'))
    report=dict(schema='ps5-qwen-limit-boundary-audit-v1',completed=True,inventory=scopes,
        historical_indexed_cases=len(index['cases']),historical_completed_true_flags=sum(x['completed']for x in index['cases']),
        kernel_policy_refusals=kernel,software_checkpoint_quota_refusals=quota,additional_affected_families=additional,
        margin_experiment=dict(case=12840,model_loads=1,requests=10,probe=probe,
            all_full_F32_maximum_zero=True,all_ordered_routes_tokens_and_bytes_exact=True,
            observed_below_OS_watermark_is_not_an_admission=True,load_under_old1154_floor_reproduced=False,
            inference_reaches_zero_extra_and_cohort_completes=True,physical_kernel_exhaustion_point_determined=False),
        IO_recomparison=io,IO_adopted=False,legacy_adoption_threshold_percent=2,
        timing_experiment=dict(case=12900,graphs=288,completion_check_fraction_percent=100*checks/total,rows=timing_rows,
            complete_F64_snapshots_and_canaries=True,pure_GPU_timestamp_claimed=False,whole_model_speed_claimed=False),
        cache_envelope=dict(bounds=cap['bounds'],rows=cap['rows'],host_trace_screen_not_native_speed=True,ownership_maps_validated=True),
        observed_memory={k:v for k,v in memory.items()if k!='pid'},observed_after_load=after,
        old1360_page_explanation_corrected_to1154=True,OS_counter_writes=0,reboots=0,forced_signals=0,CI_runs=0,
        production_adopted=False,production_SELF=production['application_SELF'],
        final_exact_restoration_and_native_gateway_models_inactive=True,evidence=ev,
        primary_OS_reference=dict(url='https://raw.githubusercontent.com/freebsd/freebsd-src/releng/9.0/sys/vm/vm_page.c',
            interpretation='Upstream allocation classes use distinct free/reserved watermarks;adding them is not an upstream universal physical-limit formula. Exact proprietary PS5 allocator equivalence is not established.'))
    need(not a.out.exists(),'Preserve preceding audit reports');a.out.write_text(json.dumps(report,indent=2)+'\n',newline='\n')
    print(json.dumps(dict(completed=True,inventory=len(scopes),kernel_policy_refusals=len(kernel),quota_refusals=len(quota),
        model_requests=10,GPU_timing_graphs=288,guard_fraction_percent=100*checks/total,IO_recomparison=io,cache_bounds=cap['bounds'])))

if __name__=='__main__':main()
