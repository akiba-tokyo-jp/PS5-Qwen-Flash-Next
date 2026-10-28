#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build the actual post-PLE router shadow and its matched observation cohort."""
import argparse,copy,json,os,re,subprocess
from pathlib import Path
from audit_native_imports import audit
from driver_table_storage import audit_linked_storage
from native_dispatch import audit as dispatch
from shader_storage import record
from build_speculative_behavior import LOOP,SCOPE as BEHAVIOR_SCOPE
from build_speculative_batch_probe import once
from router_shadow_source import model_source,engine_source
ROOT=Path(__file__).resolve().parents[1]
SCOPE=dict(BEHAVIOR_SCOPE,schema='ps5-qwen-actual-router-shadow-v1',maximum_requests=5,
    forced_rejection_requests=0,warmup_requests=1,matched_arms_per_candidate=4,
    selected_layer=23,speculative_reads=0,graph_reuse_disabled_in_both_arms=True)


def entry_source(text):
    text='#include "router_shadow_runtime.h"\n'+text
    text=text.replace('require_wide_verification_policy(policy);','require_router_shadow_policy(policy);')
    marker='int main(int argc, char ** argv)'
    text=once(text,marker,'''static std::uint64_t shadow_clock(){return std::uint64_t(std::chrono::duration_cast<std::chrono::nanoseconds>(qwen_app::ProfileClock::now().time_since_epoch()).count());}
'''+marker)
    marker='        context = llama_init_from_model(model, qwen_app::streaming_context_params(\n            true ? qwen_app::first_context_tokens : 4096, cache_bytes, prefill_tokens));'
    text=once(text,marker,'''        if(setenv("LLAMA_GRAPH_REUSE_DISABLE","1",1))throw std::runtime_error("Both shadow arms require explicit graph rebuilding");
        auto shadow_context_params=qwen_app::streaming_context_params(
            true ? qwen_app::first_context_tokens : 4096,cache_bytes,prefill_tokens);
        shadow_context_params.cb_eval=qwen_app::evaluate_router_shadow;shadow_context_params.cb_eval_user_data=nullptr;
        context=llama_init_from_model(model,shadow_context_params);''')
    s=LOOP.replace('routes.reserve(28)','routes.reserve(5)').replace('ordinal>=28','ordinal>=5')
    s=once(s,'const bool control=kind=="ordinary",adaptive=kind=="causal",reject=kind=="forced-rejection",coverage=kind=="accepted-coverage";',
        'const bool control=ordinal==0,adaptive=false,reject=false,coverage=false;')
    marker='            qwen_app::FirstGeneration trial(adapter);'
    s=once(s,marker,'''            auto shadow_device=ggml_backend_dev_by_type(GGML_BACKEND_DEVICE_TYPE_GPU);
            if(!shadow_device)shadow_device=ggml_backend_dev_by_type(GGML_BACKEND_DEVICE_TYPE_IGPU);
            if(!shadow_device)throw std::runtime_error("Original GPU owner required for actual hidden-router observation");
            qwen_app::start_router_shadow_request(context,ordinal+1,kind=="shadow",ggml_backend_dev_buffer_type(shadow_device),
                require_model_CPU_budget,shadow_clock,qwen_native_driver_checkpoint);
'''+marker)
    marker='            require_model_CPU_budget();require_unchanged_model();\n            bool exact='
    s=once(s,marker,'            const auto shadow_report=qwen_app::finish_router_shadow_request(context);\n'+marker)
    s=once(s,'{"completed_performance",performance_difference(perf,*engine)},',
        '{"completed_performance",performance_difference(perf,*engine)},{"actual_hidden_router",shadow_report},')
    s=s.replace('{"speed_measurement",false}','{"speed_measurement",ordinal>0}')
    begin=s.index('        for(unsigned group=0;group<8;++group){')
    s=s[:begin]+'''        run_arm(0,"warmup",0);run_arm(0,"off",0);run_arm(0,"shadow",0);
        run_arm(0,"shadow",0);run_arm(0,"off",0);
        coverage_complete=true;
'''
    begin=text.index('        const auto run=policy.at("native_first_generation_validation")',text.index('int main('))
    end=text.index('        qwen_app_complete_predictive_expert();qwen_native_driver_begin();',begin)
    text=text[:begin]+s+text[end:]
    text=text.replace('{"width_four_native_qualification",true}',
        '{"width_four_native_qualification",false},{"actual_router_shadow_comparison",true},{"matched_ABBA_ordinals",Json::array({1,2,3,4})}')
    text=text.replace('{"all_three_rejection_positions_executed",true}','{"all_three_rejection_positions_executed",false}')
    text=text.replace('{"speed_measurement",false}','{"speed_measurement",true}')
    return text


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in('parent','application-recipe','workspace','cache','out'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();prior=json.loads(a.parent.read_text());app=json.loads(a.application_recipe.read_text())
    frozen=list({r['path']:r for r in prior['inputs_before']+[prior['artifact']]}.values())
    for r in frozen:
        if record(r['path'])!=r:raise ValueError('Actual frozen router parent changed: '+r['path'])
    a.out.mkdir(parents=True);(a.out/'tmp').mkdir()
    entry_command=prior['compile_commands'][0].copy();template=Path(entry_command[entry_command.index('-c')+1])
    for path in template.parent.glob('*.h'):(a.out/path.name).write_bytes(path.read_bytes())
    source=a.out/'resident-actual-router-shadow.private.cpp';source.write_text(entry_source(template.read_text()),newline='\n')
    workloads=prior['wide_verification']['workloads']
    header=a.out/'speculative_behavior_policy.h';header.write_text('''#pragma once
#include "resident_comparison_policy.h"
inline void require_router_shadow_policy(const nlohmann::json&p){
 qwen_app::require_first_generation_policy(p,false);
 if(p.at("native_resident_comparison")!=nlohmann::json::parse(SCOPE)||
 p.at("native_speculative_workloads")!=nlohmann::json::parse(INPUTS)||
 p.at("native_prefill").at("tokens")!=4||p.at("native_padded_expert_cache").at("active_slots")!=53||
 p.contains("native_large_cache_scope")||p.contains("native_predictive_cache")||p.contains("native_model_free_speculation"))
 throw std::runtime_error("Exact actual-router off/on/on/off observation scope required");
}
'''.replace('SCOPE',json.dumps(json.dumps(SCOPE,separators=(',',':')))).replace('INPUTS',json.dumps(json.dumps(workloads,separators=(',',':')))),newline='\n')
    names=('router_shadow_runtime.h','router_shadow_callback.h','router_shadow_observer.h','router_shadow_graph.h')
    for name in names:(a.out/name).write_bytes((ROOT/'native/app'/name).read_bytes())
    up=a.cache/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569'
    engine=a.out/'llama_engine.actual-shadow.private.cpp';engine.write_text(engine_source((ROOT/'native/app/llama_engine.cpp').read_text()),newline='\n')
    recipe=next(c.copy()for c in app['compile_commands']if '-c'in c and Path(c[c.index('-c')+1]).name=='llama_engine.cpp')
    engine_recipe=prior['wide_verification']['commands'][0];old_engine=engine_recipe[engine_recipe.index('-o')+1]
    old_entry=entry_command[entry_command.index('-o')+1];commands=[];objects=[]
    for c,src in((recipe,engine),(recipe,ROOT/'native/app/router_shadow_runtime.cpp'),(entry_command,source)):
        c=c.copy();obj=a.out/(src.stem+'.o');c[c.index('-c')+1]=str(src);c[c.index('-o')+1]=str(obj)
        c[1:1]=['-I',str(a.out)];c+=['-I',str(template.parent),'-I',str(ROOT/'native/app'),'-I',str(up/'src')]
        commands.append(c);objects.append(obj)
    compile_database=a.cache/'build/llama-ps5/compile_commands.json';recipes=json.loads(compile_database.read_text())
    model=up/'src/models/qwen4exp.cpp'
    matches=[r for r in recipes if 'Unity'in Path(r['file']).parts and model.as_posix()in Path(r['file']).read_text()]
    if len(matches)!=1:raise ValueError('One exact original Qwen model unity recipe required')
    mr=matches[0];old_unity=Path(mr['file']);model_text=old_unity.read_text()
    model_view=a.out/'qwen4exp.actual-shadow.private.cpp';model_view.write_text(model_source(model.read_text()),newline='\n')
    unity=a.out/'actual-shadow-model-unity.cxx';unity.write_text(model_text.replace(model.as_posix(),model_view.as_posix()),newline='\n')
    model_obj=a.out/'actual-shadow-model-unity.o';mc=mr['command']
    old=str(old_unity.resolve());assert mc.count(old)==1
    mc=mc.replace(old,subprocess.list2cmdline([str(unity.resolve())]))
    mc,n=re.subn(r'(?<=\s)-o\s+(?:"[^"]+"|\S+)',lambda _:'-o '+subprocess.list2cmdline([str(model_obj.resolve())]),mc)
    if n!=1:raise ValueError('One exact model unity output required')
    mc+=' -I'+subprocess.list2cmdline([str(a.out)])+' -I'+subprocess.list2cmdline([str(model.parent)])
    replacements={old_entry:str(objects[2]),old_engine:str(objects[0])}
    if any(prior['link_command'].count(x)!=1 for x in replacements):raise ValueError('Exact actual engine/entry replacement required')
    link=[replacements.get(x,x)for x in prior['link_command']];at=next(i for i,x in enumerate(link)if x.endswith('libllama.a'))
    link[at:at]=[str(objects[1]),str(model_obj)]
    image=a.out/'qwen-native.pie.elf';link[link.index('-o')+1]=str(image)
    link=[('-Map='+str(a.out/'native-link.private.map'))if x.startswith('-Map=')else x for x in link]
    frozen +=[record(x)for x in(a.parent,a.application_recipe,Path(__file__),ROOT/'tools/router_shadow_source.py',
        ROOT/'native/app/router_shadow_runtime.cpp',ROOT/'native/app/llama_engine.cpp',compile_database,model,old_unity,model_view,unity,template,source,engine,
        *a.out.glob('*.h'),*(ROOT/'native/app'/n for n in names),*(Path(s)for s in re.findall(r'^#include "([^"]+)"',model_text,re.M)))]
    env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp'))
    jobs=[(c,ROOT)for c in commands]+[(mc,mr['directory']),(link,ROOT)]
    for i,(c,cwd)in enumerate(jobs):
        r=subprocess.run(c,cwd=cwd,capture_output=True,timeout=600,env=env);(a.out/f'{i}.private.log').write_bytes(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace')[-5000:])
        print(json.dumps(dict(actual_shadow_build_step=i+1,total=len(jobs))),flush=True)
    for r in frozen:
        if record(r['path'])!=r:raise ValueError('Frozen actual router source changed')
    receipt=copy.deepcopy(prior);receipt.update(artifact=record(image),compile_commands=[commands[-1]],link_command=link,
        source_parent=record(a.parent),inputs_before=frozen+[record(x)for x in[*objects,model_obj]],
        actual_router_shadow=dict(scope=SCOPE,workloads=workloads,commands=commands,model_command=mc,
            model_source=record(model_view),model_unity=record(unity),model_object=record(model_obj),actual_entry=record(source),
            actual_engine=record(engine),no_speculative_reads=True,original_F32_router_owner_reused=True),
        lossless_driver_table_geometry=audit_linked_storage(image,prior['lossless_driver_tables']))
    target=a.out/'receipt.private.json';target.write_text(json.dumps(receipt,indent=2)+'\n')
    receipt['real_module_import_audit']=audit(a.workspace,a.cache,a.out)
    receipt['native_dispatch_audit']=dispatch(a.workspace,a.workspace/'driver-work/PS5-Vulkan-Inference-qwen-872cc126',image,a.out/'dispatch')
    if receipt['real_module_import_audit']['missing']or not receipt['native_dispatch_audit']['passed']:raise ValueError('Actual router import/dispatch audit failed')
    target.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(dict(actual_router_shadow_native_build_complete=True,PS5_calls=0)),flush=True)


if __name__=='__main__':main()
