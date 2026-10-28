#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Bind snapshot ownership to the actual recreated API context, then relink."""
import argparse,copy,json,os,subprocess
from pathlib import Path
from shader_storage import record
from build_speculative_batch_probe import once
from audit_native_imports import audit
from native_dispatch import audit as dispatch
from driver_table_storage import audit_linked_storage
ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in('parent','workspace','cache','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();prior=json.loads(a.parent.read_text());monitor=prior['adaptive_monitor']
    for row in prior['inputs_before']+[prior['artifact']]:
        if record(row['path'])!=row:raise ValueError('Frozen combined input changed: '+row['path'])
    a.out.mkdir(parents=True);(a.out/'tmp').mkdir()
    original=Path(monitor['actual_entry']['path']);text=original.read_text()
    text=once(text,'            qwen_app::snapshot_replacement_budget.bind(context);\n','')
    marker='            engine = std::make_unique<qwen_app::LlamaEngine>(model, context, prefill_tokens);'
    # The first smoke context has already been normally retired at this point.
    text=once(text,marker,marker+'\n            qwen_app::snapshot_replacement_budget.bind(context);')
    source=a.out/'actual-recreated-context.private.cpp';source.write_text(text,newline='\n')
    command=monitor['commands'][1].copy();old_object=command[command.index('-o')+1];obj=a.out/'entry.o'
    command[command.index('-c')+1]=str(source);command[command.index('-o')+1]=str(obj);command+=['-I',str(original.parent)]
    image=a.out/'qwen-native.pie.elf';mapping=a.out/'native-link.private.map'
    link=[str(obj)if x==old_object else '-Map='+str(mapping)if x.startswith('-Map=')else x for x in prior['link_command']];link[link.index('-o')+1]=str(image)
    for i,c in enumerate((command,link)):
        r=subprocess.run(c,cwd=ROOT,capture_output=True,timeout=600,env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp')))
        (a.out/f'{i}.private.log').write_bytes(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace')[-4000:])
        print(json.dumps(dict(context_relink_step=i+1,total=2,unchanged_geometry_objects=13)),flush=True)
    receipt=copy.deepcopy(prior);receipt.update(artifact=record(image),compile_commands=[command],link_command=link,source_parent=record(a.parent))
    receipt['inputs_before'] += [record(a.parent),record(Path(__file__)),record(source),record(obj)]
    receipt['adaptive_monitor'].update(actual_entry=record(source),snapshot_owner_bound_after_API_context_recreation=True)
    receipt['adaptive_monitor']['commands'][1]=command
    g=receipt['additional_cache_geometry'];g['compiled'][1].update(object=record(obj),command=command,logical_source=record(source),compiled_source=record(source))
    g['actual_entry']=record(source);g['commands'][1]=command
    mapped=mapping.read_text()
    if not all(row['object']['path']in mapped for row in g['compiled']):raise ValueError('All selected geometry objects must occur in the new native map')
    g['actual_seven_override_map_proof']['map']=record(mapping)
    receipt['lossless_driver_table_geometry']=audit_linked_storage(image,prior['lossless_driver_tables'])
    target=a.out/'receipt.private.json';target.write_text(json.dumps(receipt,indent=2)+'\n')
    receipt['real_module_import_audit']=audit(a.workspace,a.cache,a.out)
    receipt['native_dispatch_audit']=dispatch(a.workspace,a.workspace/'driver-work/PS5-Vulkan-Inference-qwen-872cc126',image,a.out/'dispatch')
    if receipt['real_module_import_audit']['missing']or not receipt['native_dispatch_audit']['passed']:raise ValueError('Corrected context relink audit failed')
    target.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(dict(context_relinked=True,PS5_operations=0)),flush=True)
if __name__=='__main__':main()
