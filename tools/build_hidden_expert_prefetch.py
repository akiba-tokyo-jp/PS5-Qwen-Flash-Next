#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build a same-shadow-graph off/on/on/off one-Expert read comparison."""
import argparse,copy,json,os,subprocess
from pathlib import Path
from shader_storage import record
from build_speculative_batch_probe import once
from hidden_expert_source import moe_source,callback_header,entry_source
from audit_native_imports import audit
from native_dispatch import audit as dispatch
from driver_table_storage import audit_linked_storage
ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in('parent','workspace','cache','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();prior=json.loads(a.parent.read_text());frozen=list({r['path']:r for r in prior['inputs_before']+[prior['artifact']]}.values())
    for r in frozen:
        if record(r['path'])!=r:raise ValueError('Frozen actual shadow input changed: '+r['path'])
    a.out.mkdir(parents=True);(a.out/'tmp').mkdir();shadow=prior['actual_router_shadow']
    original=Path(shadow['actual_entry']['path'])
    for h in original.parent.glob('*.h'):(a.out/h.name).write_bytes(h.read_bytes())
    scope=copy.deepcopy(shadow['scope']);scope.update(schema='ps5-qwen-hidden-Expert-prefetch-v1',speculative_reads=1,
        maximum_predicted_experts_per_decode=1,shadow_graph_enabled_in_all_arms=True,old_route_forecast_disabled=True)
    h=a.out/'speculative_behavior_policy.h';s=h.read_text()
    s=once(s,json.dumps(json.dumps(shadow['scope'],separators=(',',':'))),json.dumps(json.dumps(scope,separators=(',',':'))))
    h.write_text(s,newline='\n')
    (a.out/'hidden_expert_prefetch.h').write_bytes((ROOT/'native/app/hidden_expert_prefetch.h').read_bytes())
    callback=a.out/'router_shadow_callback.h';callback.write_text(callback_header(callback.read_text()),newline='\n')
    main_src=a.out/'hidden-Expert-entry.private.cpp';main_src.write_text(entry_source(original.read_text()),newline='\n')
    overlay=prior['resident_context_reuse']['MoE']
    old_moe=Path(overlay['actual_source']['path']);moe=a.out/'hidden-Expert-moe.private.cpp';moe.write_text(moe_source(old_moe.read_text()),newline='\n')
    runtime=ROOT/'native/app/router_shadow_runtime.cpp'
    jobs=[(overlay['command'].copy(),moe),(shadow['commands'][1].copy(),runtime),(shadow['commands'][2].copy(),main_src)]
    commands=[];objects=[];replacements={}
    for i,(c,src)in enumerate(jobs):
        obj=a.out/f'{i}.o';old=c[c.index('-o')+1];c[c.index('-c')+1]=str(src);c[c.index('-o')+1]=str(obj)
        c[1:1]=['-I',str(a.out)];c+=['-I',str(original.parent),'-I',str(ROOT/'native/app')]
        if prior['link_command'].count(old)!=1:raise ValueError('One actual linked shadow/cache object is required: '+old)
        replacements[old]=str(obj);commands.append(c);objects.append(obj)
    link=[replacements.get(x,x)for x in prior['link_command']];image=a.out/'qwen-native.pie.elf';link[link.index('-o')+1]=str(image)
    link=[('-Map='+str(a.out/'native-link.private.map'))if x.startswith('-Map=')else x for x in link]
    frozen +=[record(x)for x in(a.parent,Path(__file__),ROOT/'tools/hidden_expert_source.py',ROOT/'native/app/hidden_expert_prefetch.h',old_moe,original,runtime,main_src,moe,*a.out.glob('*.h'))]
    for i,c in enumerate(commands+[link]):
        r=subprocess.run(c,cwd=ROOT,capture_output=True,timeout=600,env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp')))
        (a.out/f'{i}.private.log').write_bytes(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace')[-5500:])
        print(json.dumps(dict(hidden_Expert_build_step=i+1,total=4)),flush=True)
    for r in frozen:
        if record(r['path'])!=r:raise ValueError('Frozen hidden Expert source changed')
    receipt=copy.deepcopy(prior);receipt.update(artifact=record(image),compile_commands=[commands[-1]],link_command=link,source_parent=record(a.parent),inputs_before=frozen+[record(x)for x in objects],
        hidden_Expert_prefetch=dict(scope=scope,actual_entry=record(main_src),actual_MoE=record(moe),actual_MoE_object=record(objects[0]),commands=commands,
            original_three_role_BF16_bank_leases=True,main_producer_registration=True,worker_frontend_calls=False,
            original_maximum_two_outstanding_source_reads_preserved=True,same_shadow_graph_in_control_and_candidate=True),
        lossless_driver_table_geometry=audit_linked_storage(image,prior['lossless_driver_tables']))
    # The mandatory immutable provenance rebinder records this new override
    # before SELF packaging; original source manifests remain unchanged.
    b=receipt['bounded_model_source_overrides'];b['actual_hidden_Expert_overlay']=dict(actual_source=record(moe),actual_object=record(objects[0]),compile_command=commands[0],original=copy.deepcopy(overlay))
    target=a.out/'receipt.private.json';target.write_text(json.dumps(receipt,indent=2)+'\n')
    receipt['real_module_import_audit']=audit(a.workspace,a.cache,a.out)
    receipt['native_dispatch_audit']=dispatch(a.workspace,a.workspace/'driver-work/PS5-Vulkan-Inference-qwen-872cc126',image,a.out/'dispatch')
    if receipt['real_module_import_audit']['missing']or not receipt['native_dispatch_audit']['passed']:raise ValueError('Hidden Expert native audit failed')
    target.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(dict(hidden_Expert_native_build_complete=True,PS5_calls=0)),flush=True)


if __name__=='__main__':main()
