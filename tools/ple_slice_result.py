#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Review a completed PLE fixture without launching, retrying, closing or adopting it."""
import math,statistics

def validate(result,pid,stages):
    smoke=isinstance(result,dict)and result.get('schema')=='ps5-qwen-PLE-slice-smoke-v1'
    paired=isinstance(result,dict)and result.get('schema')=='ps5-qwen-PLE-slice-paired-fixture-v2'
    prior=smoke or paired
    graphs=4 if smoke else 208
    if type(pid)is not int or pid<=0 or not isinstance(result,dict)or result.get('schema')not in('ps5-qwen-PLE-slice-fixture-v1','ps5-qwen-PLE-slice-smoke-v1','ps5-qwen-PLE-slice-paired-fixture-v2')or type(result.get('pid'))is not int or result['pid']!=pid:
        raise ValueError('Exact owned PLE fixture required')
    for key in('F64_reference_passed','all_F32_outputs_bit_exact','input_and_output_canaries_intact','original_BF16_to_F32_casts_preserved',
        'graph_construction_measured_separately','common_final_output_copy_in_all_arms','driver_final_epoch_retirement_requires_caller',
        'positive_device_idle_and_epoch_retirement','all_used_shader_inputs_SHA256_checked','all_shader_input_leases_returned'):
        if result.get(key)is not True:raise ValueError('Unpassed PLE completion or precision: '+key)
    for key,value in dict(GPU_graphs=graphs,device_ledger_live_bytes=0,source_preflight_read_calls=2,existing_source_scratch_bytes=8<<20,source_worker_read_ns=0).items():
        if type(result.get(key))is not int or result[key]!=value:raise ValueError('Wrong PLE finite counter: '+key)
    if prior:
        h=result.get('prior_all_shader_CPU_report_SHA256')
        if not isinstance(h,str)or len(h)!=64 or any(c not in'0123456789abcdef'for c in h)or result.get('current_complete_external_file_SHA256_checked')is not True or type(result.get('shader_CPU_verified_assets'))is not int or result['shader_CPU_verified_assets']!=0:
            raise ValueError('Missing prior and current shader integrity')
    if paired and any(result.get(k)is not True for k in('source_guard_current_full_SHA256_checked','source_guard_bytes_not_used_for_numerics')):
        raise ValueError('Paired v2 requires its completed bounded source integrity')
    for key in(('prior_all_shader_CPU_assets','shader_module_inputs_after_CPU_verification')if prior else('shader_CPU_verified_assets','shader_module_inputs_after_CPU_verification')):
        if type(result.get(key))is not int or result[key]<=0:raise ValueError('Missing current shader proof')
    if result.get('model_loaded')is not False or result.get('numerical_data')!='deterministic_original_shapes_not_model_weights'or result.get('timed_scope')!='graph_compute_synchronization_driver_checkpoints_and_output_readback':
        raise ValueError('Unexpected PLE model or timing scope')
    error=result.get('maximum_absolute_error');peak=result.get('device_ledger_peak_bytes');source=result.get('source_preflight_read_bytes')
    if type(error)not in(int,float)or not math.isfinite(error)or error<0 or type(peak)is not int or not 0<peak<=1792<<20 or type(source)is not int or not 32768<=source<49152:
        raise ValueError('Invalid PLE numeric or resource measurement')
    widths=result.get('widths');expected_events=[];summaries=[]
    if not isinstance(widths,list)or len(widths)!=(1 if smoke else 4):raise ValueError('Incomplete PLE widths')
    for width,row in enumerate(widths,1):
        keys={'tokens','graph_construction_ns','CONT_nodes','warmups','batches','raw_device_buffer_cap_bytes','all_operations_on_single_Vulkan_backend'}
        if not isinstance(row,dict)or set(row)!=keys or type(row['tokens'])is not int or row['tokens']!=width or row['CONT_nodes']!=[8,4,4,0]or any(type(x)is not int for x in row['CONT_nodes'])or row['all_operations_on_single_Vulkan_backend']is not True or type(row['raw_device_buffer_cap_bytes'])is not int or row['raw_device_buffer_cap_bytes']!=16<<20:
            raise ValueError('Wrong PLE graph geometry or placement')
        construction=row['graph_construction_ns']
        if not isinstance(construction,list)or len(construction)!=4 or any(type(x)is not int or x<0 or x>120000000000 for x in construction):raise ValueError('Invalid separate graph construction time')
        warmups=row['warmups'];batches=row['batches']
        if not isinstance(warmups,list)or len(warmups)!=4 or not isinstance(batches,list)or len(batches)!=(0 if smoke else 48):raise ValueError('Incomplete PLE warm/timed cohort')
        ordinal=0;by_pair={}
        for mode,warm in enumerate(warmups):
            ordinal+=1
            if not isinstance(warm,dict)or set(warm)!={'mode','ordinal','graph_completion_and_readback_ns'}or warm['mode']!=mode:raise ValueError('Wrong PLE warmup')
            check_event(warm,ordinal);expected_events.append((width,mode,ordinal,warm['graph_completion_and_readback_ns']))
        position=0
        for candidate in(()if smoke else(1,2,3)):
            ratios=[]
            for round_ in range(8):
                times={}
                for arm in range(2):
                    event=batches[position];position+=1;ordinal+=1;mode=candidate if(round_+arm)%2 else 0
                    if not isinstance(event,dict)or set(event)!={'candidate','round','mode','ordinal','graph_completion_and_readback_ns'}or any(type(event[k])is not int for k in('candidate','round','mode'))or (event['candidate'],event['round'],event['mode'])!=(candidate,round_,mode):raise ValueError('PLE alternating order differs')
                    check_event(event,ordinal);elapsed=event['graph_completion_and_readback_ns'];times[mode]=elapsed;expected_events.append((width,mode,ordinal,elapsed))
                ratios.append(times[0]/times[candidate])
            by_pair[str(candidate)]=dict(median_paired_ratio=statistics.median(ratios),faster_rounds=sum(r>1 for r in ratios),all_rounds_faster=all(r>1 for r in ratios))
        summaries.append(dict(tokens=width,candidates=by_pair))
    lines=[line for line in stages.splitlines()if line.startswith(('PLE_fixture_graph_before ','PLE_fixture_graph_and_readback_returned '))]
    if len(lines)!=2*len(expected_events):raise ValueError('Missing durable PLE graph completion')
    for i,(width,mode,ordinal,elapsed)in enumerate(expected_events):
        before=f'PLE_fixture_graph_before width={width} mode={mode} ordinal={ordinal} GPU_backing_pinned=1'
        after=f'PLE_fixture_graph_and_readback_returned width={width} mode={mode} ordinal={ordinal} elapsed_ns={elapsed} GPU_completion_checked=1'
        if lines[2*i:2*i+2]!=[before,after]:raise ValueError('Durable PLE graph binding/order/time differs')
    begin='PLE_slice_shared_shader_CPU_admission_completed GPU_not_started=1';end='PLE_slice_validation_completed_waiting_for_ordinary_close model_loaded=0'
    if stages.splitlines().count(begin)!=1 or stages.splitlines().count(end)!=1 or not stages.index(begin)<stages.index(lines[0])<stages.rindex(lines[-1])<stages.index(end):raise ValueError('Missing final PLE caller retirement')
    return dict(completed=True,GPU_graphs=graphs,width_summaries=summaries,graph_fixture_only=True,smoke_only=smoke,
        model_quality_or_speed_qualified=False,production_adopted=False,unknown_completion=False)

def check_event(event,ordinal):
    if type(event.get('ordinal'))is not int or event['ordinal']!=ordinal or type(event.get('mode'))is not int:
        raise ValueError('Wrong PLE event types/order')
    elapsed=event.get('graph_completion_and_readback_ns')
    if type(elapsed)is not int or not 0<elapsed<=120000000000:raise ValueError('Invalid PLE complete-graph interval')
