#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Inspect actual declared lifetimes and the first refused alias in two requests."""
import json,os,subprocess,sys
from pathlib import Path
import build_memory_quality_cohort as quality
from build_speculative_batch_probe import once
from expert_q4 import require,record,write_json
from finite_route_capacity import bind_route_capacity
from build_cache_capacity_1125 import literal
ROOT=Path(__file__).resolve().parents[1];original_link=quality.link
core_only=False;protect_input=False;four_pairs=False


def instrument(parent,out,variants,inputs):
    command,text=variants['entry']
    if four_pairs:
        prior=json.loads(Path(parent).read_text())
        for scope in (prior['all_Q2_optimized_monitor']['scope'],prior['expert_q2_model']['scope'],prior['output_Q8_normal']['probation_scope']):
            old=dict(scope,maximum_requests=8,HTTP_requests=0,VideoOut_starts=0,headless_fixed_quality=True,quality_failures_recorded_without_aborting=True)
            text=once(text,literal(old),literal(dict(old,maximum_requests=10)))
        text=once(text,'const unsigned request_count=8;','const unsigned request_count=10;')
        text=once(text,'const unsigned task=ordinal/2;','const unsigned task=ordinal<2?0:ordinal/2-1;')
    text=bind_route_capacity(text,10 if four_pairs else 2)
    text='#include <cstdint>\nextern "C" void qwen_app_overlap_select(bool);\nextern "C" void qwen_app_overlap_graph_stats(std::uint64_t*);\nextern "C" const char*qwen_app_overlap_alias_name(unsigned);\n'+text
    selection='ordinal>=2&&((task%2)?!repeat:repeat)'if four_pairs else'repeat'
    text=once(text,'            const auto current_hits_before=qwen_app_current_bundle_hits();','            const bool overlap_candidate='+selection+';qwen_app_overlap_select(overlap_candidate);\n            const auto current_hits_before=qwen_app_current_bundle_hits();')
    check='''            if(!result.request_reset_completed||geometry_error||value_error||!rows||
               (repeat&&rows!=reference_rows))throw std::runtime_error("Additional full F32 continuation validation failed");'''
    text=once(text,check,'''            if(!result.request_reset_completed||geometry_error||value_error||!rows||
               (repeat&&rows!=reference_rows)){
                std::uint64_t observed_overlap[10]{};qwen_app_overlap_stats(observed_overlap);
                write_fresh_report(startup.admission_report+".arm"+std::to_string(ordinal)+".F32-failure",{{"ordinal",ordinal},{"maximum_absolute_logit_error",max_error},{"rows",rows},{"reference_rows",reference_rows},{"geometry_error",geometry_error},{"value_error",value_error},{"request_reset_completed",result.request_reset_completed},{"same_tokens_and_bytes",result.token_ids==reference_ids&&result.output_bytes==reference_bytes},{"overlap_counts",std::vector<std::uint64_t>(observed_overlap,observed_overlap+10)}});
                throw std::runtime_error("Additional full F32 continuation validation failed");
            }''')
    text=once(text,'            row["quality_task"]=task;',
        '            std::uint64_t graph_stats[4]{};qwen_app_overlap_graph_stats(graph_stats);row["overlap_candidate"]=overlap_candidate;row["overlap_diagnostic"]={{"graph_counts",std::vector<std::uint64_t>(graph_stats,graph_stats+4)},{"writer",qwen_app_overlap_alias_name(0)},{"reader",qwen_app_overlap_alias_name(1)},{"input",qwen_app_overlap_alias_name(2)}};\n            row["quality_task"]=task;')
    return original_link(parent,out,dict(entry=(command,text)),[*inputs,Path(__file__),ROOT/'tools/finite_route_capacity.py',ROOT/'native/app/delivery_overlap.cpp'])


def main():
    global core_only,protect_input,four_pairs
    if '--core-only'in sys.argv:core_only=True;sys.argv.remove('--core-only')
    if '--protect-input'in sys.argv:protect_input=True;sys.argv.remove('--protect-input')
    if '--four-pairs'in sys.argv:four_pairs=True;sys.argv.remove('--four-pairs')
    require(four_pairs or('--only-task'in sys.argv and sys.argv[sys.argv.index('--only-task')+1]=='0'),'One diagnostic pair or four fixed pairs required')
    require(not four_pairs or'--only-task'not in sys.argv,'Four pairs must include every fixed task')
    parent=Path(sys.argv[sys.argv.index('--parent')+1]);out=Path(sys.argv[sys.argv.index('--out')+1]);prior=json.loads(parent.read_text());aux=out.with_name(out.name+'-aux');aux.mkdir(parents=True,exist_ok=False);(aux/'tmp').mkdir()
    runtime=ROOT/'native/app/delivery_overlap.cpp';old_hash=prior['delivery_overlap']['runtime_source']['sha256']
    archives=[parent.parent/'qualified-runtime-source.private.cpp',*[Path(r['path'])for r in prior['inputs_before']if Path(r['path']).name=='qualified-runtime-source.private.cpp'and r['sha256']==old_hash]]
    archives=[p for p in archives if p.exists()and record(p)['sha256']==old_hash];require(archives,'Exact pre-instrumentation runtime required');archive=archives[0]
    public_runtime=runtime
    runtime_text=public_runtime.read_text()
    if core_only:runtime_text=once(runtime_text,'"ffn_shexp_gated-%d"','"ffn_shexp-%d"')
    model_inputs=[];model_replacement=None
    if protect_input:
        model_meta=prior['ordered_overlap'];model_source=Path(model_meta['model_source']['path']);unity_source=Path(model_meta['model_unity']['path'])
        require(record(model_source)==model_meta['model_source']and record(unity_source)==model_meta['model_unity'],'Exact ordered model providers required')
        model_text=once(model_source.read_text(),'qwen_app_overlap_graph_set(ggml_tensor*,int);','qwen_app_overlap_graph_set(ggml_tensor*,int,ggml_tensor*);')
        model_text=once(model_text,'qwen_app_overlap_graph_set(ffn_shexp, il);','qwen_app_overlap_graph_set(ffn_shexp, il, cur);')
        new_model=aux/'protected-model.private.cpp';new_model.write_text(model_text,newline='\n');new_unity=aux/'protected-model-unity.cxx';new_unity.write_text(once(unity_source.read_text(),model_source.as_posix(),new_model.as_posix()),newline='\n')
        model_command=model_meta['auxiliary_commands']['model'].copy();old_model=model_meta['auxiliary_objects']['model']['path'];new_object=aux/'model.o';model_command[model_command.index('-c')+1]=str(new_unity);model_command[model_command.index('-o')+1]=str(new_object)
        if '-MF'in model_command:model_command[model_command.index('-MF')+1]=str(aux/'model.private.d')
        p=subprocess.run(model_command,capture_output=True,timeout=600,env=dict(os.environ,TMP=str(aux/'tmp'),TEMP=str(aux/'tmp')));(aux/'model-build.private.log').write_bytes(p.stdout+p.stderr);require(p.returncode==0,p.stderr.decode(errors='replace')[-1500:])
        model_replacement=(old_model,str(new_object));model_inputs=[model_source,unity_source,new_model,new_unity,new_object]
        runtime_text=once(runtime_text,'qwen_app_overlap_graph_set(ggml_tensor*t,int layer){','qwen_app_overlap_graph_set(ggml_tensor*t,int layer,ggml_tensor*input){')
        runtime_text=once(runtime_text,'if(!enabled)return;++graph_counts[0];','if(!enabled)return;if(!input)throw std::runtime_error("Shared input required");auto*root=input;while(root->view_src)root=root->view_src;ggml_set_output(root);ggml_set_output(input);++graph_counts[0];')
    if core_only or protect_input:
        runtime=aux/'runtime-variant.private.cpp';runtime.write_text(runtime_text,newline='\n')
    command=prior['delivery_overlap']['runtime_command'].copy();old_object=prior['delivery_overlap']['runtime_object']['path'];obj=aux/'runtime.o';command[command.index('-c')+1]=str(runtime);command[command.index('-o')+1]=str(obj)
    if '-MF'in command:command[command.index('-MF')+1]=str(aux/'runtime.private.d')
    p=subprocess.run(command,capture_output=True,timeout=600,env=dict(os.environ,TMP=str(aux/'tmp'),TEMP=str(aux/'tmp')));(aux/'build.private.log').write_bytes(p.stdout+p.stderr);require(p.returncode==0,p.stderr.decode(errors='replace')[-1500:])
    prior['inputs_before']=[r for r in prior['inputs_before']if Path(r['path'])!=public_runtime];prior['inputs_before'] +=[record(p)for p in (runtime,public_runtime,archive,obj,Path(__file__))];prior['link_command'][prior['link_command'].index(old_object)]=str(obj)
    if model_replacement:
        old,new=model_replacement;require(prior['link_command'].count(old)==1,'One actual model provider required');prior['link_command'][prior['link_command'].index(old)]=new;prior['inputs_before'] +=[record(p)for p in model_inputs]
        prior['protected_input_overlap']=dict(model_source=record(new_model),model_unity=record(new_unity),model_object=record(new_object),model_command=model_command,original_model_object=old,selected_ID_and_shared_input_lifetimes_protected=True,original_workspace_cap=48<<20,production_adopted=False)
    plan=ROOT/'native/app/delivery_overlap_plan.h';old_plan_archive=Path(prior['delivery_overlap']['backend_source']['path']).parent/'qualified-plan-before-imported-view.private.h'
    for row in prior['inputs_before']:
        if Path(row['path'])==plan and row['sha256']!=record(plan)['sha256']:require(record(old_plan_archive)['sha256']==row['sha256'],'Exact original dependency plan archive required')
    prior['inputs_before']=[r for r in prior['inputs_before']if Path(r['path'])!=plan];prior['inputs_before'] +=[record(plan),record(old_plan_archive)]
    prior['delivery_overlap'].update(runtime_source=record(runtime),runtime_object=record(obj),runtime_command=command);seed=aux/'seed.private.json';write_json(seed,prior)
    sys.argv[sys.argv.index('--parent')+1]=str(seed);quality.link=instrument;quality.main();path=out/'receipt.private.json';r=json.loads(path.read_text())
    r['cold_request']['actual_sources']['entry']=r['memory_quality_cohort']['actual_sources']['entry'];r['cold_request']['commands']['entry']=r['memory_quality_cohort']['commands']['entry']
    count=10 if four_pairs else 2
    if four_pairs:
        for key in ('normal_performance','output_Q8_normal','all_Q2_optimized_monitor','routing_sharing','routing_winners_normal','memory_quality_cohort'):
            for name in ('scope','model_scope','probation_scope'):
                if name in r[key]and isinstance(r[key][name],dict)and r[key][name].get('maximum_requests')==8:r[key][name]['maximum_requests']=10
        r['expert_q2_model']['scope']['maximum_requests']=10;r['memory_quality_cohort']['requests']=10;r['memory_quality_cohort']['independent_pairs']=5
    r['overlap_quality']=dict(requests=count,warmup_requests=2 if four_pairs else 0,fixed_tasks=4 if four_pairs else 1,diagnostic=not four_pairs,wall_speed_qualification=four_pairs,endpoint='ffn_shexp'if core_only else'ffn_shexp_gated',shared_input_lifetime_protected=protect_input,imported_view_alias_refusal=True,final_sigmoid_gating_and_add_retained_in_remaining_graph=core_only,full_F32_and_routes_exact_required=True,evidence_capacity=count,original_alias_refusal=True,production_adopted=False)
    write_json(path,r);write_json(out/'core-safety.private.json',dict(completed=True,kind='actual_overlap_lifetime_alias_diagnostic',finite_requests=count,original_guards=True,diagnostic_is_not_normal_timing=not four_pairs,candidate=record(path),PS5_operations=0,CI_runs=0))


if __name__=='__main__':main()
