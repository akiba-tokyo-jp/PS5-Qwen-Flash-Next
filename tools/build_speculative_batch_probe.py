#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build a diagnostic-only same-width reference without changing the engine ABI."""
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
SCOPE=dict(schema='ps5-qwen-same-batch-qualification-v1',enabled=True,maximum_probed_attempts=1,
    ordinary_references=2,state_observations=3,readback_window_bytes=65536,
    original_width_two_graph_and_class_layout=True,original_tolerance_unchanged=True,
    full_active_F32_KV_and_recurrent_state=True,speed_qualification=False,automatic_retries=0)

def once(text,old,new):
    if text.count(old)!=1:raise ValueError('Expected one exact native boundary: '+old[:90])
    return text.replace(old,new,1)

def engine_source(text):
    text='#include "speculative_batch_probe.h"\n'+text
    marker='            const llama_token pair[]={pending_,draft};'
    text=once(text,marker,marker+'''
            const bool same_batch_probe=speculative_batch_probe_requested();
            if(same_batch_probe) {
                process_batch_once(pair,2,position_);
                speculative_batch_probe_observe(0,context_,llama_get_logits_ith(context_,0),llama_get_logits_ith(context_,1));
                restore_checkpoint_in_active_epoch();
                process_batch_once(pair,2,position_);
                speculative_batch_probe_observe(1,context_,llama_get_logits_ith(context_,0),llama_get_logits_ith(context_,1));
                restore_checkpoint_in_active_epoch();
            }
''')
    marker='            const auto *first=llama_get_logits_ith(context_,0),*second=llama_get_logits_ith(context_,1);'
    text=once(text,marker,marker+'\n            if(same_batch_probe)speculative_batch_probe_observe(2,context_,first,second);')
    marker='            if(expert_hooks_.verified)expert_hooks_.verified(draft_accepted,capture_seconds,restore_seconds);'
    text=once(text,marker,'            if(same_batch_probe)speculative_batch_probe_decision(draft_accepted,position_,speculative_bonus_ready_);\n'+marker)
    return text

def entry_source(text):
    text='#include "speculative_batch_probe.h"\n'+text
    marker='        qwen_app::require_resident_comparison_policy(policy);'
    scope=json.dumps(json.dumps(SCOPE,separators=(',',':')))
    text=once(text,marker,marker+'\n        if(policy.at("native_speculative_same_batch_probe")!=Json::parse('+scope+'))throw std::runtime_error("Exact same-batch diagnostic scope required");')
    marker='        std::vector<float> reference_logits(resident_reference_rows*logit_columns);'
    text=once(text,marker,marker+'''
        qwen_app::SpeculativeBatchProbe same_batch_probe(logit_columns);
        std::vector<float> distribution_scratch(logit_columns);
''')
    marker='        for(unsigned ordinal=0;ordinal<arms.size();++ordinal) {'
    text=once(text,marker,marker+'\n            same_batch_probe.arm(ordinal==1);\n            Json distribution=Json::array();')
    marker='                    for(std::size_t i=0;i<count;++i){const double a=v[i],b=reference_logits[logits_seen*logit_columns+i],e=std::abs(a-b);'
    # Observations are preallocated. JSON is emitted only after the positive
    # request reset; the original noexcept callback remains allocation-free.
    marker2='            std::size_t callback_calls=0,first_bad_row=SIZE_MAX,first_bad_column=SIZE_MAX;'
    text=once(text,marker2,marker2+'\n            std::array<qwen_app::LogitDifference,23> row_differences{};')
    text=once(text,marker,'                    row_differences[logits_seen]=qwen_app::compare_logits(v,reference_logits.data()+logits_seen*logit_columns,count,distribution_scratch.data());\n'+marker)
    marker='            engine->set_logits_observer({});'
    text=once(text,marker,marker+'''
            if(ordinal)for(std::size_t i=0;i<logits_seen;++i)distribution.push_back(qwen_app::logit_difference_report(row_differences[i]));
            write_fresh_report(prefix+".logit-distribution",{{"rows",distribution},{"full_vocabulary",logit_columns},{"timing_qualification",false}});
            const auto same_batch_result=ordinal==1?same_batch_probe.report():Json(nullptr);
            if(ordinal==1)write_fresh_report(prefix+".same-batch",same_batch_result);
''')
    marker='            completed.push_back(row);write_fresh_report(prefix+".result",row);'
    text=once(text,marker,'            row["same_batch_probe"]=same_batch_result;\n'+marker)
    return text

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('parent','application-recipe','workspace','cache','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();prior=json.loads(a.parent.read_text());app=json.loads(a.application_recipe.read_text())
    frozen=list({row['path']:row for row in prior['inputs_before']+[prior['artifact']]}.values())
    for row in frozen:
        if record(row['path'])!=row:raise ValueError('Original frozen dependency changed: '+row['path'])
    a.out.mkdir(parents=True);(a.out/'tmp').mkdir()
    command=prior['compile_commands'][0].copy();template=Path(command[command.index('-c')+1])
    source=a.out/'resident-comparison-same-batch.private.cpp';source.write_text(entry_source(template.read_text()),newline='\n')
    for path in template.parent.glob('*.h'):(a.out/path.name).write_bytes(path.read_bytes())
    new_inputs=[ROOT/'native/app'/name for name in('logit_difference.h','speculative_batch_probe.h','speculative_batch_probe.cpp','llama_engine.cpp','llama_engine.h')]
    for path in new_inputs[:2]:(a.out/path.name).write_bytes(path.read_bytes())
    engine=a.out/'llama_engine.same-batch.private.cpp';engine.write_text(engine_source((ROOT/'native/app/llama_engine.cpp').read_text()),newline='\n')
    recipe=next(c.copy()for c in app['compile_commands']if '-c'in c and Path(c[c.index('-c')+1]).name=='llama_engine.cpp')
    old_main=command[command.index('-o')+1];old_engine=next(x for x in prior['link_command']if Path(x).name.startswith('llama_engine-')and x.endswith('.o'))
    commands=[];objects=[]
    for ordinal,(original,src)in enumerate(((recipe,engine),(recipe,ROOT/'native/app/speculative_batch_probe.cpp'),(command,source))):
        c=original.copy();obj=a.out/f'{ordinal}.o';c[c.index('-c')+1]=str(src);c[c.index('-o')+1]=str(obj)
        # Preserve the parent's scoped system-memory headers ahead of ordinary
        # repository headers. Only the new probe headers shadow this recipe.
        c[1:1]=['-I',str(a.out)];c+=['-I',str(template.parent),'-I',str(ROOT/'native/app')]
        commands.append(c);objects.append(obj)
    replacements={old_engine:str(objects[0]),old_main:str(objects[2])}
    link=[replacements.get(x,x)for x in prior['link_command']];link.insert(link.index(str(objects[0])),str(objects[1]))
    image=a.out/'qwen-native.pie.elf';link[link.index('-o')+1]=str(image)
    link=[('-Map='+str(a.out/'native-link.private.map'))if x.startswith('-Map=')else x for x in link]
    frozen +=[record(x)for x in(a.parent,a.application_recipe,Path(__file__),template,source,engine,*new_inputs,*a.out.glob('*.h'))]
    env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp'))
    for i,c in enumerate(commands+[link]):
        result=subprocess.run(c,cwd=ROOT,capture_output=True,timeout=600,env=env);(a.out/f'{i}.private.log').write_bytes(result.stdout+result.stderr)
        if result.returncode:raise RuntimeError(result.stderr.decode(errors='replace')[-6000:])
        print(json.dumps(dict(same_batch_build_step=i+1,total=len(commands)+1)),flush=True)
    for row in frozen:
        if record(row['path'])!=row:raise ValueError('Same-batch build input changed')
    receipt=copy.deepcopy(prior);receipt.update(artifact=record(image),compile_commands=[commands[-1]],link_command=link,
        source_parent=record(a.parent),inputs_before=frozen+[record(obj)for obj in objects],
        speculative_same_batch_qualification=dict(scope=SCOPE,actual_entry=record(source),actual_engine=record(engine),
            commands=commands,object_replacements=replacements,helper=record(new_inputs[2]),
            unchanged_class_header=record(new_inputs[-1]),ggml_engine_and_driver_objects_unchanged=True),
        lossless_driver_table_geometry=audit_linked_storage(image,prior['lossless_driver_tables']))
    receipt['post_context_OS_reserve']['original_engine_and_driver_objects_unchanged']=False
    receipt['post_context_OS_reserve']['original_driver_objects_unchanged']=True
    path=a.out/'receipt.private.json';path.write_text(json.dumps(receipt,indent=2)+'\n')
    receipt['real_module_import_audit']=audit(a.workspace,a.cache,a.out)
    receipt['native_dispatch_audit']=dispatch(a.workspace,a.workspace/'driver-work/PS5-Vulkan-Inference-qwen-872cc126',image,a.out/'dispatch')
    if receipt['real_module_import_audit']['missing']or not receipt['native_dispatch_audit']['passed']:raise ValueError('Native dispatch/import audit failed')
    path.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(dict(same_batch_diagnostic_built=True,PS5_operations=0)),flush=True)

if __name__=='__main__':main()
