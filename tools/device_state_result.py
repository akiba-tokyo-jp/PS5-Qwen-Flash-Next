#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Classify the isolated state-copy fixture, never whole-model checkpoints."""
def validate(result,stages,pid):
    if not isinstance(result,dict)or result.get('schema')!='ps5-qwen-device-state-fixture-result-v1'or result.get('pid')!=pid:raise ValueError('Exact device-copy owner required')
    for key in ('all_F32_bits_exact','canaries_intact','all_copy_owners_retired','source_IO_completed_and_worker_stopped',
        'positive_device_idle_and_epoch_retirement','all_used_shader_inputs_SHA256_checked','all_shader_input_leases_returned','queue_submission_count_not_inferred'):
        if result.get(key)is not True:raise ValueError('Unpassed copy completion: '+key)
    for key,value in dict(state_bytes=136<<20,CPU_transfer_window_bytes=2<<20,device_ledger_live_bytes=0,shader_CPU_verified_assets=1527).items():
        if type(result.get(key))is not int or result[key]!=value:raise ValueError('Wrong finite copy scope: '+key)
    for key in ('model_loaded','model_state_completeness_qualified','host_full_state_payload_allocated'):
        if result.get(key)is not False:raise ValueError('Wrong copy-only scope')
    if type(result.get('device_ledger_peak_bytes'))is not int or not 0<result['device_ledger_peak_bytes']<=768<<20:raise ValueError('Unpriced copy allocation')
    if type(result.get('shader_module_inputs_after_CPU_verification'))is not int or result['shader_module_inputs_after_CPU_verification']<0:raise ValueError('Missing shader lease accounting')
    cases=result.get('cases')
    if not isinstance(cases,list)or len(cases)!=8:raise ValueError('Incomplete copy cohort')
    for n,row in enumerate(cases):
        if row!=dict(case=n,capture_pieces=2 if n%2==0 else 1,restore_pieces=1+n%3,discard=n==7,F32_bits_exact=True,canaries_intact=True):raise ValueError('Wrong copy partitions or exactness')
        if any(type(row[k])is not int for k in ('case','capture_pieces','restore_pieces'))or any(type(row[k])is not bool for k in ('discard','F32_bits_exact','canaries_intact')):raise ValueError('Wrong copy result types')
    expected={'device_state_shared_shader_CPU_admission_completed GPU_not_started=1':1,
        'device_state_before_capture owners_pinned=1':8,'device_state_capture_copies_completed owners_pinned=1':8,
        'device_state_before_restore owners_pinned=1':8,'device_state_restore_copies_completed owners_pinned=1':7,
        'device_state_restore_discarded_without_copy':1,'device_state_case_exact_and_positive_completion':8,
        'device_state_validation_completed_waiting_for_ordinary_close model_loaded=0':1}
    lines=stages.splitlines()
    if any(lines.count(key)!=value for key,value in expected.items()):raise ValueError('Missing durable copy completion')
    order=[line for line in lines if line in expected]
    sequence=['device_state_shared_shader_CPU_admission_completed GPU_not_started=1']
    for n in range(8):sequence+=['device_state_before_capture owners_pinned=1','device_state_capture_copies_completed owners_pinned=1',
        'device_state_before_restore owners_pinned=1','device_state_restore_discarded_without_copy'if n==7 else'device_state_restore_copies_completed owners_pinned=1',
        'device_state_case_exact_and_positive_completion']
    sequence+=['device_state_validation_completed_waiting_for_ordinary_close model_loaded=0']
    if order!=sequence:raise ValueError('Out-of-order device-copy completion')
    return dict(completed=True,completed_copy_cases=8,native_F32_copy_fixture_qualified=True,
        state_bytes=136<<20,positive_device_idle_and_epoch_retirement=True,all_copy_owners_retired=True,
        complete_model_checkpoint_qualified=False,prefix_reuse_qualified=False,speculative_verification_qualified=False,
        production_adopted=False,unknown_completion=False)
