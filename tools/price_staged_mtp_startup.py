#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Admit the measured CPU startup, then use unchanged live native phase guards."""
import argparse
from pathlib import Path

from audit_expert_all_q2_safety import body
from build_performance_quantizer import record
from mtp_shadow_host_check import require_online_profile
from price_unloaded_iq2_startup import initializer_count
from run_native_paired_down import geometry
from start_success_route import load,need,save


def require(path,package_path):
    value=load(path)
    need(value['completed'] and value['scope']=='S1-staged-startup' and value['package']==record(package_path) and
         value['native_physical_reserve_budget_and_completion_guards_unchanged'] and value['CPU_phase_slack_pages']==256 and
         value['full_model_admission_not_inferred_from_CPU_screen'] and all(record(r['path'])==r for r in value['inputs']),
         'One exact measured CPU startup with unchanged live GPU/model admission required')
    return value


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('current','package','CPU-price','successful-MTP','out'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--completed-phase-case',type=Path)
    p.add_argument('--completed-phase-close',type=Path)
    a=p.parse_args();cpu=load(a.CPU_price);package=load(a.package);profile=load(package['effective_application_policy']['profile']['path'])
    require_online_profile(profile)
    need(cpu['completed'] and cpu['CPU_phase_slack_pages']==256 and cpu['CPU_floor']==919 and cpu['constructors']==30,
         'The completed original-reader CPU startup and unchanged slack are required')
    need(all(record(r['path'])==r for r in cpu['inputs']),'Completed CPU source/phase evidence changed')
    old=load(a.successful_MTP/'result.private.json');terminal=load(old['terminal']['path']);closed=load(old['closure']['path'])
    need(old['completed'] and closed['ordinary_exit_observed'] and closed['current_seven_restored_and_native_hashed'] and
         terminal['completed'] and terminal['all_model_source_device_owners_positively_retired'] and terminal['device_ledger_live_bytes']==0,
         'The original native MTP model must already have completed and ordinarily restored')
    case=load(a.successful_MTP/'case/plan.private.json');prior=load(case['package']['path']);baseline=load(prior['effective_application_policy']['profile']['path'])
    need(profile['CPU_SELF_provider']==baseline['CPU_SELF_provider'] and initializer_count(package)==initializer_count(prior)==30 and
         profile['no_unused_prefix_checkpoint'] and profile['ordinary_compact_engine_contract'],
         'Only the corrected finite three-ordinary-request MTP entries are admitted')
    left=Path(baseline['source']['path']).read_text(encoding='utf-8');right=Path(profile['source']['path']).read_text(encoding='utf-8')
    for name in ('observed_system_headroom','require_model_CPU_budget','wait_for_initial_model_CPU_budget',
                 'model_file_identity','model_directory_identity','resident_reset_empty_context','bind_resident_main_SELF'):
        need(body(left,name)==body(right,name),'An original successful native phase guard changed')
    need('model_params.load_mtp=true;' in left and 'model_params.load_mtp=true;' in right and
         'const bool reuse=false;' in right,'The same MTP model and ordinary-only sequence are required')
    old_geometry,new_geometry=geometry(prior),geometry(package)
    extra=sum(max(0,new_geometry[k]-old_geometry[k]) for k in ('file_pages','zero_pages'))
    # No removed pages are credited. Include one page for new fixed metadata.
    selected=cpu['CPU_screen']+extra+1
    inputs=[record(a.CPU_price),record(a.package),package['effective_application_policy']['profile'],profile['source'],
        record(a.successful_MTP/'result.private.json'),old['terminal'],old['closure'],case['package'],
        prior['effective_application_policy']['profile'],baseline['source'],profile['ordinary_compact_engine_contract']]+cpu['inputs']
    state=load(a.current/'active-console.private.json')
    phase=None
    if a.completed_phase_case:
        need(a.completed_phase_close is not None,'Source-bound ordinary closure of the same completed phases required')
        failure_path=a.completed_phase_case/'case/native.failure.private.json';failure=load(failure_path)
        closure=load(a.completed_phase_close);vm_path=a.completed_phase_case/'VM-before/result.private.json';vm=load(vm_path)['observations']
        need(closure['completed'] and closure['S1_post_request_certificate_refusal'] and closure['target_request_operations']==1 and
             closure['ordinary_exit_observed'] and closure['current_seven_restored_and_native_hashed'] and not closure['unknown_completion'] and
             failure['CPU_worker_completion_unknown'] is False and failure['four_next']['complete_captures_elided']==6 and
             vm['boot_before']==vm['boot_after']==state['current_boot'],'Only the completed49-epoch first request with known subsequent CPU refusal is admitted')
        audit=load(closure['source_audit']['path']);need(audit['proof']['completed_GPU_epochs']==49 and audit['proof']['completed_F32_rows']==23 and
            record(closure['source_audit']['path'])==closure['source_audit'],'Exact positive target/auxiliary boundary required')
        phases={r['phase']:r for r in failure['limit_margin_probe']['phases']}
        need(all(phases[i]['admission_calls']>0 and phases[i]['legacy_refusals']==0 and phases[i]['padding_reductions']==0 for i in (1,2,3)),
             'All measured live loading/context/model phase admissions must pass unchanged')
        start=min(vm['free_first'],vm['free_last']);pre_model=min(phases[i]['minimum_free_pages'] for i in (1,2));during_model=phases[3]['minimum_free_pages']
        GPU=start-pre_model+1185+1024+extra+1;model=start-during_model+1104+1024+extra+1
        selected=max(selected,GPU,model)
        phase=dict(start_pages=start,pre_model_phase_minimum_pages=pre_model,model_phase_minimum_pages=during_model,
            GPU_screen=GPU,model_screen=model,GPU_floor=1185,model_floor=1104,model_and_GPU_slack_pages=1024,
            subsequent_CPU_certificate_failure_not_a_phase_failure=True,exclusive_allocation_bound_claimed=False)
        inputs += [record(failure_path),record(vm_path),record(a.completed_phase_close),closure['source_audit']]
    save(a.out,dict(completed=True,scope='S1-staged-startup',package=record(a.package),current_boot=state['current_boot'],inputs=inputs,
        original_CPU_screen=cpu['CPU_screen'],extra_ELF_pages=extra,new_fixed_metadata_allowance_pages=1,
        selected_readiness_pages=selected,CPU_floor=919,CPU_phase_slack_pages=256,constructors=30,
        historical_whole_model_extrapolation_screen=7374,extra_model_GPU_prelaunch_extrapolation_slack_pages=1024 if phase else 0,
        completed_GPU_phase_evidence=phase,
        native_physical_reserve_budget_and_completion_guards_unchanged=True,full_model_admission_not_inferred_from_CPU_screen=True,
        GPU_and_model_phases_require_fresh_native_admission=True,all_runtime_allocations_remain_bounded=True,
        removed_ELF_or_buffer_credit=0,inactive_pages_counted=0,previous_native_tests_replayed=0,PS5_operations=0,
        universal_hardware_startup_bound_claimed=False))
    print(dict(completed=True,selected_CPU_readiness_pages=selected,native_phase_guards_unchanged=True,PS5_operations=0))


if __name__=='__main__':main()
