#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build isolated routing, active-Expert-count and repeated causal comparisons."""
import argparse,copy,json,os,shlex,subprocess
from pathlib import Path
from active_native_inputs import active_link_inputs
from expert_q4 import require,record,write_json
from build_speculative_batch_probe import once
from driver_table_storage import audit_linked_storage
from audit_native_imports import audit
from native_dispatch import audit as dispatch
ROOT=Path(__file__).resolve().parents[1]
MODES=[0,0,2,2,0,3,3,0,4,4,0]+list(range(5))*3
SCOPE=dict(schema='ps5-qwen-routing-sharing-continuation-v1',enabled=True,maximum_requests=26,
 order=MODES,counting_requests=11,quality_requests=15,quality_tasks=3,model_loads=1,
 active_cache_slots=867,cache_budget_bytes=1333739520,selected_IO_flags=5,
 cache_rank_multiplier=1.5,decode_Expert_counts=[10,10,8,6,10],prefill_Top10_preserved=True,
 maximum_causal_attempts=8,verification_width=2,causal_drafts_only=True,
 graph_reuse_disabled_uniformly=True,approximate_routing_changes_permitted=True,
 quality_changes_recorded_without_aborting=True,complete_state_rejection_required=True,
 HTTP_requests=0,VideoOut_starts=0,automatic_retries=0)

def graph_source(text):
 text='#include "expert_routing_experiment.h"\n'+text
 text=once(text,'    const uint32_t n_expert_used_il = hparams.n_expert_used(il);',
  '    const uint32_t n_expert_used_il = qwen_app::bounded_expert_aggregate(hparams.n_expert_used(il),unsigned(n_expert_used));')
 marker='    const bool weight_before_ffn = arch == LLM_ARCH_LLAMA4;'
 text=once(text,marker,'''    if(n_expert==512&&n_expert_used==10&&n_tokens==1&&qwen_app_route_is_decode())
        n_expert_used=qwen_app::experimental_expert_count(qwen_app_route_mode(),1);
'''+marker)
 marker='    // select experts\n    ggml_tensor * selected_experts = selected_experts_in;'
 return once(text,marker,'''    if(n_expert==512&&n_tokens==1&&qwen_app_route_is_decode()&&qwen_app_route_mode()==1){
        selection_probs=ggml_map_custom1(ctx0,selection_probs,qwen_app_route_rank,1,reinterpret_cast<void*>(std::uintptr_t(il)));
        cb(selection_probs,"qwen_cache_rank",il);
    }
'''+marker)

def cache_source(text):
 text='#include "expert_routing_experiment.h"\n'+text
 text=once(text,'                slot_map[key_of[s] / n_expert][key_of[s] % n_expert] = -1;',
  '                qwen_app_route_resident(unsigned(key_of[s]/n_expert),unsigned(key_of[s]%n_expert),false);\n                slot_map[key_of[s] / n_expert][key_of[s] % n_expert] = -1;')
 return once(text,'            key_of[s] = il*n_expert + e;','            qwen_app_route_resident(unsigned(il),unsigned(e),true);\n            key_of[s] = il*n_expert + e;')

def observer_sources(header,text):
 header=once(header,'std::uint8_t layer=0, tokens=0;','std::uint8_t layer=0, tokens=0, experts=10;')
 text=once(text,'unsigned layer=0,tokens=0;','unsigned layer=0,tokens=0,experts=10;')
 text=once(text,'const auto tokens=tensor->ne[0]/10;','const auto used=unflattened?unflattened->ne[0]:0;\n                const auto tokens=used?tensor->ne[0]/used:0;')
 text=once(text,'tensor->ne[0]%10||tokens<1','(used!=6&&used!=8&&used!=10)||tensor->ne[0]%used||tokens<1')
 text=once(text,'!unflattened||unflattened->ne[0]!=10||','!unflattened||unflattened->ne[0]!=used||')
 text=once(text,'observer->layer=unsigned(layer);observer->tokens=unsigned(tokens);',
  'observer->layer=unsigned(layer);observer->tokens=unsigned(tokens);observer->experts=unsigned(used);')
 text=once(text,'for(unsigned i=0;i<10*observer->tokens;++i){','row.experts=std::uint8_t(observer->experts);\n    for(unsigned i=0;i<observer->experts*observer->tokens;++i){')
 return header,text

def entry_source(text,model_scope,IO_scope):
 text='#include "expert_routing_experiment.h"\n#include "repeated_expert_speculation.private.h"\n#include "resident_checkpoint_capacity.h"\n'+text
 text='extern "C" void qwen_app_select_Q2_normal_IO(unsigned);\n'+text
 text='inline constexpr const char*routing_comparison_scope='+json.dumps(json.dumps(SCOPE,separators=(',',':')))+';\n'+text
 text=once(text,'        context = llama_init_from_model(model, qwen_app::streaming_context_params(',
  '        if(setenv("LLAMA_GRAPH_REUSE_DISABLE","1",1))throw std::runtime_error("Uniform graph-rebuild comparison selection failed");\n        context = llama_init_from_model(model, qwen_app::streaming_context_params(')
 start=text.index('// SPDX-License-Identifier: MIT\n// Dedicated finite comparisons after the original model/context admission.')
 end=text.index('        qwen_native_stage("resident_additional_completed_waiting_for_ordinary_close");',start)
 end+=len('        qwen_native_stage("resident_additional_completed_waiting_for_ordinary_close");')
 text=text[:start]+(ROOT/'native/app/expert_routing_sharing_cohort.inc').read_text()+text[end:]
 text=text.replace('10*row.tokens','row.experts*row.tokens')
 text=once(text,'{"layer",row.layer},{"tokens",row.tokens},{"ids",ids}',
  '{"layer",row.layer},{"tokens",row.tokens},{"experts",row.experts},{"ids",ids}')
 text=once(text,'{"experts_per_token",10}','{"experts_per_token","per_record"}')
 # The actual top-k route observer has variable cardinality; the source transfer
 # reconciliation retains unique demand == hits+misses and full role payloads.
 text=text.replace('{"routing_and_cache_policy_unchanged",true}','{"routing_and_cache_policy_unchanged",false}')
 return text

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--finish-existing-link',action='store_true',help='Qualify an already completed host link only if every generated source remains byte-identical')
 for k in ('parent','headless','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();prior=json.loads(a.parent.read_text());old=json.loads(a.headless.read_text())
 require(prior['all_Q2_IO_normal']['flags']==5,'Exact selected normal I/O parent required')
 model_scope=dict(old['expert_q2_model']['scope'],schema='ps5-qwen-routing-sharing-model-v1',maximum_requests=26,timed_requests=10,selected_Experts='10_prefill_6_8_10_decode',full_same_Q2_F32_rows_and_routes_required=False,approximate_routing_owner_authorized=True)
 IO_scope=dict(old['all_Q2_IO_measurement']['scope'],schema='ps5-qwen-routing-sharing-IO-v1',maximum_requests=26)
 frozen=active_link_inputs(prior)+[r for r in prior['inputs_before']if Path(r['path']).suffix=='.so']+[record(a.parent),record(a.headless)]
 added_files=[ROOT/'tools/build_expert_routing_sharing.py',ROOT/'native/app/expert_routing_experiment.h',ROOT/'native/app/expert_routing_experiment.cpp',ROOT/'native/app/expert_routing_sharing_cohort.inc',ROOT/'native/app/expert_q2_speculative.h',ROOT/'native/app/resident_checkpoint_capacity.h',ROOT/'native/app/completed_expert_routes.h',ROOT/'native/app/completed_expert_routes.cpp']
 frozen +=[record(x)for x in added_files]
 for r in frozen:require(record(r['path'])==r,'Current selected source changed')
 if a.finish_existing_link:
  require((a.out/'qwen-native.pie.elf').is_file()and(a.out/'native-link.private.map').is_file()and not(a.out/'receipt.private.json').exists(),'Only a completed unsealed host link may be finished')
 else:a.out.mkdir(parents=True,exist_ok=False);(a.out/'tmp').mkdir()
 def write_source(path,text):
  raw=text.encode()
  if a.finish_existing_link:require(path.read_bytes()==raw,'Existing compiled source differs: '+str(path))
  else:path.write_bytes(raw)
 h,capture=observer_sources((ROOT/'native/app/completed_expert_routes.h').read_text(),(ROOT/'native/app/completed_expert_routes.cpp').read_text())
 write_source(a.out/'completed_expert_routes.h',h)
 adapter=(ROOT/'native/app/expert_q2_speculative.h').read_text().replace('ExpertQ2SpeculativeEngine','RepeatedExpertQ2SpeculativeEngine').replace('attempts_<1','attempts_<8').replace('DraftEvidence::consistent_pair','DraftEvidence::single_latest').replace('width=cost_.choose(pending,draft);','width=2;')
 write_source(a.out/'repeated_expert_speculation.private.h',adapter)
 oldentry=old['expert_q2_model']['actual_entry'];entry=entry_source(Path(oldentry['path']).read_text(),model_scope,IO_scope)
 from build_expert_q2_io_reduction import MODEL_SCOPE as OLD_MODEL
 entry=once(entry,json.dumps(json.dumps(OLD_MODEL,separators=(',',':'))),json.dumps(json.dumps(model_scope,separators=(',',':'))))
 engine_record=prior['all_Q2_optimized_monitor']['actual_engine']
 engine='#include "expert_routing_experiment.h"\n'+Path(engine_record['path']).read_text()
 engine=once(engine,'    stage("inference_before_decode_call");','    qwen_app_route_phase(!inside_prefill_);\n    stage("inference_before_decode_call");')
 compile_db=json.loads((a.cache/'build/llama-ps5/compile_commands.json').read_text())
 graph=next(x for x in compile_db if x['file'].endswith('/llama-graph.cpp'))
 graph_cmd=[s.strip('"')for s in shlex.split(graph['command'],posix=False)]
 capture_cmd=prior['compile_commands'][0]
 engine_cmd=prior['all_Q2_optimized_monitor']['commands'][2]
 variants=[('entry',prior['compile_commands'][0],prior['all_Q2_optimized_monitor']['actual_entry'],entry),
  ('cache',prior['expert_q2_model']['commands'][1],prior['expert_q2_model']['actual_cache'],cache_source(Path(prior['expert_q2_model']['actual_cache']['path']).read_text())),
  ('engine',engine_cmd,engine_record,engine),
  ('capture',capture_cmd,record(ROOT/'native/app/completed_expert_routes.cpp'),capture),
  ('routing',capture_cmd,record(ROOT/'native/app/expert_routing_experiment.cpp'),(ROOT/'native/app/expert_routing_experiment.cpp').read_text()),
  ('graph',graph_cmd,record(graph['file']),graph_source(Path(graph['file']).read_text()))]
 replacements={};jobs=[];added=[];actual={}
 for label,base,original,text in variants:
  source=a.out/(label+'.private.cpp');write_source(source,text);obj=a.out/(label+'.o');cmd=base.copy()
  old_object=cmd[cmd.index('-o')+1];cmd[cmd.index('-c')+1]=str(source);cmd[cmd.index('-o')+1]=str(obj)
  cmd[1:1]=['-I',str(a.out),'-I',str(Path(original['path']).parent),'-I',str(Path(oldentry['path']).parent)]
  cmd +=['-I',str(ROOT/'native/app')]
  if '-MF'in cmd:cmd[cmd.index('-MF')+1]=str(a.out/(label+'.private.d'))
  if label in ('entry','cache','engine'):
   require(prior['link_command'].count(old_object)==1,'Exactly one selected object must be replaced: '+label);replacements[old_object]=str(obj)
  if label=='capture':
   matches=[x for x in prior['link_command']if x.endswith('.o')and'completed_expert_routes'in x]
   require(len(matches)==1,'One original route observer must be replaced');replacements[matches[0]]=str(obj)
  jobs.append(cmd);actual[label]=record(source);added +=[record(source),original]
 image=a.out/'qwen-native.pie.elf';link=[replacements.get(x,x)for x in prior['link_command']]
 link[1:1]=[str(a.out/'routing.o'),str(a.out/'graph.o')];link[link.index('-o')+1]=str(image)
 link=[('-Map='+str(a.out/'native-link.private.map'))if x.startswith('-Map=')else x for x in link]
 for i,cmd in enumerate([]if a.finish_existing_link else jobs+[link]):
  run=subprocess.run(cmd,capture_output=True,timeout=600,env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp')))
  (a.out/f'{i}.private.log').write_bytes(run.stdout+run.stderr);require(run.returncode==0,run.stderr.decode(errors='replace')[-5000:]);print(json.dumps(dict(routing_build_step=i+1,total=7)),flush=True)
 for r in frozen:require(record(r['path'])==r,'Frozen input changed during build')
 receipt=copy.deepcopy(prior);receipt.update(artifact=record(image),compile_commands=[jobs[0]],link_command=link,source_parent=record(a.parent),inputs_before=frozen+added+[record(a.out/(x+'.o'))for x in actual]+[record(a.out/'completed_expert_routes.h'),record(a.out/'repeated_expert_speculation.private.h')],lossless_driver_table_geometry=audit_linked_storage(image,prior['lossless_driver_tables']))
 receipt['expert_q2_model'].update(scope=model_scope,actual_entry=actual['entry'],actual_cache=actual['cache'],commands=jobs[:2])
 receipt['all_Q2_IO_measurement']=dict(scope=IO_scope,entry=actual['entry'],owner=prior['all_Q2_optimized_monitor']['actual_owner'])
 receipt['all_Q2_bundle_comparison']=dict(scope=SCOPE)
 receipt['routing_sharing']=dict(scope=SCOPE,model_scope=model_scope,IO_scope=IO_scope,actual_sources=actual,commands=jobs,original_source_and_GPU_completion_guards_retained=True,production_adopted=False)
 target=a.out/'receipt.private.json';write_json(target,receipt)
 receipt['real_module_import_audit']=audit(a.workspace,a.cache,a.out);receipt['native_dispatch_audit']=dispatch(a.workspace,a.workspace/'driver-work/PS5-Vulkan-Inference-qwen-872cc126',image,a.out/'dispatch')
 require(not receipt['real_module_import_audit']['missing']and receipt['native_dispatch_audit']['passed'],'Import/dispatch audit failed');write_json(target,receipt)
 print('All three bounded experiments linked; no console execution or CI.',flush=True)
if __name__=='__main__':main()
