#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build selectable counting/adaptive passive profiles using closed native proofs."""
import argparse,copy,json,os,subprocess
from pathlib import Path
from shader_storage import record
from adaptive_monitor_source import engine_source,entry_source
from audit_native_imports import audit
from native_dispatch import audit as dispatch
from driver_table_storage import audit_linked_storage
ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in('parent','resident','wide-reference','speed-result','behavior-result','application-recipe','workspace','cache','out'):
        p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();prior=json.loads(a.parent.read_text());resident=json.loads(a.resident.read_text());reference=json.loads(a.wide_reference.read_text())
    speed=json.loads(a.speed_result.read_text());behavior=json.loads(a.behavior_result.read_text());app=json.loads(a.application_recipe.read_text())
    if not speed['completed']or not speed['all_model_source_device_owners_positively_retired']or speed['snapshot_replacements']<7 or speed['actual_snapshot_F32_sections']!=109:
        raise ValueError('Closed actual 128-slot multiple-replacement execution is required')
    if not behavior['completed']or not behavior['all_model_source_device_owners_positively_retired']or not behavior['eight_input_adaptive_behavior']:
        raise ValueError('Closed eight-input adaptive behavior is required')
    arms=speed['requests'];control=sum(arms[i]['decode_tokens_per_second']for i in(1,4))/2;candidate=sum(arms[i]['decode_tokens_per_second']for i in(2,3))/2
    if min(arms[i]['decode_tokens_per_second']for i in(2,3))<=max(arms[i]['decode_tokens_per_second']for i in(1,4)):
        raise ValueError('Both actual reverse-order adaptive arms must beat both controls')
    frozen=list({r['path']:r for data in(prior,resident,reference)for r in data['inputs_before']+[data['artifact']]}.values())
    for r in frozen:
        if record(r['path'])!=r:raise ValueError('Frozen adaptive monitor parent changed: '+r['path'])
    a.out.mkdir(parents=True);(a.out/'tmp').mkdir()
    base=Path(prior['speculative_monitor']['actual_entry']['path']);legacy=Path(prior['speculative_monitor']['actual_engine']['path'])
    for h in base.parent.glob('*.h'):(a.out/h.name).write_bytes(h.read_bytes())
    for h in Path(reference['adaptive_behavior']['actual_entry']['path']).parent.glob('*.h'):
        if h.name=='wide_batch_probe.h':(a.out/h.name).write_bytes(h.read_bytes())
    names=('adaptive_monitor_profile.h','causal_wide_engine.h','adaptive_draft_depth.h','model_free_span.h','wide_draft_control.h',
        'snapshot_replacement_runtime.h','snapshot_replacement_budget.h','snapshot_layout_witness.h')
    for name in names:(a.out/name).write_bytes((ROOT/'native/app'/name).read_bytes())
    input_record=resident['causal_wide']['workloads']['requests'][7]
    scope=dict(schema='ps5-qwen-causal-adaptive-monitor-v1',counting_control_available=True,adaptive_prompt=input_record['prompt'],
        context_tokens=256,prefill_tokens=4,active_cache_slots=128,maximum_output_tokens=32,maximum_actual_attempts=8,
        first_API_request='ordinary_complete_prefix_capture',second_API_request='final_prefix_restore_and_causal_adaptive',
        widths=[1,2,4],original_precision=True,allocator_caps_changed=False,persistent_caches=False,
        speed_evidence_SHA256=record(a.speed_result)['sha256'],behavior_evidence_SHA256=record(a.behavior_result)['sha256'])
    main_src=a.out/'adaptive-monitor.private.cpp';main_src.write_text(entry_source(base.read_text(),scope,input_record['prompt_token_ids'],input_record['expected_token_ids']),newline='\n')
    engine=a.out/'llama_engine.adaptive-monitor.private.cpp';engine.write_text(engine_source((ROOT/'native/app/llama_engine.cpp').read_text(),legacy.read_text()),newline='\n')
    # Quoted headers resolve next to their actual translation unit first. Copy
    # this source so the selected profile getter is compiled into the API too.
    demo_original=ROOT/'native/app/bounded_demo.cpp';demo=a.out/'bounded-demo.adaptive-profile.private.cpp'
    demo.write_text('#include "adaptive_monitor_profile.h"\n'+demo_original.read_text().replace('demo_prompt','adaptive_monitor_prompt()'),newline='\n')
    commands=[];objects=[];replacement={}
    for i,(src,c)in enumerate(((engine,prior['speculative_monitor']['commands'][0].copy()),(main_src,prior['speculative_monitor']['commands'][1].copy()))):
        obj=a.out/f'{i}.o';old=c[c.index('-o')+1];c[c.index('-c')+1]=str(src);c[c.index('-o')+1]=str(obj);c[1:1]=['-I',str(a.out)];c+=['-I',str(base.parent),'-I',str(ROOT/'native/app')]
        commands.append(c);objects.append(obj);replacement[old]=str(obj)
    dc=next(c.copy()for c in app['compile_commands']if '-c'in c and Path(c[c.index('-c')+1]).name=='bounded_demo.cpp')
    old_demo=[x for x in prior['link_command']if Path(x).name.startswith('bounded_demo-')and x.endswith('.o')]
    if len(old_demo)!=1:raise ValueError('One actual passive API object is required')
    dobj=a.out/'bounded-demo.o';dc[dc.index('-c')+1]=str(demo);dc[dc.index('-o')+1]=str(dobj);dc[1:1]=['-I',str(a.out)];dc+=['-I',str(ROOT/'native/app')]
    commands.append(dc);objects.append(dobj);replacement[old_demo[0]]=str(dobj)
    if any(prior['link_command'].count(x)!=1 for x in replacement):raise ValueError('Unique actual passive entry/engine/API replacements required')
    # Reuse the already compiled full four-row/state observer; it is dormant in
    # normal mode and cannot run a model or create a driver independently.
    probe_recipe=reference['adaptive_behavior']['commands'][1]
    helper=[probe_recipe[probe_recipe.index('-o')+1]]
    if reference['link_command'].count(helper[0])!=1:raise ValueError('The captured full-width observer must occur once in the actual link')
    if len(helper)!=1:raise ValueError('One exact qualified full-width state helper is required')
    link=[replacement.get(x,x)for x in prior['link_command']];link.insert(link.index(str(objects[0])),helper[0]);image=a.out/'qwen-native.pie.elf';link[link.index('-o')+1]=str(image)
    link=[('-Map='+str(a.out/'native-link.private.map'))if x.startswith('-Map=')else x for x in link]
    frozen +=[record(x)for x in(a.parent,a.resident,a.wide_reference,a.speed_result,a.behavior_result,a.application_recipe,Path(__file__),
        ROOT/'tools/adaptive_monitor_source.py',ROOT/'native/app/llama_engine.cpp',demo_original,base,legacy,main_src,engine,demo,*a.out.glob('*.h'),*(ROOT/'native/app'/n for n in names),helper[0])]
    for i,c in enumerate(commands+[link]):
        r=subprocess.run(c,cwd=ROOT,capture_output=True,timeout=600,env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp')))
        (a.out/f'{i}.private.log').write_bytes(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace')[-6000:])
        print(json.dumps(dict(adaptive_monitor_build_step=i+1,total=4)),flush=True)
    for r in frozen:
        if record(r['path'])!=r:raise ValueError('Frozen adaptive monitor source changed')
    receipt=copy.deepcopy(prior);receipt.update(artifact=record(image),compile_commands=[commands[1]],link_command=link,source_parent=record(a.parent),inputs_before=frozen+[record(x)for x in objects],
        adaptive_monitor=dict(scope=scope,actual_entry=record(main_src),actual_engine=record(engine),actual_API=record(demo),commands=commands,
            same_SELF_normal_and_diagnostic=True,original_counting_profile_preserved=True,read_only_native_and_web_UI=True,
            measured_repetition_decode_ratio=candidate/control,whole_model_speed_not_generalized=True),
        lossless_driver_table_geometry=audit_linked_storage(image,prior['lossless_driver_tables']))
    target=a.out/'receipt.private.json';target.write_text(json.dumps(receipt,indent=2)+'\n')
    receipt['real_module_import_audit']=audit(a.workspace,a.cache,a.out)
    receipt['native_dispatch_audit']=dispatch(a.workspace,a.workspace/'driver-work/PS5-Vulkan-Inference-qwen-872cc126',image,a.out/'dispatch')
    if receipt['real_module_import_audit']['missing']or not receipt['native_dispatch_audit']['passed']:raise ValueError('Adaptive monitor native audit failed')
    target.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(dict(adaptive_monitor_built=True,PS5_operations=0)),flush=True)


if __name__=='__main__':main()
