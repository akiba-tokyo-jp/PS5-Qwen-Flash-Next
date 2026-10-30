#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Observe current Top6 forecasts, actual residency and deadlines without prefetch."""
import argparse,copy,json,os,re,subprocess
from pathlib import Path
from build_speculative_batch_probe import once
from build_cache_capacity_1125 import literal,recipes
from expert_q4 import require,record,write_json
from scoped_native_variant import link,seal
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('parent','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();prior=json.loads(a.parent.read_text());require(prior['cold_request']['scope']['mode']=='profile','Exact current measurement control required');a.out.mkdir(parents=True,exist_ok=False);(a.out/'aux-tmp').mkdir()
    scope=dict(prior['cold_request']['scope'],mode='actual_router_deadline_observer',additional_GPU_operations=True,selected_forecast_layer=23,decode_forecast_width=1,speculative_reads=0,original_router_F32_weights=True)
    entry_command=prior['compile_commands'][0];entry=Path(entry_command[entry_command.index('-c')+1]).read_text();entry='#include "cold_router_forecast.h"\n'+entry
    entry=once(entry,literal(prior['cold_request']['scope']),literal(scope))
    entry=once(entry,'        context = llama_init_from_model(model, qwen_app::streaming_context_params(\n            true ? qwen_app::first_context_tokens : 4096, cache_bytes, prefill_tokens));',
        '        auto cold_context_params=qwen_app::streaming_context_params(true?qwen_app::first_context_tokens:4096,cache_bytes,prefill_tokens);\n        cold_context_params.cb_eval=qwen_app::evaluate_cold_forecast;cold_context_params.cb_eval_user_data=nullptr;\n        context=llama_init_from_model(model,cold_context_params);')
    entry=once(entry,'            const auto perf=performance_snapshot(*engine);','            qwen_app::cold_forecast_begin(context,ordinal,require_model_CPU_budget,qwen_native_driver_checkpoint);\n            const auto perf=performance_snapshot(*engine);')
    entry=once(entry,'            row["actual_graph_reuses"]=','            row["deadline_forecast"]=qwen_app::cold_forecast_finish(context);\n            row["actual_graph_reuses"]=')
    entry=once(entry,'{"GPU_operations_added", false}','{"GPU_operations_added", true}')
    cache_command=prior['routing_sharing']['commands'][1];cache=Path(cache_command[cache_command.index('-c')+1]).read_text();cache='#include "cold_router_forecast_bridge.h"\n'+cache
    cache=once(cache,'        size_t n_hit = 0;','        if(il==23&&ids.size()==6)qwen_app_cold_forecast_demand(unsigned(il),ids.data(),g.slru.slot_map[il]);\n        size_t n_hit = 0;')
    route_path=Path(prior['routing_sharing']['actual_sources']['routing']['path']);route_command=next(c for c in recipes(prior)if c[c.index('-c')+1]==str(route_path));routing=route_path.read_text()
    routing+='\nextern "C" bool qwen_app_cold_forecast_resident(unsigned layer,unsigned expert){if(layer>=48||expert>=512)throw std::runtime_error("Forecast residency exceeds model");return residency[layer*512+expert].load(std::memory_order_relaxed)!=0;}\n'
    up=a.cache/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569';model=up/'src/models/qwen4exp.cpp';database=a.cache/'build/llama-ps5/compile_commands.json';db=json.loads(database.read_text())
    matches=[r for r in db if 'Unity'in Path(r['file']).parts and model.as_posix()in Path(r['file']).read_text()];require(len(matches)==1,'One exact Qwen model unity required');recipe=matches[0]
    helper=a.out/'cold-router-graph.private.h';helper.write_text('''#pragma once
#include "ggml.h"
#include <stdexcept>
namespace qwen_app {
inline ggml_tensor*cold_router_graph(ggml_context*c,ggml_tensor*x,ggml_tensor*w){
    if(!c||!x||!w||x->type!=GGML_TYPE_F32||x->ne[0]!=2560||x->ne[1]!=1||w->type!=GGML_TYPE_F32||w->ne[0]!=2560||w->ne[1]!=512)
        throw std::runtime_error("Current forecast requires the original F32 router and one actual early hidden vector");
    auto*ids=ggml_argsort_top_k(c,ggml_soft_max(c,ggml_mul_mat(c,w,x)),6);ggml_set_output(ids);return ids;
}}
''',newline='\n')
    model_text=once(model.read_text(),'#include "models.h"','#include "models.h"\n#include "cold-router-graph.private.h"')
    marker='        ggml_build_forward_expand(gf, cur);\n\n        if (hparams.is_recr(il))'
    model_text=once(model_text,marker,'''        if(il==23&&n_tokens==1){auto*forecast=qwen_app::cold_router_graph(ctx0,cur,model.layers[il].ffn_gate_inp);
            cb(forecast,"cold_router_topk",il);ggml_build_forward_expand(gf,forecast);}
'''+marker)
    view=a.out/'qwen4exp.cold-forecast.private.cpp';view.write_text(model_text,newline='\n');unity=a.out/'cold-model-unity.cxx';unity.write_text(once(Path(recipe['file']).read_text(),model.as_posix(),view.as_posix()),newline='\n')
    model_object=a.out/'cold-model-unity.o';command=recipe['command'];old=str(Path(recipe['file']).resolve());require(command.count(old)==1,'One exact unity command input required')
    command=command.replace(old,subprocess.list2cmdline([str(unity.resolve())]));command,n=re.subn(r'(?<=\s)-o\s+(?:"[^"]+"|\S+)',lambda _:'-o '+subprocess.list2cmdline([str(model_object.resolve())]),command);require(n==1,'One unity output required')
    command+=' -I'+subprocess.list2cmdline([str(a.out)])+' -I'+subprocess.list2cmdline([str(model.parent)])
    runtime_command=prior['routing_sharing']['commands'][2].copy();runtime=ROOT/'native/app/cold_router_forecast.cpp';runtime_object=a.out/'cold-forecast-runtime.o'
    runtime_command[runtime_command.index('-c')+1]=str(runtime);runtime_command[runtime_command.index('-o')+1]=str(runtime_object);runtime_command[1:1]=['-I',str(up/'src'),'-I',str(ROOT/'native/app')]
    if '-MF'in runtime_command:runtime_command[runtime_command.index('-MF')+1]=str(a.out/'runtime.private.d')
    for i,(cmd,cwd)in enumerate(((command,recipe['directory']),(runtime_command,ROOT))):
        run=subprocess.run(cmd,cwd=cwd,capture_output=True,timeout=600,env=dict(os.environ,TMP=str(a.out/'aux-tmp'),TEMP=str(a.out/'aux-tmp')));(a.out/f'aux-{i}.private.log').write_bytes(run.stdout+run.stderr);require(run.returncode==0,run.stderr.decode(errors='replace')[-3500:]);print(json.dumps(dict(forecast_auxiliary_step=i+1,total=2)),flush=True)
    seed=copy.deepcopy(prior);at=next(i for i,v in enumerate(seed['link_command'])if v.endswith('libllama.a'));seed['link_command'][at:at]=[str(model_object),str(runtime_object)]
    frozen=[Path(__file__),ROOT/'native/app/cold_router_forecast.h',ROOT/'native/app/cold_router_forecast_bridge.h',runtime,model,Path(recipe['file']),view,unity,helper,database,model_object,runtime_object]
    seed['inputs_before'] +=[record(x)for x in frozen];seed_path=a.out/'seed.private.json';write_json(seed_path,seed)
    result,jobs,actual=link(seed_path,a.out,dict(entry=(entry_command,entry),cache=(cache_command,cache),routing=(route_command,routing)),frozen)
    for key in ('normal_performance','output_Q8_normal'):
        result[key]['actual_sources'].update(actual);result[key]['commands'].update(jobs)
    result['all_Q2_optimized_monitor']['actual_entry']=actual['entry'];result['all_Q2_optimized_monitor']['commands'][0]=jobs['entry'];result['routing_winners_normal']['actual_entry']=actual['entry']
    result['routing_sharing']['actual_sources']['routing']=actual['routing'];result['routing_sharing']['commands']=[jobs['routing']if c==route_command else c for c in result['routing_sharing']['commands']]
    result['cold_request']=dict(scope=scope,actual_sources=actual,commands=jobs,normal_validation_pending=True,production_adopted=False,original_driver_physical_kernel_heap_ledger_completion_guards=True,
        selected_layer=23,forecast_readback_bytes=24,speculative_IO_started=False,model_unity=record(unity),model_unity_object=record(model_object),runtime_object=record(runtime_object))
    seal(result,a.workspace,a.cache,a.out);write_json(a.out/'core-safety.private.json',dict(completed=True,kind='actual_top6_deadline_observer',driver_and_original_physical_reserves_preserved=True,candidate=record(a.out/'receipt.private.json'),PS5_operations=0,CI_runs=0))
    print(json.dumps(dict(built=True,actual_F32_router=True,Top6=True,speculative_reads=0)))
if __name__=='__main__':main()
