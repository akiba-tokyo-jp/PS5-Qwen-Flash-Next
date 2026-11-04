#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Price only the unchanged ordinary target from completed R1 phase evidence."""
import argparse
from pathlib import Path

from audit_expert_all_q2_safety import body
from build_performance_quantizer import record
from price_unloaded_iq2_startup import initializer_count
from run_native_paired_down import geometry
from start_success_route import load,need,save


def require(path,package_path):
    value=load(path)
    need(value['completed'] and value['package']==record(package_path) and value['scope']=='ordinary-target-control' and
         value['original_native_guards_unchanged'] and value['no_MTP_or_new_GPU_buffers'] and
         value['ordinary_phase_slack_pages']==1024 and all(record(r['path'])==r for r in value['inputs']),
         'One exact original-target price with unchanged native guards and phase slack required')
    return value


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('current','package','R1-price','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();old=load(a.R1_price);package=load(a.package);profile=load(package['effective_application_policy']['profile']['path'])
    need(old['completed'] and old['CPU_phase_slack_pages']==256 and old['ordinary_model_phase_slack_pages']==1024 and
         profile['kind']=='headless-model-audit' and profile['headless_audit_kind'] in ('S1-ordinary-target-control','P1-tail-eight'),
         'Only the unchanged non-MTP target or bounded cold output-width refinement is admitted')
    if profile['headless_audit_kind']=='P1-tail-eight':
        refinement=load(profile['P1_refinement']['path'])
        need(record(profile['P1_refinement']['path'])==profile['P1_refinement'] and refinement['cold_output_tail_rows']==8 and
             len(refinement['new_selector_controls'])==16,'Exact completed eight-row output selector required')
    else:
        need(profile['overrides']['native_headless_model_audit']['auxiliary_contexts']==0 and
             profile['overrides']['native_headless_model_audit']['MTP_process_calls']==0,'The ordinary control may not create an auxiliary')
    need(all(record(r['path'])==r for r in old['inputs']),'Completed original CPU/R1 phase evidence changed')
    selected=load(a.current/'provenance/selected-entry-build.private.json');original=load(selected['application_policy']['path'])
    need(profile['CPU_SELF_provider']==original['CPU_SELF_provider'] and initializer_count(package)==old['constructors']==30,
         'Original reader and constructor count required')
    left=Path(original['source']['path']).read_text(encoding='utf-8');right=Path(profile['source']['path']).read_text(encoding='utf-8')
    for name in ('observed_system_headroom','require_model_CPU_budget','wait_for_initial_model_CPU_budget',
                 'model_file_identity','model_directory_identity','resident_reset_empty_context','bind_resident_main_SELF'):
        need(body(left,name)==body(right,name),'An original physical, identity, context or SELF guard changed')
    need('MTP_placements' not in right and 'model_params.load_mtp=true' not in right,'The control must have no auxiliary allocations')
    if profile['headless_audit_kind']=='S1-ordinary-target-control':need('const bool reuse=false;' in right,'No unused prefix capture is admitted')
    original_package=load(a.current/'provenance/current-package.private.json');old_geometry,new_geometry=geometry(original_package),geometry(package)
    extra=sum(max(0,new_geometry[k]-old_geometry[k]) for k in ('file_pages','zero_pages'))
    # One extra CPU page conservatively covers the reused F32 SHA observer's
    # fixed stack state. Credit no removed presentation or ELF pages.
    observer_stack=1;addition=extra+observer_stack
    inputs=[record(a.R1_price),package['effective_application_policy']['profile'],profile['source'],profile['entry_artifact'],
        selected['application_policy'],original['source'],record(a.package)] + old['inputs']
    state=load(a.current/'active-console.private.json')
    save(a.out,dict(completed=True,scope='ordinary-target-control',application_kind=profile['headless_audit_kind'],package=record(a.package),current_boot=state['current_boot'],
        inputs=inputs,original_native_guards_unchanged=True,no_MTP_or_new_GPU_buffers=True,constructors=30,
        original_geometry=old_geometry,new_geometry=new_geometry,additional_ELF_pages=extra,observer_stack_page_allowance=observer_stack,
        CPU_screen=old['CPU_screen']+addition,GPU_screen=old['GPU_screen']+addition,model_screen=old['model_screen']+addition,
        selected_readiness_pages=old['selected_readiness_pages']+addition,ordinary_phase_slack_pages=1024,CPU_slack_pages=256,
        removed_ELF_or_GPU_buffer_credit=0,previous_native_tests_replayed=0,PS5_operations=0,capacity_gain_claimed=False))
    print(dict(completed=True,selected_readiness_pages=old['selected_readiness_pages']+addition,extra_pages=addition,PS5_operations=0))


if __name__=='__main__':main()
