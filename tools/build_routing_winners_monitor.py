#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Relink a selected routing composition into the existing passive/API app."""
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

def normal_source(text,old,scope,model_scope,bits):
 text='#include "expert_routing_policy.h"\n#include "causal_expert_sharing.h"\n'+text
 text=once(text,literal(old['expert_q2_model']['scope']),literal(model_scope))
 text=once(text,literal(old['all_Q2_optimized_monitor']['scope']),literal(scope))
 text=once(text,'        context = llama_init_from_model(model, qwen_app::streaming_context_params(',
  '        if(setenv("LLAMA_GRAPH_REUSE_DISABLE","1",1))throw std::runtime_error("Policy graph rebuild selection failed");\n        context = llama_init_from_model(model, qwen_app::streaming_context_params(')
 text=text.replace('10*row.tokens','row.experts*row.tokens')
 text=once(text,'{"layer",row.layer},{"tokens",row.tokens},{"ids",ids}','{"layer",row.layer},{"tokens",row.tokens},{"experts",row.experts},{"ids",ids}')
 text=once(text,'{"experts_per_token",10}','{"experts_per_token","per_record"}')
 text=once(text,'        Json completed=Json::array();','        Json completed=Json::array();\n        constexpr unsigned selected_policy='+str(bits)+';\n        std::uint64_t last_payload=0,saved_payload=0,observed_captures=0;')
 text=once(text,'            const auto rounded=qwen_app::final_prefix_handoff.new_allocation(context,bytes);',
 '''            const auto captures=engine->checkpoint_validation_stats().captures;
            if(captures!=observed_captures){
                if(captures!=observed_captures+1||!last_payload)throw std::runtime_error("Positive prior checkpoint capture required");
                saved_payload=last_payload;observed_captures=captures;
            }
            const auto rounded=qwen_app::checkpoint_replacement_growth(bytes,saved_payload);
            last_payload=bytes;''')
 text=once(text,'                resident_reset_empty_context(context,model,startup.admission_report);',
  '                resident_reset_empty_context(context,model,startup.admission_report);\n                qwen_app_route_begin(selected_policy);observed_captures=0;')
 start=text.index('            engine->set_logits_observer([&](const float *v,std::size_t count) noexcept {')
 end=text.index('            qwen_app::ExpertQ2SpeculativeEngine causal',start)
 text=text[:start]+'''            std::uint64_t routing_before[3]{};qwen_app_route_stats(routing_before);
            qwen_app::CheckpointValidationStats checkpoint_baseline{};
            engine->set_logits_observer([&](const float*v,std::size_t count)noexcept{
                if(!v||count!=columns||rows>=resident_reference_rows){geometry_error=true;return;}
                for(std::size_t i=0;i<count;++i){
                    if(!std::isfinite(v[i]))value_error=true;
                    if(!ordinal)reference_logits[rows*columns+i]=v[i];
                    else if(rows<reference_rows){const auto e=std::abs(double(v[i])-reference_logits[rows*columns+i]);
                        max_error=std::max(max_error,e);if(ordinal==1&&e>1e-5+1e-5*std::abs(reference_logits[rows*columns+i]))value_error=true;}
                    else if(ordinal==1)geometry_error=true;
                }
                ++rows;if(!ordinal)++reference_rows;
            });
'''+text[end:]
 text=once(text,'qwen_app::ExpertQ2SpeculativeEngine causal(*engine,model,context,second);',
  'qwen_app::CausalExpertSharingEngine causal(*engine,model,context,second&&qwen_app::routing_policy(selected_policy).sharing);')
 text=text.replace('qwen_app::ExpertQ2SpeculativeEngine&','qwen_app::CausalExpertSharingEngine&')
 text=once(text,'llama_context*c;bool final;std::function<void(std::uint64_t)>admit;',
  'llama_context*c;bool final;std::function<void(std::uint64_t)>admit;qwen_app::CheckpointValidationStats&base;')
 text=once(text,'bool f,std::function<void(std::uint64_t)>g):causal(a),e(v),c(x),final(f),admit(std::move(g)){}',
  'bool f,std::function<void(std::uint64_t)>g,qwen_app::CheckpointValidationStats&b):causal(a),e(v),c(x),final(f),admit(std::move(g)),base(b){}')
 text=once(text,'void prefill(std::uint32_t n)override{causal.prefill(n);if(final){',
  'void prefill(std::uint32_t n)override{causal.prefill(n);base=e.checkpoint_validation_stats();if(final){')
 text=once(text,'consumer(causal,*engine,context,second,admit_checkpoint);',
  'consumer(causal,*engine,context,second&&qwen_app::routing_policy(selected_policy).sharing,admit_checkpoint,checkpoint_baseline);')
 text=once(text,'(ordinal&&rows!=reference_rows)','(ordinal==1&&rows!=reference_rows)')
 text=once(text,'else if(result.token_ids!=reference_ids||result.output_bytes!=reference_bytes)',
  'else if(ordinal==1&&(result.token_ids!=reference_ids||result.output_bytes!=reference_bytes))')
 start=text.index('            if(ordinal){const auto&a=routes[0],&b=routes[ordinal];')
 end=text.index('            const auto p=engine->prefix_reuse_stats();',start)
 text=text[:start]+'''            if(ordinal==1){const auto&a=routes[0],&b=routes[ordinal];
                if(a.rows.size()!=b.rows.size())throw std::runtime_error("Same-policy independent route geometry differs");
                for(std::size_t i=0;i<b.rows.size();++i){
                    if(a.rows[i].layer!=b.rows[i].layer||a.rows[i].tokens!=b.rows[i].tokens||a.rows[i].experts!=b.rows[i].experts||
                       !std::equal(a.rows[i].ids.begin(),a.rows[i].ids.begin()+a.rows[i].experts*a.rows[i].tokens,b.rows[i].ids.begin()))
                        throw std::runtime_error("Same-policy independent ordered routes differ");}}
'''+text[end:]
 start=text.index('            if(second&&(!qwen_app::final_prefix_handoff.consumed()')
 end=text.index('            require_model_CPU_budget();require_unchanged_model();',start)
 text=text[:start]+'''            const auto checkpoints=engine->checkpoint_validation_stats();
            if(second&&qwen_app::routing_policy(selected_policy).sharing&&
               (!qwen_app::final_prefix_handoff.consumed()||speculative.attempts<2||
                speculative.attempts!=speculative.accepted+speculative.rejected||
                checkpoints.captures-checkpoint_baseline.captures!=speculative.attempts||
                checkpoints.restores-checkpoint_baseline.restores!=speculative.rejected))
                throw std::runtime_error("Final consumer requires reconciled repeated target decisions and complete state");
'''+text[end:]
 marker='            row["F32_comparison_scope"]='
 start=text.index(marker);end=text.index('            row["speculation"]=',start)
 text=text[:start]+'''            std::uint64_t routing_after[3]{};qwen_app_route_stats(routing_after);
            row["routing_policy"]={{"bits",selected_policy},{"decode_Experts",qwen_app::routing_policy(selected_policy).experts},
                {"cache_rank",qwen_app::routing_policy(selected_policy).cache_rank},{"repeated_sharing",second&&qwen_app::routing_policy(selected_policy).sharing},
                {"rank_calls",routing_after[0]-routing_before[0]},{"resident_scores",routing_after[1]-routing_before[1]},
                {"rank_CPU_ns",routing_after[2]-routing_before[2]},{"preferences_latched_per_target_event",true}};
            row["checkpoint"]={{"captures",checkpoints.captures-checkpoint_baseline.captures},
                {"restores",checkpoints.restores-checkpoint_baseline.restores},{"maximum_payload_bytes",checkpoints.maximum_payload_bytes}};
            row["same_tokens_as_independent"]=result.token_ids==reference_ids&&result.output_bytes==reference_bytes;
            row["full_F32_finite"]=true;
            row["F32_comparison_scope"]=second?"Approximate cached routing and mixed width: complete finite vocabulary; differences disclosed":"Same-policy independent full F32 and ordered routes";
'''+text[end:]
 text=once(text,'{"all_repeated_Q2_tokens_and_bytes_exact",true}',
  '{"all_repeated_Q2_tokens_and_bytes_exact",std::all_of(completed.begin(),completed.end(),[](const Json&r){return r.at("same_tokens_as_independent").get<bool>();})}')
 text=once(text,'{"optimized_delivery_and_final_prefix_handoff_completed",true}',
  '{"optimized_delivery_and_final_prefix_handoff_completed",true},{"final_prefix_handoff_consumed",qwen_app::final_prefix_handoff.consumed()},{"routing_winners_policy",selected_policy},{"graph_reuse_disabled_for_policy",true}')
 label='GATE UP Q2_K / DOWN Q2_0 MSE / OTHER BF16 F32 / TOP6'+(' CACHE'if bits&4 else '')
 text=text.replace('GATE UP Q2_K / DOWN Q2_0 MSE / OTHER BF16 F32',label)
 return text

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('parent','comparison','selection','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();prior=json.loads(a.parent.read_text());comp=json.loads(a.comparison.read_text());selection=json.loads(a.selection.read_text())
 require(selection['completed']and selection['all_quality_tasks_completed'],'A closed physical composition selection is required')
 bits=selection['selected_policy'];require(bits in (2,6,14),'Only the measured selected composition may be integrated')
 scope=dict(prior['all_Q2_optimized_monitor']['scope'],schema='ps5-qwen-routing-winners-monitor-v1',selected_routing_policy=bits,
  decode_Experts=6,cached_ranking=bool(bits&4),maximum_speculative_attempts=8 if bits&8 else 0,
  final_API='exact_prefix_restore_then_selected_causal_sharing',unlike_width_full_vocab_finite_and_top1_equal_required=False,
  graph_reuse_disabled_for_policy=True,preferences_latched_per_target_event=True)
 model_scope=dict(prior['expert_q2_model']['scope'],schema='ps5-qwen-routing-winners-monitor-model-v1',selected_Experts='10_prefill_6_decode',
  approximate_routing_owner_authorized=True,final_unlike_width_full_vocabulary_finite_top1_and_same_tokens_required=False)
 frozen=active_link_inputs(prior)+active_link_inputs(comp)+[r for r in prior['inputs_before']if Path(r['path']).suffix=='.so']+[record(x)for x in (a.parent,a.comparison,a.selection,Path(__file__),ROOT/'native/app/expert_routing_policy.h',ROOT/'native/app/causal_expert_sharing.h')]
 for r in frozen:require(record(r['path'])==r,'Selected normal integration input changed')
 a.out.mkdir(parents=True,exist_ok=False);(a.out/'tmp').mkdir()
 old=prior['all_Q2_optimized_monitor']['actual_entry'];entry=a.out/'entry.private.cpp';entry.write_text(normal_source(Path(old['path']).read_text(),prior,scope,model_scope,bits),newline='\n')
 cmd=prior['compile_commands'][0].copy();oldobj=cmd[cmd.index('-o')+1];cmd[cmd.index('-c')+1]=str(entry);cmd[cmd.index('-o')+1]=str(a.out/'entry.o')
 cmd[1:1]=['-I',str(Path(comp['artifact']['path']).parent),'-I',str(Path(old['path']).parent)];cmd+=['-I',str(ROOT/'native/app')]
 if '-MF'in cmd:cmd[cmd.index('-MF')+1]=str(a.out/'entry.private.d')
 replacements={oldobj:str(a.out/'entry.o')}
 for key,index in (('cache',1),('engine',2)):
  oldcmd=prior['expert_q2_model']['commands'][1]if key=='cache'else prior['all_Q2_optimized_monitor']['commands'][2]
  newcmd=comp['routing_sharing']['commands'][index]
  replacements[oldcmd[oldcmd.index('-o')+1]]=newcmd[newcmd.index('-o')+1]
 oldcapture=[x for x in prior['link_command']if x.endswith('.o')and'completed_expert_routes'in x];require(len(oldcapture)==1,'One original observer object required')
 folder=Path(comp['artifact']['path']).parent;replacements[oldcapture[0]]=str(folder/'capture.o')
 image=a.out/'qwen-native.pie.elf';link=[replacements.get(x,x)for x in prior['link_command']]
 require(all(prior['link_command'].count(k)==1 for k in replacements),'One actual replacement per composed provider required')
 link[1:1]=[str(folder/'routing.o'),str(folder/'graph.o')];link[link.index('-o')+1]=str(image);link=[('-Map='+str(a.out/'native-link.private.map'))if x.startswith('-Map=')else x for x in link]
 for i,command in enumerate((cmd,link)):
  run=subprocess.run(command,capture_output=True,timeout=600,env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp')));(a.out/f'{i}.private.log').write_bytes(run.stdout+run.stderr)
  require(run.returncode==0,run.stderr.decode(errors='replace')[-5000:]);print(json.dumps(dict(normal_routing_build_step=i+1,total=2)),flush=True)
 for r in frozen:require(record(r['path'])==r,'Frozen normal integration source changed')
 receipt=copy.deepcopy(prior);receipt.update(artifact=record(image),compile_commands=[cmd],link_command=link,source_parent=record(a.parent),inputs_before=list({r['path']:r for r in frozen+[record(entry),record(a.out/'entry.o')]}.values()),lossless_driver_table_geometry=audit_linked_storage(image,prior['lossless_driver_tables']))
 receipt['expert_q2_model'].update(scope=model_scope,actual_entry=record(entry),actual_cache=comp['routing_sharing']['actual_sources']['cache'],commands=[cmd,comp['routing_sharing']['commands'][1]])
 receipt['all_Q2_optimized_monitor'].update(scope=scope,actual_entry=record(entry),actual_engine=comp['routing_sharing']['actual_sources']['engine'],commands=[cmd,prior['all_Q2_optimized_monitor']['commands'][1],comp['routing_sharing']['commands'][2]],production_adopted=False)
 receipt['routing_winners_normal']=dict(scope=scope,model_scope=model_scope,selected_policy=bits,selection=record(a.selection),actual_entry=record(entry),qualified_composition=record(a.comparison),shared_providers=comp['routing_sharing']['actual_sources'],normal_validation_pending=True)
 receipt['routing_sharing']=dict(comp['routing_sharing'],scope=dict(scope,approximate_routing_changes_permitted=True),model_scope=model_scope,actual_sources=dict(comp['routing_sharing']['actual_sources'],entry=record(entry)))
 target=a.out/'receipt.private.json';write_json(target,receipt);receipt['real_module_import_audit']=audit(a.workspace,a.cache,a.out);receipt['native_dispatch_audit']=dispatch(a.workspace,a.workspace/'driver-work/PS5-Vulkan-Inference-qwen-872cc126',image,a.out/'dispatch')
 require(not receipt['real_module_import_audit']['missing']and receipt['native_dispatch_audit']['passed'],'Normal import/dispatch audit failed');write_json(target,receipt)
 print('Selected routing providers integrated with the existing passive/API and exact-prefix app.',flush=True)
if __name__=='__main__':main()
