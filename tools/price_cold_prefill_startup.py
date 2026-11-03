#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Price the ordinary P1 scope from completed CPU and actual ordinary model phases."""
import argparse
import re
from pathlib import Path

from audit_expert_all_q2_safety import body
from build_performance_quantizer import record
from price_cpu_startup_original_reader import load_pages
from price_unloaded_iq2_startup import initializer_count
from start_success_route import load,need,save


def exact(row):
    need(record(row['path'])==row,'An immutable startup pricing input changed');return load(row['path'])


def require(path,packages):
    value=load(path)
    need(value['completed'] and value['scope']=='P1-cold' and value['all_original_native_guards_unchanged'] and
         value['ordinary_model_phase_slack_pages']==1024 and value['CPU_phase_slack_pages']==256 and
         value['CPU_floor']==919 and value['GPU_floor']==1185 and value['model_floor']==1104,
         'Exact scope-specific observed pricing required')
    need(all(record(p) in value['packages'] for p in packages),'Pricing belongs to different native packages')
    need(all(record(r['path'])==r for r in value['inputs']),'Completed memory or source proof changed')
    return value


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('current','CPU-case','sequence','memory','out'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--package',type=Path,action='append',required=True);a=p.parse_args()
    evidence=[record(a.CPU_case/'result.private.json'),record(a.sequence/'result.private.json'),record(a.memory)]
    CPU=load(a.CPU_case/'result.private.json');closed=exact(CPU['closure']);terminal=exact(CPU['terminal'])
    need(CPU['completed'] and closed['ordinary_exit_observed'] and closed['current_seven_restored_and_native_hashed'] and
         not closed['unknown_completion'] and terminal['audit']['GPU_calls']==terminal['audit']['model_loads']==0,
         'Completed ordinary-reader CPU control and exact restoration required')
    evidence.extend((CPU['closure'],CPU['terminal']))
    CPU_start=load(a.CPU_case/'VM-before/result.private.json')['observations'];main=terminal['audit']['main_SELF']
    need(main['completed'] and main['full_current_SELF_SHA256_passed'] and main['selected_CPU_floor']==919 and
         main['maximum_read_window_bytes']==65536,'The original whole SELF reader is required')
    CPU_drop=min(CPU_start['free_first'],CPU_start['free_last'])-main['minimum_sampled_free']
    evidence.append(record(a.CPU_case/'VM-before/result.private.json'))
    memory=load(a.memory);need(memory['completed'] and len(memory['rows'])==12,'All four completed ordinary phase histories required')
    sequence=load(a.sequence/'result.private.json')
    need(sequence['completed'] and sequence['scope']=='R1-stage' and sequence['all_ordinary_closes_and_exact_restores'],
         'A positively completed ordinary-model R1 cohort required')
    GPU_drop=model_drop=0
    for case in sequence['cases']:
        done=exact(case['close']);native=exact(case['native_terminal'])
        need(done['ordinary_exit_observed'] and done['current_seven_restored_and_native_hashed'] and not done['unknown_completion'] and
             native['all_model_source_device_owners_positively_retired'] and native['device_ledger_live_bytes']==0,
             'Only positively retired model scopes may price a new model')
        evidence.extend((case['close'],case['native_terminal'],case['case_plan']))
        clock=a.sequence/('clock-'+str(case['case']))/'execution/console.private.log'
        match=re.findall(rb'CURRENT_VM index=0 pages=(\d+)',clock.read_bytes());need(len(match)==1,'One original prelaunch observation required')
        start=int(match[0]);evidence.append(record(clock))
        reports={r['suffix']:exact(r['report']) for r in memory['rows'] if r['case']==case['case']}
        evidence.extend(r['report'] for r in memory['rows'] if r['case']==case['case'])
        gpu=reports['resident.before-GPU'];after=reports['system-memory.after-context'];history=reports['resident.startup-memory']
        need(gpu['required_pages']==1185 and gpu['GPU_calls']==0 and after['model_loaded'] and after['kernel_minimum_pages']==898 and
             after['kernel_reserved_pages']==206 and after['kernel_page_size']==16384 and after['CPU_heap_libc_fallbacks']==0,
             'Original native phase geometry and successful model/context completion required')
        GPU_drop=max(GPU_drop,start-gpu['free_pages'])
        model_drop=max(model_drop,start-min([after['kernel_free_pages']]+[r['kernel_free_pages'] for r in history['samples']]))
    selected=load(a.current/'provenance/selected-entry-build.private.json');original=exact(selected['application_policy'])
    original_text=Path(original['source']['path']).read_text();evidence.extend((selected['application_policy'],original['source']))
    current=load(a.current/'provenance/current-package.private.json');pages=load_pages(current);constructors=initializer_count(current)
    extra=0
    for path in a.package:
        package=load(path);profile=exact(package['effective_application_policy']['profile'])
        need(package['completed'] and package['normalized_SELF_roundtrip_equal'] and profile['kind']=='P1-cold-prefill' and
             profile['CPU_SELF_provider']==original['CPU_SELF_provider'] and initializer_count(package)==constructors==30,
             'Only the two explicit cold-only P1 packages with unchanged reader/constructors are admitted')
        checked=exact(profile['P1_refinement']);need(checked['actual_PS5_ABI_compiled'] and len(checked['new_selector_controls'])==16,
             'All new ordered phase controls must already pass')
        need(record(profile['source']['path'])==profile['source'],'Actual compiled P1 entry changed')
        changed=Path(profile['source']['path']).read_text()
        for name in ('observed_system_headroom','require_model_CPU_budget','wait_for_initial_model_CPU_budget',
                     'model_file_identity','model_directory_identity','bind_resident_main_SELF'):
            need(body(original_text,name)==body(changed,name),'An original memory/identity guard changed')
        extra=max(extra,load_pages(package)-pages)
        evidence.extend((package['effective_application_policy']['profile'],profile['P1_refinement'],profile['source'],profile['entry_artifact']))
    extra=max(0,extra)
    CPU_screen=CPU_drop+919+256+extra;GPU_screen=GPU_drop+1185+1024+extra;model_screen=model_drop+1104+1024+extra
    state=load(a.current/'active-console.private.json')
    report=dict(completed=True,scope='P1-cold',packages=[record(p) for p in a.package],current_boot=state['current_boot'],
        inputs=evidence,observed_CPU_start_to_minimum_SELF_drop=CPU_drop,observed_ordinary_pre_GPU_drop=GPU_drop,
        observed_ordinary_model_prefix_drop=model_drop,extra_ELF_LOAD_pages=extra,constructors=constructors,
        CPU_floor=919,GPU_floor=1185,model_floor=1104,CPU_phase_slack_pages=256,ordinary_model_phase_slack_pages=1024,
        CPU_screen=CPU_screen,GPU_screen=GPU_screen,model_screen=model_screen,
        selected_readiness_pages=max(CPU_screen,GPU_screen,model_screen),historical_S1_screen=7374,
        all_original_native_guards_unchanged=True,global_observations_not_exclusive_allocation_bounds=True,
        capacity_or_speed_gain_claimed=False,no_inactive_pages_counted=True,previous_native_scopes_replayed=0,PS5_operations=0)
    save(a.out,report);print({k:v for k,v in report.items() if k.endswith('_screen') or k=='selected_readiness_pages'})


if __name__=='__main__':main()
