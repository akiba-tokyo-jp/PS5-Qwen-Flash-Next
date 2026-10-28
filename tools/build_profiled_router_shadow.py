#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Add a bounded existing timestamp logger to the shadow cohort's warmup only."""
import argparse,copy,json,os,subprocess
from pathlib import Path
from shader_storage import record
from audit_native_imports import audit
from native_dispatch import audit as dispatch
from driver_table_storage import audit_linked_storage
from build_speculative_batch_probe import once
ROOT=Path(__file__).resolve().parents[1]
PROFILE=dict(schema='ps5-qwen-bounded-existing-kernel-profile-v1',enabled=True,profiled_request=0,
    timestamp_implementation='existing_ggml_vulkan',maximum_kernel_labels=256,
    timed_arms_profile_enabled=False,new_shader_or_driver_code=False)


def generate(text):
    text='#include "bounded_gpu_profile.h"\n'+text
    marker='        require_router_shadow_policy(policy);'
    text=once(text,marker,marker+'''\n        if(policy.at("native_kernel_profile")!=Json::parse(PROFILE))throw std::runtime_error("Exact warmup-only kernel profile scope required");
        if(setenv("GGML_VK_PERF_LOGGER","1",1)||setenv("GGML_VK_PERF_LOGGER_FREQUENCY","1",1))
            throw std::runtime_error("Existing serialized GPU timestamp logger must initialize before the backend");
        auto warmup_GPU_profile=std::make_unique<qwen_app::BoundedGpuProfile>();warmup_GPU_profile->start();
'''.replace('PROFILE',json.dumps(json.dumps(PROFILE,separators=(',',':')))))
    marker='            qwen_app::FirstGeneration trial(adapter);'
    text=once(text,marker,'            if(!ordinal)warmup_GPU_profile->clear_completed_scope();\n'+marker)
    marker='            const auto shadow_report=qwen_app::finish_router_shadow_request(context);'
    text=once(text,marker,marker+'\n            const auto kernel_profile=!ordinal?warmup_GPU_profile->finish():Json(nullptr);')
    return once(text,'{"actual_hidden_router",shadow_report},','{"actual_hidden_router",shadow_report},{"kernel_profile",kernel_profile},')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in('parent','workspace','cache','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();prior=json.loads(a.parent.read_text());frozen=list({r['path']:r for r in prior['inputs_before']+[prior['artifact']]}.values())
    for r in frozen:
        if record(r['path'])!=r:raise ValueError('Actual frozen shadow dependency changed: '+r['path'])
    a.out.mkdir(parents=True);(a.out/'tmp').mkdir();c=prior['compile_commands'][0].copy();template=Path(c[c.index('-c')+1])
    for h in template.parent.glob('*.h'):(a.out/h.name).write_bytes(h.read_bytes())
    h=ROOT/'native/app/bounded_gpu_profile.h';(a.out/h.name).write_bytes(h.read_bytes())
    source=a.out/'resident-profiled-shadow.private.cpp';source.write_text(generate(template.read_text()),newline='\n')
    obj=a.out/'profiled-shadow.o';old=c[c.index('-o')+1];c[c.index('-c')+1]=str(source);c[c.index('-o')+1]=str(obj)
    c[1:1]=['-I',str(a.out)];c+=['-I',str(template.parent)]
    if prior['link_command'].count(old)!=1:raise ValueError('One exact actual entry replacement required')
    link=[str(obj)if x==old else x for x in prior['link_command']];image=a.out/'qwen-native.pie.elf';link[link.index('-o')+1]=str(image)
    link=[('-Map='+str(a.out/'native-link.private.map'))if x.startswith('-Map=')else x for x in link]
    frozen +=[record(x)for x in(a.parent,Path(__file__),h,template,source,*a.out.glob('*.h'))]
    for i,command in enumerate((c,link)):
        r=subprocess.run(command,cwd=ROOT,capture_output=True,timeout=600,env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp')))
        (a.out/f'{i}.private.log').write_bytes(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace')[-5000:])
        print(json.dumps(dict(profiled_shadow_build_step=i+1,total=2)),flush=True)
    for r in frozen:
        if record(r['path'])!=r:raise ValueError('Frozen profile source changed')
    receipt=copy.deepcopy(prior);receipt.update(artifact=record(image),compile_commands=[c],link_command=link,source_parent=record(a.parent),
        inputs_before=frozen+[record(obj)],bounded_kernel_profile=dict(scope=PROFILE,actual_entry=record(source),header=record(h)),
        lossless_driver_table_geometry=audit_linked_storage(image,prior['lossless_driver_tables']))
    path=a.out/'receipt.private.json';path.write_text(json.dumps(receipt,indent=2)+'\n')
    receipt['real_module_import_audit']=audit(a.workspace,a.cache,a.out)
    receipt['native_dispatch_audit']=dispatch(a.workspace,a.workspace/'driver-work/PS5-Vulkan-Inference-qwen-872cc126',image,a.out/'dispatch')
    if receipt['real_module_import_audit']['missing']or not receipt['native_dispatch_audit']['passed']:raise ValueError('Profiled shadow import/dispatch failed')
    path.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(dict(profiled_shadow_native_build_complete=True,PS5_calls=0)),flush=True)


if __name__=='__main__':main()
