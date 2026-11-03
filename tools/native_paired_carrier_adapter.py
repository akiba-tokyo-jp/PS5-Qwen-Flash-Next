#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Preserve a positively idle component device through ordinary process close."""
from pathlib import Path
from build_performance_quantizer import record
from start_success_route import load, need


def replace_once(text, before, after):
    need(text.count(before) == 1, 'One exact carrier lifetime adapter boundary required')
    return text.replace(before, after)


def support_text(text):
    text = replace_once(text, '#include "post_device_retirement.h"', '#include "retained_completed_device.h"')
    start = text.index('static void native_component_finish(uint64_t epoch){')
    end = text.index('int qwen_paired_down_component(int,char**);', start)
    text = text[:start] + '''static qwen_app::RetainedCompletedDevice native_retained_device;
static NativeJson native_retained_result;
static void native_component_retain(uintptr_t device,uintptr_t instance,uint64_t epoch){
    native_require(qwen_app::retain_completed_device(device,instance,epoch,native_retained_device,
        {ps5_ai_arena_kick_snapshot,ps5_ai_arena_snapshot,ps5_ai_native_arena_journal_checkpoint}),
        "The completed idle device must remain explicitly owned until ordinary close");
    native_guard();
}
static NativeJson native_retained_receipt(){
    const auto&v=native_retained_device;native_require(v.held,"Completed idle device certificate required");
    return {{"held",true},{"device",v.device},{"instance",v.instance},{"epoch",v.epoch},
        {"driver_reserved_bytes",v.owner.reserved_bytes},{"driver_used_bytes",v.owner.used_bytes},
        {"driver_live_allocations",v.owner.live_allocations},{"mapping_owned",bool(v.owner.mapping_owned)},
        {"physical_owned",bool(v.owner.physical_owned)},{"global_capacity_measured",false},
        {"device_destroy_calls",0},{"driver_retire_calls",0},{"post_completion_GPU_operations",0},
        {"ordinary_process_close_required",true}};
}
''' + text[end:]
    text = replace_once(text, '        qwen_native_stage("paired_Down_native_GPU_completed_owners_retired_waiting_for_ordinary_close");',
        '''        native_retained_result["all_source_IO_completed"]=true;
        native_retained_result["IO_journal_closed"]=true;
        native_save(native_report,native_retained_result);
        qwen_native_stage("paired_Down_native_GPU_completed_idle_device_retained_waiting_for_ordinary_close");''')
    return text


def controls(proof_path, root):
    proof = load(proof_path)
    need(proof['completed'] and proof['positive_controls'] == 2 and proof['negative_controls'] == 17 and
         proof['device_destroy_calls'] == proof['driver_retire_calls'] == proof['PS5_operations'] == 0,
         'The completed nineteen new retained-device controls are required')
    expected = {Path(row['path']).name: row for row in proof['inputs_before']}
    for name, relative in (('retained_completed_device.h', 'native/app/retained_completed_device.h'),
                           ('retained_completed_device_test.cpp', 'tests/retained_completed_device_test.cpp')):
        need(record(root / relative) == expected[name], 'The qualified retained-device source changed')
    return record(proof_path)
