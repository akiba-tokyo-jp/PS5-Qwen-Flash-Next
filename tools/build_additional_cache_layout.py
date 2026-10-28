#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Enable only the restored-table, unloaded 134-slot numerical fixture."""
import argparse,copy,json,os,subprocess
from pathlib import Path
from shader_storage import record
from build_speculative_batch_probe import once
from audit_native_imports import audit
from native_dispatch import audit as dispatch
from driver_table_storage import audit_linked_storage
ROOT=Path(__file__).resolve().parents[1]


def generate(text):
    old='        qwen_app::require_resident_refill_policy(policy);'
    text=once(text,old,'''        qwen_app::require_first_generation_policy(policy,false);
        qwen_app::require_large_cache_layout_phase_scope(policy,startup.first_generation_validation,false,1);
        if(qwen_app::additional_cache_slots()!=134)throw std::runtime_error("This unloaded fixture qualifies exactly 134 slots");''')
    marker='        if(false)\n            isolated_large_cache_layout(startup,policy,native_resources_started);'
    text=once(text,marker,'''        isolated_large_cache_layout(startup,policy,native_resources_started);
        throw std::runtime_error("The isolated 134-slot fixture cannot enter model initialization");
''')
    at=text.index('        isolated_large_cache_layout(startup,policy,native_resources_started);')
    if text.index('restore_resident_tables_incrementally()')>at or text.index('        admit_shader_storage_CPU(policy,startup.admission_report,true,')>at:
        raise ValueError('Every original cold driver table must restore before Vulkan initialization')
    return text


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in('parent','workspace','cache','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();prior=json.loads(a.parent.read_text());frozen=list({r['path']:r for r in prior['inputs_before']+[prior['artifact']]}.values())
    for r in frozen:
        if record(r['path'])!=r:raise ValueError('Actual cache variant source changed: '+r['path'])
    a.out.mkdir(parents=True);(a.out/'tmp').mkdir();c=prior['compile_commands'][0].copy()
    logical=Path(c[c.index('-c')+1]);effective=Path(prior['additional_cache_geometry']['actual_entry']['path'])
    source=a.out/'resident-unloaded-cache134.private.cpp';source.write_text(generate(effective.read_text()),newline='\n')
    old=c[c.index('-o')+1];obj=a.out/'unloaded-cache134.o';c[c.index('-c')+1]=str(source);c[c.index('-o')+1]=str(obj)
    if '-MF'in c:c[c.index('-MF')+1]=str(a.out/'entry.private.d')
    c+=['-I',str(logical.parent)]
    link=[str(obj)if x==old else x for x in prior['link_command']];image=a.out/'qwen-native.pie.elf';link[link.index('-o')+1]=str(image)
    link=[('-Map='+str(a.out/'native-link.private.map'))if x.startswith('-Map=')else x for x in link]
    frozen +=[record(x)for x in(a.parent,Path(__file__),effective,logical,source)]
    for i,command in enumerate((c,link)):
        r=subprocess.run(command,cwd=ROOT,capture_output=True,timeout=600,env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp')))
        (a.out/f'{i}.private.log').write_bytes(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace')[-5000:])
        print(json.dumps(dict(cache_layout_build_step=i+1,total=2)),flush=True)
    for row in frozen:
        if record(row['path'])!=row:raise ValueError('Frozen unloaded cache source changed')
    receipt=copy.deepcopy(prior);receipt.update(artifact=record(image),compile_commands=[c],link_command=link,
        source_parent=record(a.parent),inputs_before=frozen+[record(obj)],
        additional_cache_layout=dict(active_slots=134,physical_planes=135,maximum_graphs=360,original_residues=30,
            layouts=4,model_loads=0,old_CPU_tables_restored_before_GPU=True,actual_entry=record(source),
            original_allocator_caps_and_GPU_completion_retained=True),
        lossless_driver_table_geometry=audit_linked_storage(image,prior['lossless_driver_tables']))
    target=a.out/'receipt.private.json';target.write_text(json.dumps(receipt,indent=2)+'\n')
    receipt['real_module_import_audit']=audit(a.workspace,a.cache,a.out)
    receipt['native_dispatch_audit']=dispatch(a.workspace,a.workspace/'driver-work/PS5-Vulkan-Inference-qwen-872cc126',image,a.out/'dispatch')
    if receipt['real_module_import_audit']['missing']or not receipt['native_dispatch_audit']['passed']:raise ValueError('Unloaded cache import/dispatch audit failed')
    target.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(dict(cache134_layout_native_build_complete=True,PS5_calls=0)),flush=True)


if __name__=='__main__':main()
