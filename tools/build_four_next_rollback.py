#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compare complete state copies and native one-token rollback at fixed n_rs=1."""
import argparse,json,re
from pathlib import Path
from build_cache_capacity_1125 import recipes,literal
from build_speculative_batch_probe import once
from expert_q4 import require,record,write_json
from scoped_native_variant import link,seal
from rebind_cache_provenance import rebind_cache
ROOT=Path(__file__).resolve().parents[1]
EXTRA=124<<20
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('parent','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();n=json.loads(a.parent.read_text());a.out.mkdir(parents=True,exist_ok=False)
 ec=n['compile_commands'][0];oc=n['all_Q2_optimized_monitor']['commands'][1];eg=n['routing_sharing']['commands'][2]
 selected={c[c.index('-o')+1]:c for c in recipes(n)if'-c'in c and'-o'in c and c[c.index('-o')+1]in n['link_command']}
 for c in (ec,oc,eg):selected[c[c.index('-o')+1]]=c
 directories={Path(c[c.index('-c')+1]).parent for c in selected.values()}
 for c in selected.values():directories.update(Path(c[i+1])for i,x in enumerate(c[:-1])if x=='-I')
 donors=[Path(row['path'])for row in n['GDN_decode_cache_comparison']['headers']if Path(row['path']).name=='device_buffer_budget.h'];require(len(donors)==1,'One exact installed budget donor required');donor=donors[0];text=donor.read_text();line=next(x for x in text.splitlines()if 'constexpr' in x and 'model_postload_device_budget ='in x)
 text=once(text,line,'inline constexpr std::uint64_t model_postload_device_budget = '+str(5086097408+EXTRA)+'ull;');header=a.out/'device_buffer_budget.h';header.write_text(text,newline='\n')
 targets={ROOT/'native/app/device_buffer_budget.h',ROOT.with_name(ROOT.name+'-refill')/'native/app/device_buffer_budget.h',donor,*[d/'device_buffer_budget.h'for d in directories if(d/'device_buffer_budget.h').is_file()]}
 overlay=a.out/'rollback-budget.private.json';write_json(overlay,dict(version=0,**{'case-sensitive':'false','use-external-names':False},roots=[dict(type='file',name=x.resolve().as_posix(),**{'external-contents':header.resolve().as_posix()})for x in sorted(targets)]))
 old=n['GDN_model_comparison']['scope'];scope=dict(old,schema='ps5-qwen-native-rollback-model-v1',candidate='one_token_recurrent_rollback',n_rs_seq=1,extra_bounded_state_allowance_bytes=EXTRA,postload_budget_bytes=5086097408+EXTRA,
  physical_Direct_Flexible_and_OS_reserves_unchanged=True,quality_checkpoint_pairs=0,quality_forces_EOS_rejections=True,
  complete_control_checkpoint_API_unchanged=True,compact_arm_saves_no_complete_state=True,unlike_rejection_arithmetic_bit_equality_required=False,original_single_token_fusion_in_both_arms=True)
 entry=Path(ec[ec.index('-c')+1]).read_text();entry='#include "causal_rollback_engine.h"\nextern "C" void qwen_app_compact_rollback_select(bool);\nextern "C" void qwen_app_compact_rollback_stats(std::uint64_t*);\n'+entry
 entry=once(entry,'qwen_app::model_postload_device_budget==5086097408ull','qwen_app::model_postload_device_budget=='+str(5086097408+EXTRA)+'ull');entry=once(entry,literal(old),literal(scope));entry=once(entry,'qwen_app_conv_norm_trial_select(arm==1);','qwen_app_conv_norm_trial_select(true);qwen_app_compact_rollback_select(arm==1);')
 entry=once(entry,'if(reuse)engine->enable_prefix_reuse(admit_checkpoint);','engine->enable_speculative_step_prototype(admit_checkpoint);')
 entry=entry.replace('qwen_app::CausalExpertSharingEngine','qwen_app::CausalRollbackEngine')
 entry=once(entry,'causal(*engine,model,context,second&&qwen_app::routing_policy(selected_policy).sharing)', 'causal(*engine,model,context,ordinal>=10)')
 entry=once(entry,'if(ordinal>=10&&m.generated_tokens<=7)','if(false)');entry=once(entry,'checkpoint_samples.size()!=(ordinal>=10?std::min<std::size_t>(7,result.metrics.generated_tokens):0u)','!checkpoint_samples.empty()');entry=entry.replace('{"metrics_include_state_operations",ordinal>=10}','{"metrics_include_state_operations",false}')
 entry=once(entry,'            row["phase"]=phase;','            std::uint64_t rollback_counts[2]{};qwen_app_compact_rollback_stats(rollback_counts);row["compact_rollback"]={{"enabled",arm==1},{"complete_captures_elided",rollback_counts[0]},{"all_memory_rollbacks",rollback_counts[1]},{"n_rs_seq",llama_n_rs_seq(context)}};\n            row["phase"]=phase;')
 engine=Path(eg[eg.index('-c')+1]).read_text();engine='#include <atomic>\nnamespace {std::atomic<bool>compact_rollback{false};std::uint64_t compact_captures=0,compact_rejections=0;}\nextern "C" void qwen_app_compact_rollback_select(bool v){compact_rollback.store(v);}\nextern "C" void qwen_app_compact_rollback_stats(std::uint64_t*p){p[0]=compact_captures;p[1]=compact_rejections;}\n'+engine
 engine=once(engine,'    params.n_seq_max = 1;','    params.n_seq_max = 1;params.n_rs_seq=1;')
 engine=once(engine,'auto cost_start=ProfileClock::now();capture_checkpoint_in_active_epoch();\n            const auto capture_seconds=double(profile_elapsed_ns(cost_start))/1e9;',
  'const bool compact=compact_rollback.load();if(llama_n_rs_seq(context_)!=1||llama_memory_seq_pos_max(llama_get_memory(context_),0)!=position_-1)throw std::runtime_error("Exact recurrent rollback state and position required");\n            auto cost_start=ProfileClock::now();if(compact)++compact_captures;else capture_checkpoint_in_active_epoch();\n            const auto capture_seconds=compact?0.0:double(profile_elapsed_ns(cost_start))/1e9;')
 engine=once(engine,'cost_start=ProfileClock::now();restore_checkpoint_in_active_epoch();++speculative_stats_.rejected;',
 '''cost_start=ProfileClock::now();if(compact){
                    restored_logits_.assign(first,first+count);
                    const auto memory=llama_get_memory(context_);
                    if(!llama_memory_seq_rm(memory,0,position_+1,-1)||llama_memory_seq_pos_max(memory,0)!=position_)
                        throw std::runtime_error("Complete hybrid/PLE/recurrent rollback failed; retain owner");
                    ++position_;pending_=LLAMA_TOKEN_NULL;restored_logits_active_=true;++compact_rejections;
                    stage("compact_rollback_all_memory_modules_rewound_to_causal_pending_token");
                }else restore_checkpoint_in_active_epoch();++speculative_stats_.rejected;''')
 variants={};labels={ec[ec.index('-o')+1]:'entry',oc[oc.index('-o')+1]:'owner',eg[eg.index('-o')+1]:'engine'}
 for i,(obj,c)in enumerate(selected.items()):
  label=labels.get(obj,'budget'+str(i));source=Path(c[c.index('-c')+1]);include_budget='device_buffer_budget.h'in source.read_text()
  if '-MF'in c and Path(c[c.index('-MF')+1]).is_file():include_budget|='device_buffer_budget.h'in Path(c[c.index('-MF')+1]).read_text()
  if obj not in labels and not include_budget:continue
  command=c.copy()+['-ivfsoverlay',str(overlay),'-I',str(ROOT/'native/app')];variants[label]=(command,entry if label=='entry'else engine if label=='engine'else source.read_text())
 r,jobs,sources=link(a.parent,a.out,variants,[Path(__file__),header,overlay,donor,ROOT/'native/app/causal_rollback_engine.h'])
 for key in ('normal_performance','output_Q8_normal','cold_request','resident_all_Q8','resident_cache3072','resident_small_rows','resident_weight_normal','memory_quality_cohort'):
  r[key]['actual_sources'].update({k:sources[k]for k in labels.values()});r[key]['commands'].update({k:jobs[k]for k in labels.values()})
 r['all_Q2_optimized_monitor']['actual_entry']=sources['entry'];r['all_Q2_optimized_monitor']['actual_owner']=sources['owner'];r['all_Q2_optimized_monitor']['actual_engine']=sources['engine'];r['all_Q2_optimized_monitor']['commands'][:3]=[jobs[k]for k in ('entry','owner','engine')]
 r['routing_sharing']['actual_sources']['engine']=sources['engine'];r['routing_sharing']['commands'][2]=jobs['engine'];r['routing_winners_normal']['actual_entry']=sources['entry'];r['GDN_model_comparison']['scope']=scope;r['GDN_model_comparison']['actual_sources']['entry']=sources['entry'];r['GDN_model_comparison']['commands']['entry']=jobs['entry'];r['four_next_rollback']=dict(scope=scope,headers=[record(header),record(overlay)],actual_sources=sources,commands=jobs,model_comparison_pending=True)
 rebind_cache(r,a.out/'cache-provenance',r['routing_sharing']['commands'][1],r['routing_sharing']['actual_sources']['cache']);seal(r,a.workspace,a.cache,a.out)
 write_json(a.out/'core-safety.private.json',dict(completed=True,kind='bounded_native_recurrent_rollback',candidate=record(a.out/'receipt.private.json'),extra_application_state_bytes=EXTRA,physical_reserves_OS_minimum_positive_completion_unchanged=True,PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()
