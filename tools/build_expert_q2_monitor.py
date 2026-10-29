#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Relink only the passive mixed-Expert monitor entry; never deploy or execute."""
import argparse,copy,json,os,subprocess
from pathlib import Path
from active_native_inputs import active_link_inputs
from expert_q4 import record,require,write_json
from expert_q2_monitor_source import MONITOR_SCOPE,monitor_entry_source
from driver_table_storage import audit_linked_storage
from audit_native_imports import audit
from native_dispatch import audit as dispatch
R=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('parent','workspace','cache','out'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();prior=json.loads(a.parent.read_text());parent=Path(prior['expert_q2_model']['actual_entry']['path'])
    require(prior['expert_q2_model'].get('complete_prefix_metadata') and
            prior['expert_q2_model']['GPU_math_and_provider_objects_unchanged'],'Complete-prefix mixed parent required')
    frozen=active_link_inputs(prior)+[record(a.parent),record(parent),record(__file__),
        record(R/'tools/expert_q2_monitor_source.py'),record(R/'tools/expert_q4_monitor_source.py')]
    for row in frozen:require(record(row['path'])==row,'Qualified monitor parent changed')
    a.out.mkdir();(a.out/'tmp').mkdir();source=a.out/'Expert-Q2-monitor.private.cpp'
    source.write_text(monitor_entry_source(parent.read_text()),newline='\n')
    cmd=prior['compile_commands'][0].copy();obj=a.out/'entry.o';old=cmd[cmd.index('-o')+1]
    cmd[cmd.index('-c')+1]=str(source);cmd[cmd.index('-o')+1]=str(obj)
    if '-MF'in cmd:cmd[cmd.index('-MF')+1]=str(a.out/'entry.private.d')
    cmd+=['-I',str(parent.parent)]
    require(prior['link_command'].count(old)==1,'One exact monitor entry replacement required')
    link=[str(obj)if x==old else x for x in prior['link_command']];image=a.out/'qwen-native.pie.elf';link[link.index('-o')+1]=str(image)
    link=[('-Map='+str(a.out/'native-link.private.map'))if x.startswith('-Map=')else x for x in link]
    frozen.append(record(source))
    for i,command in enumerate((cmd,link)):
        x=subprocess.run(command,cwd=R,capture_output=True,timeout=600,env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp')))
        (a.out/f'{i}.private.log').write_bytes(x.stdout+x.stderr);require(x.returncode==0,x.stderr.decode(errors='replace')[-5000:])
        print(json.dumps(dict(mixed_monitor_build_step=i+1,total=2)),flush=True)
    for row in frozen:require(record(row['path'])==row,'A frozen monitor input changed')
    result=copy.deepcopy(prior);result.update(artifact=record(image),compile_commands=[cmd],link_command=link,
        source_parent=record(a.parent),inputs_before=prior['inputs_before']+frozen+[record(obj)],
        lossless_driver_table_geometry=audit_linked_storage(image,prior['lossless_driver_tables']))
    result['expert_q2_model'].update(actual_entry=record(source),scope=MONITOR_SCOPE,passive_monitor=True,
        HTTP_requests=2,VideoOut_starts=1,same_Q2_reference_from_completed_warmup=True,normal_application_validation_pending=True)
    write_json(a.out/'receipt.private.json',result)
    result['real_module_import_audit']=audit(a.workspace,a.cache,a.out)
    result['native_dispatch_audit']=dispatch(a.workspace,a.workspace/'driver-work/PS5-Vulkan-Inference-qwen-872cc126',image,a.out/'dispatch')
    require(not result['real_module_import_audit']['missing']and result['native_dispatch_audit']['passed'],'Mixed monitor import/dispatch audit failed')
    write_json(a.out/'receipt.private.json',result)
    print(json.dumps(dict(mixed_monitor_built=True,PS5_operations=0,CI_runs=0)),flush=True)

if __name__=='__main__':main()
