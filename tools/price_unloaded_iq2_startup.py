#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Price source-bound Direct-staged, model-free IQ2 arithmetic scopes."""
import argparse
import json
from pathlib import Path
import struct

from audit_expert_all_q2_safety import body
from build_performance_quantizer import record
from price_cpu_startup_original_reader import load_pages
from start_success_route import load,need,save


def exact(row):
    need(record(row['path'])==row,'An immutable component pricing input changed');return load(row['path'])


def initializer_count(package):
    linked=exact(package['relink']);row=linked['artifact'];need(record(row['path'])==row,'Exact linked ELF required')
    raw=Path(row['path']).read_bytes();offset=struct.unpack_from('<Q',raw,40)[0];stride,count,names=struct.unpack_from('<HHH',raw,58)
    need(stride==64 and count>0 and names<count,'Complete ELF64 section table required')
    headers=[struct.unpack_from('<IIQQQQIIQQ',raw,offset+i*stride) for i in range(count)];strings=headers[names]
    labels=raw[strings[4]:strings[4]+strings[5]]
    sizes=[h[5] for h in headers if labels[h[0]:labels.index(0,h[0])]==b'.init_array']
    need(len(sizes)==1 and sizes[0]%8==0,'One complete native constructor array required');return sizes[0]//8


def make(package_path,CPU_case,memory_evidence,vector_control,prefill_control,canonical_entry):
    package=load(package_path);profile=exact(package['effective_application_policy']['profile']);scope=profile['overrides']['native_IQ2_fixture']
    F16_reference=scope.get('F16_storage_FP32_accumulation') is True
    exact_F32=(scope['F32_shader_arithmetic_explicit'] and
        scope['backend_environment']=={'GGML_VK_DISABLE_MMVQ':'1','GGML_VK_DISABLE_F16':'1'} and
        scope['widths']==[1,2,30,32] and scope['maximum_GPU_graphs']==144 and scope['cases']==12)
    exact_F16=(F16_reference and not scope['F32_shader_arithmetic_explicit'] and
        scope['backend_environment']=={'GGML_VK_DISABLE_MMVQ':'1'} and scope['qualification_only'] and
        scope['synthetic_inputs_exactly_FP16'] and scope['widths']==[30,32] and
        scope['maximum_GPU_graphs']==12 and scope['cases']==6)
    need(package['completed'] and package['normalized_SELF_roundtrip_equal'] and package['effective_application_policy']['kind']=='Q2-IQ2-fixture' and
         profile['unloaded_GPU_fixture'] and profile['model_and_GPU_guards_preserved'] and scope['model_loads']==0 and
         (exact_F32 or exact_F16),'Exact finite model-free arithmetic profile required')
    base=load(canonical_entry);canonical=exact(base['application_policy']);need(record(canonical['source']['path'])==canonical['source'] and
         record(profile['source']['path'])==profile['source'],'Exact canonical and changed entries required')
    original=Path(canonical['source']['path']).read_text();changed=Path(profile['source']['path']).read_text()
    for name in ('observed_system_headroom','require_model_CPU_budget','wait_for_initial_model_CPU_budget','model_file_identity',
                 'model_directory_identity','admit_shader_storage_CPU','validate_prior_shader_CPU','bind_resident_main_SELF'):
        need(body(original,name)==body(changed,name),'An original CPU, identity or shader admission guard changed')
    reader=profile['CPU_SELF_provider'];need(reader['artifact']==base['reader'] and reader['OS_minimum_plus_21_unchanged'] and
         record(reader['artifact']['path'])==reader['artifact'],'Original selected64KiB SELF reader required')
    if F16_reference:
        runtime=profile['arithmetic_reference_runtime'];provider=profile['arithmetic_reference_provider']
        need(record(runtime['path'])==runtime and record(provider['path'])==provider and
             provider in exact(package['relink'])['new_inputs'] and 'unsetenv("GGML_VK_DISABLE_F16")' in changed,
             'The actual FP16-storage runtime, provider and normal environment must remain bound')
        source=Path(runtime['path']).read_text()
        need('outputs[format]->op_params[0]=int32_t(GGML_PREC_F32)' in source and
             'double(ggml_fp16_to_fp32(ggml_fp32_to_fp16(decoded[col])))' in source and
             'for(unsigned format=0;format<2&&valid;++format)' in source,
             'FP32 accumulation, the rounded storage reference and twelve distinct graphs are required')
    else:need('setenv("GGML_VK_DISABLE_F16","1",1)' in changed,'Explicit F32 environment must precede initialization')
    completed=load(CPU_case/'result.private.json');closure=exact(completed['closure']);terminal=exact(completed['terminal']);audit=terminal['audit']
    need(completed['completed'] and closure['ordinary_exit_observed'] and not closure['unknown_completion'] and
         audit['model_loads']==audit['GPU_calls']==0 and audit['main_SELF']['completed'] and audit['main_SELF']['full_current_SELF_SHA256_passed'],
         'Positive Direct whole-SELF CPU startup and ordinary restoration required')
    plan=load(CPU_case/'case/plan.private.json');CPU_package=exact(plan['package']);vm=load(CPU_case/'VM-before/result.private.json')['observations']
    need(vm['page_bytes']==16384 and vm['minimum']==898 and audit['main_SELF']['selected_CPU_floor']==919,'Exact current CPU page geometry required')
    before=min(vm['free_first'],vm['free_last']);read=audit['main_SELF'];startup_drop=before-read['minimum_sampled_free'];after_SELF_drop=before-read['free_after']
    extra=max(0,load_pages(package)-load_pages(CPU_package));constructors=initializer_count(package);CPU_constructors=initializer_count(CPU_package)
    need(constructors<=CPU_constructors,'Additional unmeasured native constructors require separate pricing')
    memory=load(memory_evidence);need(memory['completed'] and memory['PS5_mutations']==0,'Completed successful numeric memory evidence required')
    tail=0;GPU_floor=0
    for row in memory['observations']:
        prior=exact(row['plan']);reports=row['reports'];GPU=exact(reports['.resident.before-GPU']);GPU_floor=max(GPU_floor,GPU['required_pages'])
        need(GPU['GPU_calls']==0 and GPU['required_pages']==1185,'Unchanged native before-GPU price required')
        if '.resident.startup-memory' in reports:
            samples=exact(reports['.resident.startup-memory'])['samples'];start=next(s['kernel_free_pages'] for s in samples if s['phase']=='stage_0')
            tail=max(tail,start-GPU['free_pages'])
    controls=[]
    for path in (vector_control,prefill_control):
        control=load(path);closed=exact(control['closure']);component=exact(control['component'])
        need(control['completed'] and closed['ordinary_exit_observed'] and not closed['unknown_completion'] and
             component['all_backends_positively_retired'] and component['source_descriptor_and_scratch_retired'],
             'Control allocation observations require positive GPU completion and ordinary retirement')
        native=load(Path(control['case']['path']).parent/'headless-observer/native.private.bin')
        need(native['CPU_heap_peak_bytes']==64<<20 and native['device_ledger_peak_bytes']<=128<<20,
             'Measured bounded component allocation controls required; numerical success remains separate')
        controls.append(dict(control=record(path),CPU_peak=native['CPU_heap_peak_bytes'],device_peak=native['device_ledger_peak_bytes']))
    slack=256;GPU_extra=256
    CPU_screen=startup_drop+919+slack+extra;GPU_screen=after_SELF_drop+tail+GPU_floor+GPU_extra+slack+extra
    return dict(completed=True,source=record(Path(__file__)),compiled_component_package=record(package_path),CPU_case=record(CPU_case/'result.private.json'),
        memory_evidence=record(memory_evidence),vector_control=record(vector_control),prefill_control=record(prefill_control),canonical_entry=record(canonical_entry),
        observed_Direct_startup_global_drop_pages=startup_drop,observed_after_SELF_global_drop_pages=after_SELF_drop,
        observed_pre_GPU_tail_pages=tail,original_CPU_floor_pages=919,unchanged_native_before_GPU_pages=GPU_floor,
        extra_ELF_LOAD_pages=extra,constructors=constructors,CPU_control_constructors=CPU_constructors,operational_slack_pages=slack,
        additional_component_GPU_metadata_screen_pages=GPU_extra,CPU_phase_screen_pages=CPU_screen,GPU_phase_screen_pages=GPU_screen,
        selected_model_free_readiness_pages=max(CPU_screen,GPU_screen),allocation_controls=controls,model_loads=0,
        ordinary_model_screen_pages_unchanged=7374,ordinary_model_launch_admission_granted=False,all_original_native_guards_unchanged=True,
        empirical_global_observations_not_exclusive_bounds=True,universal_safe_memory_bound_established=False,PS5_operations=0)


def require_pricing(path,package):
    value=load(path);actual=make(package,Path(value['CPU_case']['path']).parent,Path(value['memory_evidence']['path']),
        Path(value['vector_control']['path']),Path(value['prefill_control']['path']),Path(value['canonical_entry']['path']))
    need(value==actual,'Exact model-free pricing must reproduce from unchanged evidence');return value


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('package','CPU-case','memory-evidence','vector-control','prefill-control','canonical-entry','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();result=make(a.package,a.CPU_case,a.memory_evidence,a.vector_control,a.prefill_control,a.canonical_entry)
    a.out.mkdir(parents=True,exist_ok=False);save(a.out/'result.private.json',result)
    print(json.dumps({k:result[k] for k in ('completed','selected_model_free_readiness_pages','CPU_phase_screen_pages','GPU_phase_screen_pages','ordinary_model_screen_pages_unchanged')}))


if __name__=='__main__':main()
