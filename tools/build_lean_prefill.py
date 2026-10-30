#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build finite prefill comparisons from the exact qualified routing providers."""
import argparse,copy,json,os,subprocess
from pathlib import Path
from active_native_inputs import active_link_inputs
from expert_q4 import require,record,write_json
from build_speculative_batch_probe import once
from driver_table_storage import audit_linked_storage
from audit_native_imports import audit
from native_dispatch import audit as dispatch
from build_lean_prefill_cache_capacity import cache_source

ROOT=Path(__file__).resolve().parents[1]
COUNTING=[0,0,1,2,3,4,5,5,4,3,2,1,0]
ORDER=COUNTING+list(range(6))*3
SCOPE=dict(schema='ps5-qwen-lean-prefill-comparison-v1',enabled=True,
 maximum_requests=len(ORDER),order=ORDER,counting_requests=len(COUNTING),quality_requests=18,
 quality_tasks=3,model_loads=1,context_tokens=256,maximum_output_tokens=32,
 prefill_widths=[4,8,16],prefill_modes='all_outputs_or_one_tail_output_per_chunk',
 zero_output_batches=False,selected_routing_policy=6,decode_Experts=6,prefill_Experts=10,
 active_cache_slots=867,cache_budget_bytes=1333739520,selected_IO_flags=5,
 graph_reuse_disabled_uniformly=True,approximate_routing_changes_permitted=True,
 quality_changes_recorded_without_aborting=True,HTTP_requests=0,VideoOut_starts=0,
 automatic_retries=0,original_physical_heap_ledger_owner_completion_guards=True)

def engine_source(text):
 text='#include "lean_prefill_policy.h"\n'+text
 marker='namespace qwen_app {\nvoid configure_bf16_indexed_vector'
 declarations='''namespace {qwen_app::LeanPrefillPolicy lean_policy{4,false};qwen_app::LeanPrefillStats lean_stats;}
extern "C" void qwen_app_lean_prefill_configure(unsigned mode){lean_policy=qwen_app::lean_prefill_policy(mode);lean_stats={};}
extern "C" qwen_app::LeanPrefillStats qwen_app_lean_prefill_stats(){return lean_stats;}
'''
 text=once(text,marker,declarations+marker)
 text=once(text,'tokens != 1 && tokens != 2 && tokens != 4','tokens != 1 && tokens != 2 && tokens != 4 && tokens != 8 && tokens != 16')
 text=once(text,'    llama_batch_ext_clear(batch_);','''    llama_batch_ext_clear(batch_);
    if(inside_prefill_){++lean_stats.calls;lean_stats.input_tokens+=count;
        lean_stats.maximum_width=std::max<std::uint64_t>(lean_stats.maximum_width,count);}
''')
 text=once(text,'!llama_batch_ext_set_output_logits(batch_, index, true)',
  '!llama_batch_ext_set_output_logits(batch_, index, qwen_app::lean_prefill_output(lean_policy,inside_prefill_,i,count))')
 text=once(text,'    qwen_app_route_phase(!inside_prefill_);','''    if(inside_prefill_)lean_stats.output_rows+=lean_policy.last_output_only?1:count;
    qwen_app_route_phase(!inside_prefill_);''')
 return text

def entry_source(text,old,model_scope,IO_scope):
 text='#include "lean_prefill_policy.h"\n'+text
 for a,b in ((old['model_scope'],model_scope),(old['scope'],SCOPE)):
  text=once(text,json.dumps(json.dumps(a,separators=(',',':'))),json.dumps(json.dumps(b,separators=(',',':'))))
 text=once(text,'p.at("tokens").get<std::uint64_t>() > 4','p.at("tokens").get<std::uint64_t>() > 16')
 text=once(text,'p.at("schema") != "ps5-qwen-bounded-prefill-v1"','p.at("schema") != "ps5-qwen-lean-prefill-context-v1"')
 text=once(text,'p.at("all_prompt_outputs_requested") != true','p.at("all_prompt_outputs_requested") != false')
 text=once(text,'prefill_tokens != 1 && prefill_tokens != 2 && prefill_tokens != 4','prefill_tokens != 16')
 text=once(text,'llama_n_batch(context)!=4||','llama_n_batch(context)!=16||')
 text=once(text,'request_count=16','request_count=31')
 text=once(text,'counting_modes[]={2,2,6,14,14,6,2};\n        constexpr unsigned quality_modes[]={2,6,14}',
  'counting_modes[]={'+','.join(map(str,COUNTING))+'};\n        constexpr unsigned quality_modes[]={0,1,2,3,4,5}')
 text=once(text,'ordinal<7;const unsigned mode=counting?counting_modes[ordinal]:quality_modes[(ordinal-7)%3]',
  'ordinal<13;const unsigned mode=counting?counting_modes[ordinal]:quality_modes[(ordinal-13)%6]')
 text=once(text,'const unsigned task=counting?0:(ordinal-7)/3','const unsigned task=counting?0:(ordinal-13)/6')
 text=once(text,'            qwen_app_route_begin(mode);','''            qwen_app_route_begin(6);
            qwen_app_lean_prefill_configure(mode);''')
 text=once(text,'engine=std::make_unique<qwen_app::LlamaEngine>(model,context,4);',
  'engine=std::make_unique<qwen_app::LlamaEngine>(model,context,qwen_app::lean_prefill_policy(mode).width);')
 text=once(text,'            if(qwen_app::routing_policy(mode).sharing)engine->enable_speculative_step_prototype(admit_checkpoint);','')
 text=once(text,'qwen_app::RepeatedExpertQ2SpeculativeEngine adapter(*engine,model,context,qwen_app::routing_policy(mode).sharing);','''struct Adapter final:qwen_app::Engine {
                qwen_app::LlamaEngine&e;explicit Adapter(qwen_app::LlamaEngine&v):e(v){}
                std::uint32_t tokenize(const std::string&s)override{return e.tokenize(s);}
                void prefill(std::uint32_t n)override{e.prefill(n);}
                qwen_app::Token next()override{qwen_app_routing_event_begin();return e.next();}
                void finish()override{e.finish();}
                std::optional<qwen_app::ExpertCacheMetrics>expert_cache_metrics()const override{return e.expert_cache_metrics();}
            } adapter(*engine);''')
 text=once(text,'counting&&mode==2','counting&&mode==0')
 marker='            completed.push_back(row);write_fresh_report(prefix+".result",row);'
 text=once(text,marker,'''            const auto prefill=qwen_app_lean_prefill_stats();const auto selected=qwen_app::lean_prefill_policy(mode);
            if(prefill.input_tokens!=result.metrics.prompt_tokens||prefill.calls!=(prefill.input_tokens+selected.width-1)/selected.width||
               prefill.output_rows!=(selected.last_output_only?prefill.calls:prefill.input_tokens)||!prefill.maximum_width)
                throw std::runtime_error("Actual prefill calls and output rows must reconcile");
            row["prefill_policy"]={{"width",selected.width},{"last_output_only",selected.last_output_only},
                {"calls",prefill.calls},{"input_tokens",prefill.input_tokens},{"output_rows",prefill.output_rows},{"maximum_width",prefill.maximum_width}};
'''+marker)
 return text

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('parent','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();prior=json.loads(a.parent.read_text());old=prior['routing_sharing']
 require(old['scope']['maximum_requests']==16,'Exact qualified composition parent required')
 frozen=active_link_inputs(prior)+[r for r in prior['inputs_before']if Path(r['path']).suffix=='.so']+[record(a.parent),record(Path(__file__)),record(ROOT/'native/app/lean_prefill_policy.h')]
 for r in frozen:require(record(r['path'])==r,'Qualified input changed')
 a.out.mkdir(parents=True,exist_ok=False);(a.out/'tmp').mkdir()
 model_scope=dict(old['model_scope'],schema='ps5-qwen-lean-prefill-model-v1',maximum_requests=31,warmup_requests=1,timed_requests=12,prefill_tokens=16)
 IO_scope=dict(old['IO_scope'],schema='ps5-qwen-lean-prefill-IO-v1',maximum_requests=31)
 sources=old['actual_sources'];commands={k:v for k,v in zip(('entry','cache','engine','capture','routing','graph'),old['commands'])}
 header=Path(sources['capture']['path']).with_name('completed_expert_routes.h').read_text()
 header=once(header,'std::array<std::uint16_t,40> ids{}','std::array<std::uint16_t,160> ids{}')
 (a.out/'completed_expert_routes.h').write_text(header,newline='\n')
 capture=once(Path(sources['capture']['path']).read_text(),'tokens>4','tokens>16')
 variants={'entry':entry_source(Path(sources['entry']['path']).read_text(),old,model_scope,IO_scope),
  'cache':cache_source(Path(sources['cache']['path']).read_text()),
  'engine':engine_source(Path(sources['engine']['path']).read_text()),'capture':capture}
 replacements={};jobs=[];actual=dict(sources);added=[]
 for label,text in variants.items():
  source=a.out/(label+'.private.cpp');source.write_text(text,newline='\n');obj=a.out/(label+'.o');cmd=commands[label].copy()
  original_object=cmd[cmd.index('-o')+1];cmd[cmd.index('-c')+1]=str(source);cmd[cmd.index('-o')+1]=str(obj)
  # Preserve the qualified ordering of scoped allocator and memory headers.
  # Only this experiment's route-observer header shadows the original view.
  cmd[1:1]=['-I',str(a.out)]
  if '-MF'in cmd:cmd[cmd.index('-MF')+1]=str(a.out/(label+'.private.d'))
  require(prior['link_command'].count(original_object)==1,'One selected provider must be replaced')
  replacements[original_object]=str(obj);jobs.append(cmd);actual[label]=record(source);added +=[record(source),record(obj)] if obj.exists() else [record(source)]
 image=a.out/'qwen-native.pie.elf';link=[replacements.get(x,x)for x in prior['link_command']];link[link.index('-o')+1]=str(image)
 link=[('-Map='+str(a.out/'native-link.private.map'))if x.startswith('-Map=')else x for x in link]
 for i,cmd in enumerate(jobs+[link]):
  run=subprocess.run(cmd,capture_output=True,timeout=600,env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp')))
  (a.out/f'{i}.private.log').write_bytes(run.stdout+run.stderr);require(run.returncode==0,run.stderr.decode(errors='replace')[-5500:]);print(json.dumps(dict(lean_prefill_build_step=i+1,total=len(jobs)+1)),flush=True)
 for r in frozen:require(record(r['path'])==r,'Frozen input changed during build')
 receipt=copy.deepcopy(prior);receipt.update(artifact=record(image),compile_commands=[jobs[0]],link_command=link,source_parent=record(a.parent),
  inputs_before=frozen+added+[record(a.out/(x+'.o'))for x in variants]+[record(a.out/'completed_expert_routes.h')],
  lossless_driver_table_geometry=audit_linked_storage(image,prior['lossless_driver_tables']))
 receipt['expert_q2_model'].update(scope=model_scope,actual_entry=actual['entry'],actual_cache=actual['cache'],commands=jobs[:2])
 receipt['all_Q2_IO_measurement'].update(scope=IO_scope,entry=actual['entry'])
 receipt['all_Q2_bundle_comparison']=dict(scope=SCOPE)
 receipt['routing_sharing']=dict(old,scope=SCOPE,model_scope=model_scope,IO_scope=IO_scope,actual_sources=actual,
  commands=[*jobs,commands['routing'],commands['graph']],production_adopted=False)
 receipt['lean_prefill']=dict(scope=SCOPE,actual_sources={k:actual[k]for k in variants},shared_GPU_matrix_graph_driver_unchanged=True,
  CPU_miss_bookkeeping_capacity=dict(previous=40,selected=160,maximum_tokens=16,Experts_per_prefill_token=10,
   additional_stack_bytes=1080,physical_IO_and_GPU_allocations_unchanged=True),PS5_operations=0)
 target=a.out/'receipt.private.json';write_json(target,receipt)
 receipt['real_module_import_audit']=audit(a.workspace,a.cache,a.out)
 receipt['native_dispatch_audit']=dispatch(a.workspace,a.workspace/'driver-work/PS5-Vulkan-Inference-qwen-872cc126',image,a.out/'dispatch')
 require(not receipt['real_module_import_audit']['missing']and receipt['native_dispatch_audit']['passed'],'Import/dispatch audit failed');write_json(target,receipt)
 print(json.dumps(dict(lean_prefill_built=True,requests=len(ORDER),PS5_operations=0)),flush=True)
if __name__=='__main__':main()
