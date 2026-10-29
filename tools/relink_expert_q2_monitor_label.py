#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Relink only the CPU raster label; preserve every inference/cache/driver object."""
import argparse,copy,json,os,subprocess
from pathlib import Path
from active_native_inputs import active_link_inputs
from expert_q4 import record,require,write_json
from native_dispatch import audit as dispatch
from audit_native_imports import audit
from driver_table_storage import audit_linked_storage
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('parent','compile-control','workspace','cache','out'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();prior=json.loads(a.parent.read_text());control=json.loads(a.compile_control.read_text())
    require(prior['expert_q2_model']['passive_monitor'],'Only the separate mixed Expert monitor may be relabeled')
    frozen=active_link_inputs(prior)+[record(a.parent),record(a.compile_control),record(__file__)]
    for row in frozen:require(record(row['path'])==row,'Completed monitor input changed')
    old=next(x for x in prior['link_command']if Path(x).name.startswith('monitor_raster-')and x.endswith('.o'))
    command=next(c.copy()for c in control['compile_commands']if '-c'in c and Path(c[c.index('-c')+1]).name=='monitor_raster.cpp')
    captured_object=record(command[command.index('-o')+1]);selected_object=record(old)
    require(all(captured_object[k]==selected_object[k]for k in('bytes','sha256')),
        'The captured raster compile command must produce the exact selected control object')
    original=Path(command[command.index('-c')+1]);text=original.read_text()
    old_label='"ORIGINAL BF16 / INFERENCE MONITOR"';new_label='"GATE UP Q2_K / DOWN Q4_0 / BF16 F32"'
    require(text.count(old_label)==1,'One exact fixed BF16 raster label required')
    a.out.mkdir(parents=True,exist_ok=False);(a.out/'tmp').mkdir()
    source=a.out/'Q2-monitor-raster.private.cpp';source.write_text(text.replace(old_label,new_label,1),newline='\n')
    require(source.read_text().replace(new_label,old_label,1)==text,'No rendering behavior except label may change')
    obj=a.out/'Q2-monitor-raster.o';command[command.index('-c')+1]=str(source);command[command.index('-o')+1]=str(obj)
    if '-MF'in command:command[command.index('-MF')+1]=str(a.out/'raster.private.d')
    command+=['-I',str(original.parent)]
    image=a.out/'qwen-native.pie.elf';link=prior['link_command'].copy();require(link.count(old)==1,'One raster object required')
    link=[str(obj)if x==old else x for x in link];link[link.index('-o')+1]=str(image)
    link=[('-Map='+str(a.out/'native-link.private.map'))if x.startswith('-Map=')else x for x in link]
    frozen +=[record(original),record(source)]
    for i,args in enumerate((command,link)):
        result=subprocess.run(args,cwd=ROOT,capture_output=True,timeout=600,env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp')))
        (a.out/f'{i}.private.log').write_bytes(result.stdout+result.stderr);require(result.returncode==0,result.stderr.decode(errors='replace')[-4000:])
    for row in frozen:require(record(row['path'])==row,'Raster-only relink input changed')
    receipt=copy.deepcopy(prior);receipt.update(artifact=record(image),link_command=link,source_parent=record(a.parent),
        inputs_before=prior['inputs_before']+frozen+[record(obj)],lossless_driver_table_geometry=audit_linked_storage(image,prior['lossless_driver_tables']))
    receipt['expert_q2_model']['raster_label_relink']=dict(original=record(original),actual=record(source),object=record(obj),
        compile_command=command,only_one_literal_changed=True,all_inference_cache_and_driver_objects_unchanged=True)
    target=a.out/'receipt.private.json';write_json(target,receipt)
    receipt['real_module_import_audit']=audit(a.workspace,a.cache,a.out)
    receipt['native_dispatch_audit']=dispatch(a.workspace,a.workspace/'driver-work/PS5-Vulkan-Inference-qwen-872cc126',image,a.out/'dispatch')
    require(not receipt['real_module_import_audit']['missing'] and receipt['native_dispatch_audit']['passed'],'Actual callback/import audit required')
    write_json(target,receipt);print(json.dumps(dict(Q2_mixed_raster_label_only_relinked=True,inference_objects_unchanged=True,PS5_operations=0,CI_runs=0)),flush=True)
if __name__=='__main__':main()
