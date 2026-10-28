#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Price only new storage after the same complete snapshot positively returned."""
import argparse
import copy
import json
import os
from pathlib import Path
import subprocess
from audit_native_imports import audit
from driver_table_storage import audit_linked_storage
from native_dispatch import audit as dispatch
from shader_storage import record
ROOT=Path(__file__).resolve().parents[1]


def generate(text):
    text='#include "resident_checkpoint_capacity.h"\n'+text
    needle='        const auto admit_checkpoint=[&](std::uint64_t bytes){'
    if text.count(needle)!=1:raise ValueError('One complete prefix checkpoint admission required')
    text=text.replace(needle,'''        qwen_app::ResidentCheckpointCapacity checkpoint_capacity;
        std::uint64_t checkpoint_last_requested=0,checkpoint_last_new_bytes=0;
'''+needle)
    old='            const auto rounded=(bytes+(2u<<20)-1)&~std::uint64_t((2u<<20)-1);'
    start=text.index(needle);at=text.index(old,start)
    text=text[:at]+text[at:].replace(old,'''            const auto rounded=checkpoint_capacity.new_allocation(context,bytes);
            checkpoint_last_requested=bytes;checkpoint_last_new_bytes=rounded;''',1)
    old='''            if(ledger.live>qwen_app::model_postload_device_budget||rounded>qwen_app::model_postload_device_budget-ledger.live||
               budget.available<rounded+memory_budget.direct_reserve||observed_system_headroom()<memory_budget.flexible_reserve)
                throw std::runtime_error("Complete checkpoint cannot retain original reserves");'''
    replacement='''            const auto checkpoint_flexible=observed_system_headroom();
            if(ledger.live>qwen_app::model_postload_device_budget||rounded>qwen_app::model_postload_device_budget-ledger.live||
               budget.available<rounded+memory_budget.direct_reserve||checkpoint_flexible<memory_budget.flexible_reserve) {
                write_fresh_report(startup.admission_report+".resident.checkpoint-capacity-refusal",{
                    {"payload_bytes",bytes},{"new_allocation_bytes",rounded},{"ledger_live_bytes",ledger.live},
                    {"ledger_cap_bytes",qwen_app::model_postload_device_budget},{"Direct_available_bytes",budget.available},
                    {"Direct_reserve_bytes",memory_budget.direct_reserve},{"Flexible_available_bytes",checkpoint_flexible},
                    {"Flexible_reserve_bytes",memory_budget.flexible_reserve},{"original_caps_unchanged",true}});
                throw std::runtime_error("Complete checkpoint cannot retain original reserves");
            }'''
    if text.count(old)!=1:raise ValueError('The exact original independent resource caps are required')
    text=text.replace(old,replacement)
    marker='            const auto p=engine->prefix_reuse_stats();'
    at=text.index(marker,start)+len(marker)
    text=text[:at]+'''
            if(reuse&&!second) {
                const auto checkpoint=engine->checkpoint_validation_stats();
                if(p.captures!=1||!result.request_reset_completed||!checkpoint.maximum_payload_bytes||
                   checkpoint.maximum_payload_bytes!=checkpoint_last_requested)
                    throw std::runtime_error("Only an actual positively completed same-context snapshot can retain capacity");
                checkpoint_capacity.completed(context,checkpoint.maximum_payload_bytes,true);
            }
'''+text[at:]
    marker='            completed.push_back(row);write_fresh_report(report_prefix+".result",row);'
    text=text.replace(marker,'''            row["checkpoint_capacity"]={{"requested_payload_bytes",reuse?checkpoint_last_requested:0},
                {"new_allocation_bytes",reuse?checkpoint_last_new_bytes:0},{"same_context_qualified",true},
                {"original_device_Direct_and_Flexible_caps_unchanged",true}};
'''+marker)
    return text


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('parent','workspace','cache','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();prior=json.loads(a.parent.read_text())
    for row in prior['inputs_before']+[prior['artifact']]:
        if record(row['path'])!=row:raise ValueError('Original captured input changed: '+row['path'])
    a.out.mkdir(parents=True);(a.out/'tmp').mkdir()
    command=prior['compile_commands'][0].copy();template=Path(command[command.index('-c')+1])
    source=a.out/'resident-comparison-checkpoint-reuse.private.cpp';source.write_text(generate(template.read_text()),newline='\n')
    for name in ('resident_additional_policy.h','resident_refill_policy.h','resident_incremental_tables.h','resident_direct_tables.h'):
        (a.out/name).write_bytes((template.parent/name).read_bytes())
    header=ROOT/'native/app/resident_checkpoint_capacity.h';(a.out/header.name).write_bytes(header.read_bytes())
    obj=a.out/'checkpoint-reuse.o';old=command[command.index('-o')+1]
    command[command.index('-c')+1]=str(source);command[command.index('-o')+1]=str(obj)
    command[1:1]=['-I',str(a.out)];command+=['-I',str(template.parent)]
    link=[str(obj)if x==old else x for x in prior['link_command']];image=a.out/'qwen-native.pie.elf';link[link.index('-o')+1]=str(image)
    link=[('-Map='+str(a.out/'native-link.private.map'))if x.startswith('-Map=')else x for x in link]
    frozen=prior['inputs_before']+[record(x)for x in(a.parent,Path(__file__),template,source,header,*a.out.glob('*.h'))]
    for i,c in enumerate((command,link)):
        r=subprocess.run(c,cwd=ROOT,capture_output=True,timeout=600,env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp')))
        (a.out/f'{i}.private.log').write_bytes(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace')[-5000:])
    for row in frozen:
        if record(row['path'])!=row:raise ValueError('Frozen capacity-pricing source changed')
    receipt=copy.deepcopy(prior);receipt.update(artifact=record(image),compile_commands=[command],link_command=link,
        source_parent=record(a.parent),inputs_before=frozen+[record(obj)],
        checkpoint_capacity_reuse=dict(only_positively_completed_same_context_payload_credited=True,
            original_allocator_caps_unchanged=True,actual_entry=record(source),header=record(header)),
        lossless_driver_table_geometry=audit_linked_storage(image,prior['lossless_driver_tables']))
    receipt['resident_context_reuse']['entry']=record(source)
    receipt['prefix_cache128_combination']['actual_entry']=record(source)
    path=a.out/'receipt.private.json';path.write_text(json.dumps(receipt,indent=2)+'\n')
    receipt['real_module_import_audit']=audit(a.workspace,a.cache,a.out)
    receipt['native_dispatch_audit']=dispatch(a.workspace,a.workspace/'driver-work/PS5-Vulkan-Inference-qwen-872cc126',image,a.out/'dispatch')
    if receipt['real_module_import_audit']['missing']or not receipt['native_dispatch_audit']['passed']:raise ValueError('Native audit failed')
    path.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(dict(checkpoint_reuse_entry_built=True,PS5_operations=0)),flush=True)


if __name__=='__main__':main()
