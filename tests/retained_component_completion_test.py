#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check that incomplete GPU work cannot qualify a retained-device close."""
import copy
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from retained_component_completion import validate_terminal

terminal=dict(completed=True,all_outputs_passed=True,unknown_completion=False,native_PS5=True,model_loads=0,
    all_GPU_resources_positively_retired=False,all_case_resources_positively_retired=True,
    all_source_IO_completed=True,IO_journal_closed=True,
    cases=[dict(layer=l,width=w,workgroup=g,positive_fence=True,all_case_resources_retired=True,
        all_outputs_passed=True,canaries_exact=True,mismatches=0,Vulkan_dispatches=1)
        for l in (0,23,47) for w in (1,2,30,32) for g in (64,128)],
    retained_completed_device=dict(held=True,device=1,instance=2,epoch=7,driver_used_bytes=1024,
        driver_reserved_bytes=2048,global_capacity_measured=False,device_destroy_calls=0,
        driver_retire_calls=0,post_completion_GPU_operations=0,ordinary_process_close_required=True))
assert validate_terminal(terminal)['epoch']==7
mutations=[lambda t:t.update(unknown_completion=True),lambda t:t.update(IO_journal_closed=False),
    lambda t:t.update(all_GPU_resources_positively_retired=True),lambda t:t['cases'].pop(),
    lambda t:t['cases'][0].update(positive_fence=False),lambda t:t['cases'][0].update(canaries_exact=False),
    lambda t:t['cases'][0].update(mismatches=1),lambda t:t['cases'][0].update(Vulkan_dispatches=0),
    lambda t:t['retained_completed_device'].update(epoch=0),
    lambda t:t['retained_completed_device'].update(post_completion_GPU_operations=1),
    lambda t:t['retained_completed_device'].update(global_capacity_measured=True),
    lambda t:t['retained_completed_device'].update(driver_used_bytes=4096)]
for change in mutations:
    t=copy.deepcopy(terminal);change(t)
    try: validate_terminal(t)
    except RuntimeError: pass
    else: raise AssertionError('Incomplete or differently owned work must refuse')
print('{"completed":true,"positive_controls":1,"negative_controls":12,"PS5_operations":0}')
