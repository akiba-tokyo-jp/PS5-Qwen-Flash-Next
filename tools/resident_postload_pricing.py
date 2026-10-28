#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Price the next context separately after positive model/upload completion."""
import copy
import json
import resident_kernel_min_scope as previous

SCOPE=copy.deepcopy(previous.SCOPE)
SCOPE.update(schema='ps5-qwen-postload-next-context-v3',
    activation_after_original_context_and_positive_completion=False,
    original_GPU_initialization_and_context_floors_unchanged=False,
    original_GPU_initialization_and_model_load_floors_unchanged=True,
    activation_after_model_and_positive_upload_retirement=True,
    selected_context_entry_pages=1005, measured_context_allowance_pages=43,
    observed_before_context_refusal_pages=1162, observed_original_context_entry_pages=1197)


def entry(text):
    text=previous.entry(text)
    start=text.index('\n        if(!model||!context||llama_n_ctx(context)!=256||llama_n_batch(context)!=4||qwen_app_resident_CPU_metadata_scope_active())')
    end=text.index('\n        write_fresh_report(startup.admission_report+".resident.startup-memory"',start)
    activation=text[start:end]
    if activation.count('qwen_app_activate_resident_GPU_OS_reserve();')!=1:
        raise ValueError('One exact positively completed reserve activation block required')
    text=text[:start]+text[end:]
    activation=activation.replace(
        'if(!model||!context||llama_n_ctx(context)!=256||llama_n_batch(context)!=4||qwen_app_resident_CPU_metadata_scope_active())',
        'if(!model||context||qwen_app_resident_CPU_metadata_scope_active())')
    activation=activation.replace('Original completed model/context required before reserve selection',
        'Completed original model and upload retirement required before next-context pricing')
    activation=activation.replace('OS_scope_memory.kernel_free<962','OS_scope_memory.kernel_free<1005')
    activation=activation.replace('{"activated_after_original_context",true}',
        '{"activated_after_original_context",false},{"activated_after_model_and_upload_retirement",true},{"selected_context_entry_pages",1005}')
    frontier=text.index('        const auto upload_retired_bytes=')
    at=text.index('        qwen_native_driver_begin();',frontier)
    text=text[:at]+activation+'\n'+text[at:]
    old='std::max<std::uint64_t>(context_memory.kernel_reserved,256);'
    if text.count(old)!=1:
        raise ValueError('One unchanged separately measured context allowance required')
    text=text.replace(old,'(qwen_app_resident_GPU_OS_reserve_active()?64ull:std::max<std::uint64_t>(context_memory.kernel_reserved,256));')
    before=json.dumps(previous.SCOPE,separators=(',',':'))
    if text.count(before)!=1:
        raise ValueError('One exact native scope binding required')
    text=text.replace(before,json.dumps(SCOPE,separators=(',',':')))
    if not(text.index('qwen_app_release_completed_upload_staging();')<text.index('qwen_app_activate_resident_GPU_OS_reserve();')<text.index('if(context_memory.kernel_free<context_floor+43)')):
        raise ValueError('Positive upload retirement and measured next-context ordering required')
    return text
