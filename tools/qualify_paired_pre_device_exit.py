#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Classify a restored exited fixture before device creation; permit CPU readmission only."""
import argparse
import json
from pathlib import Path
import re

from build_performance_quantizer import record
from native_dispatch import ELF
from start_success_route import load,need,save
from success_case_control import lan_module


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('current','case','archive','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();case=load(a.case/'plan.private.json');first=load(a.case/'ongoing-first.private.json')
    restoration=load(a.case/'process-exited-restoration/result.private.json');archived=load(a.archive)
    need(restoration['completed'] and restoration['exact_current_seven_restored_and_native_hashed'] and
         archived['completed'] and archived['closed_owner_PID']==first['pid'] and archived['whole_native_and_host_SHA256_equal'],
         'Positive process exit, exact current restoration and complete closed journal required')
    need(record(archived['archived_log']['path'])==archived['archived_log'],'Closed complete log changed')
    log=Path(archived['archived_log']['path']).read_text()
    need(log.startswith('QWEN_NATIVE_LOG_READY pid='+str(first['pid'])+' ') and not re.search(r'kick|submit|completed_epoch|fault_retained',log,re.I),
         'A submitted/uncertain GPU epoch cannot use pre-device CPU readmission')
    allocations=re.findall(r'RETURN perBO_AllocateDirect serial=(\d+) rc=0x00000000 physical=\d+ canary=1 known_owner=1',log)
    mappings=re.findall(r'RETURN perBO_MapDirect serial=(\d+) rc=0x00000000 pointer=\w+ canary=1 known_mapping=1 placement_valid=1 GPU_readback_proven=0',log)
    need(allocations==mappings==['1','2'] and len(re.findall(r'^BEFORE ',log,re.M))==5 and len(re.findall(r'^RETURN ',log,re.M))==5,
         'All two allocation/map syscalls and the query must be positively returned; retirement is not claimed')
    stages=Path(a.case/'same-owner-stage-review.private.log').read_text()
    need(stages.splitlines()[-1]=='Vulkan_instance_creation_completed' and
         'Vulkan_before_native_device_creation' not in stages and 'Vulkan_native_device_registered' not in stages,
         'The durable source-bound before-CreateDevice marker must be absent')
    package=load(case['package']['path']);linked=load(package['relink']['path']);image=linked['artifact']
    need(record(image['path'])==image and record(linked['source']['path'])==linked['source'],'Actual failed native source/image changed')
    source=Path(linked['source']['path']).read_text()
    need(source.index('ok(enumerate(instance,&count,nullptr)')<source.index('properties_of(candidate,&p)')<
         source.index('ok(create_device(physical,&di,nullptr,&device)') and
         source.index('native_component_prepare();API a(false)')<source.index('for(const auto&shader:'),
         'The actual component must create a device before any case or queue work')
    e=ELF(Path(image['path']));need('vk_common_GetPhysicalDeviceProperties2' not in e.symbols,
         'The actual failed image must contain the observed callback omission')
    lan=lan_module()
    with lan.OPENER.open('http://'+lan.HOST+':8084/processes_list',timeout=8) as response:raw=response.read(1<<20)
    need(not [r for r in json.loads(raw)['processes'] if r['name']=='eboot.bin' or r['pid']==first['pid']],
         'No native process may remain')
    state=load(a.current/'active-console.private.json')
    need(state['original_restored'] and not state['native_running'] and not state['model_loaded'] and
         state['GPU_retirement_readmission_pending'],'Only the restored pending CPU readmission state is admitted')
    a.out.mkdir(parents=True,exist_ok=False);(a.out/'processes.private.json').write_bytes(raw)
    save(a.out/'result.private.json',dict(completed=True,case=record(a.case/'plan.private.json'),
        restored=record(a.case/'process-exited-restoration/result.private.json'),archive=record(a.archive),
        stages=record(a.case/'same-owner-stage-review.private.log'),failed_image=image,failed_source=linked['source'],
        known_pre_device_process_exit=True,source_bound_frontend_queue_submissions=0,
        complete_driver_journal_contains_no_submission=True,known_returned_BO_allocations=2,known_mapped_BO_bytes=16793600,
        BO_retirement_claimed=False,normal_exit_claimed=False,precise_process_exit_cause_observed=False,
        missing_required_callback='vk_common_GetPhysicalDeviceProperties2',current_boot=state['current_boot'],
        only_capacity_CPU_readmission_permitted=True,GPU_execution_permitted=False,title_launches=0,GPU_calls=0))
    print(json.dumps(dict(completed=True,known_pre_device_exit=True,BO_allocations=2,BO_retirement_claimed=False,CPU_readmission_only=True)))


if __name__=='__main__':main()
