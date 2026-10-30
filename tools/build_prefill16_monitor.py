#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Integrate measured width16/all into the qualified normal prefix/causal app."""
import argparse,copy,json,os,subprocess
from pathlib import Path
from expert_q4 import require,record,write_json
from active_native_inputs import active_link_inputs
from build_speculative_batch_probe import once
from driver_table_storage import audit_linked_storage
from audit_native_imports import audit
from native_dispatch import audit as dispatch
ROOT=Path(__file__).resolve().parents[1]
def literal(v):return json.dumps(json.dumps(v,separators=(',',':')))
def causal_header_source(text):
 text='#include "prefill16_policy.h"\n'+text
 return once(text,'e.prefill_batch_tokens()!=4','!qwen_app::supported_sharing_prefill_width(e.prefill_batch_tokens())')
def engine_source(text):
 text=once(text,'tokens != 1 && tokens != 2 && tokens != 4','tokens != 1 && tokens != 2 && tokens != 4 && tokens != 16')
 text=once(text,'Bounded prefill requires 1, 2 or 4 tokens','Bounded prefill requires 1, 2, 4 or 16 tokens')
 require(text.count('prefill_tokens_!=4||')==3,'All three original checkpoint owner guards required')
 return text.replace('prefill_tokens_!=4||','(prefill_tokens_!=4&&prefill_tokens_!=16)||')
def entry_source(text,prior,scope,model_scope):
 text=once(text,literal(prior['expert_q2_model']['scope']),literal(model_scope))
 text=once(text,literal(prior['all_Q2_optimized_monitor']['scope']),literal(scope))
 text=once(text,'llama_n_batch(context)!=4||','llama_n_batch(context)!=16||')
 text=once(text,'p.at("tokens").get<std::uint64_t>() > 4','p.at("tokens").get<std::uint64_t>() > 16')
 text=once(text,'prefill_tokens != 1 && prefill_tokens != 2 && prefill_tokens != 4','prefill_tokens != 1 && prefill_tokens != 2 && prefill_tokens != 4 && prefill_tokens != 16')
 return once(text,'engine=std::make_unique<qwen_app::LlamaEngine>(model,context,4);','engine=std::make_unique<qwen_app::LlamaEngine>(model,context,16);')
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('parent','comparison','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();prior=json.loads(a.parent.read_text());comp=json.loads(a.comparison.read_text())
 require(prior['routing_winners_normal']['selected_policy']==14 and comp['lean_prefill']['CPU_miss_bookkeeping_capacity']['selected']==160,'Qualified normal composition and measured CPU capacities required')
 evidence=json.loads((ROOT/'docs/lean-prefill-results-20261030.json').read_text())
 require(evidence['completed']and evidence['measured_modes']['4']['counting_contents_passed']==2 and evidence['measured_modes']['4']['fixed_quality_strict']==3,'Completed width16/all comparison required')
 scope=dict(prior['all_Q2_optimized_monitor']['scope'],schema='ps5-qwen-prefill16-monitor-v1',prefill_tokens=16,all_prompt_outputs_requested=True)
 model_scope=dict(prior['expert_q2_model']['scope'],schema='ps5-qwen-prefill16-monitor-model-v1',prefill_tokens=16)
 frozen=active_link_inputs(prior)+active_link_inputs(comp)+[r for r in prior['inputs_before']if Path(r['path']).suffix=='.so']+[record(a.parent),record(a.comparison),record(Path(__file__)),record(ROOT/'docs/lean-prefill-results-20261030.json'),record(ROOT/'native/app/prefill16_policy.h')]
 for r in frozen:require(record(r['path'])==r,'Frozen qualified provider changed')
 a.out.mkdir(parents=True,exist_ok=False);(a.out/'tmp').mkdir()
 header=Path(comp['lean_prefill']['actual_sources']['capture']['path']).with_name('completed_expert_routes.h')
 (a.out/header.name).write_bytes(header.read_bytes())
 causal=a.out/'causal_expert_sharing.h';causal.write_text(causal_header_source((ROOT/'native/app/causal_expert_sharing.h').read_text()),newline='\n')
 old=prior['routing_sharing']['actual_sources'];variants={'entry':entry_source(Path(old['entry']['path']).read_text(),prior,scope,model_scope),'engine':engine_source(Path(old['engine']['path']).read_text())}
 old_commands={'entry':prior['compile_commands'][0],'engine':prior['all_Q2_optimized_monitor']['commands'][2]}
 jobs={};replacements={};actual=dict(old);added=[record(a.out/header.name),record(causal)]
 for key,text in variants.items():
  source=a.out/(key+'.private.cpp');source.write_text(text,newline='\n');obj=a.out/(key+'.o');cmd=old_commands[key].copy();previous=cmd[cmd.index('-o')+1]
  cmd[cmd.index('-c')+1]=str(source);cmd[cmd.index('-o')+1]=str(obj);cmd[1:1]=['-I',str(a.out)]
  if '-MF'in cmd:cmd[cmd.index('-MF')+1]=str(a.out/(key+'.private.d'))
  jobs[key]=cmd;replacements[previous]=str(obj);actual[key]=record(source);added.append(record(source))
 for key,index in (('cache',1),('capture',3)):
  before=prior['routing_sharing']['commands'][index];after=comp['routing_sharing']['commands'][index]
  replacements[before[before.index('-o')+1]]=after[after.index('-o')+1];actual[key]=comp['routing_sharing']['actual_sources'][key]
 require(all(prior['link_command'].count(k)==1 for k in replacements),'Exactly one selected object per provider required')
 image=a.out/'qwen-native.pie.elf';link=[replacements.get(x,x)for x in prior['link_command']];link[link.index('-o')+1]=str(image)
 link=[('-Map='+str(a.out/'native-link.private.map'))if x.startswith('-Map=')else x for x in link]
 for i,cmd in enumerate([*jobs.values(),link]):
  run=subprocess.run(cmd,capture_output=True,timeout=600,env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp')))
  (a.out/f'{i}.private.log').write_bytes(run.stdout+run.stderr);require(run.returncode==0,run.stderr.decode(errors='replace')[-5000:]);print(json.dumps(dict(normal_prefill_build_step=i+1,total=3)),flush=True)
 for r in frozen:require(record(r['path'])==r,'Frozen source changed during relink')
 receipt=copy.deepcopy(prior);receipt.update(artifact=record(image),compile_commands=[jobs['entry']],link_command=link,source_parent=record(a.parent),inputs_before=list({r['path']:r for r in frozen+added+[record(a.out/(k+'.o'))for k in jobs]}.values()),lossless_driver_table_geometry=audit_linked_storage(image,prior['lossless_driver_tables']))
 receipt['expert_q2_model'].update(scope=model_scope,actual_entry=actual['entry'],actual_cache=actual['cache'],commands=[jobs['entry'],comp['routing_sharing']['commands'][1]])
 receipt['all_Q2_optimized_monitor'].update(scope=scope,actual_entry=actual['entry'],actual_engine=actual['engine'],commands=[jobs['entry'],prior['all_Q2_optimized_monitor']['commands'][1],jobs['engine']],production_adopted=False)
 receipt['routing_winners_normal'].update(scope=scope,model_scope=model_scope,actual_entry=actual['entry'],shared_providers=actual,normal_validation_pending=True)
 receipt['routing_sharing'].update(scope=scope,model_scope=model_scope,actual_sources=actual,commands=[jobs['entry'],comp['routing_sharing']['commands'][1],jobs['engine'],comp['routing_sharing']['commands'][3],*prior['routing_sharing']['commands'][4:]])
 receipt['prefill16_normal']=dict(scope=scope,model_scope=model_scope,actual_sources=actual,causal_header=record(causal),qualified_width16_comparison=record(ROOT/'docs/lean-prefill-results-20261030.json'),selected_mode=4,
  selection_rationale='Width16/all retains decode speed and matches tail-only whole throughput; original prefill-first mode5 selection remains historical, not rewritten.',original_GPU_math_driver_delivery_and_allocation_caps=True,normal_validation_pending=True)
 target=a.out/'receipt.private.json';write_json(target,receipt)
 receipt['real_module_import_audit']=audit(a.workspace,a.cache,a.out);receipt['native_dispatch_audit']=dispatch(a.workspace,a.workspace/'driver-work/PS5-Vulkan-Inference-qwen-872cc126',image,a.out/'dispatch')
 require(not receipt['real_module_import_audit']['missing']and receipt['native_dispatch_audit']['passed'],'Real imports and physical dispatch required');write_json(target,receipt)
 print('Normal width16/all prefix and causal app built; actual GPU/driver code retained.',flush=True)
if __name__=='__main__':main()
