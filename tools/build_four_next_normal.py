#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Integrate only the measured768-key placement and native rollback winners."""
import argparse,copy,json,subprocess
from pathlib import Path
from active_native_inputs import active_link_inputs
from build_cache_capacity_1125 import literal
from build_speculative_batch_probe import once
from expert_q4 import require,record,write_json
from scoped_native_variant import link,seal
from rebind_cache_provenance import rebind_cache
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('normal','placement','rollback','comparison','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();normal=json.loads(a.normal.read_text());placement=json.loads(a.placement.read_text());rollback=json.loads(a.rollback.read_text());proof=json.loads(a.comparison.read_text())
 require(proof['candidate_comparisons_completed']and proof['placement']['eligible']and proof['rollback']['eligible']and not proof['two_token']['eligible']and not proof['gate_up']['kernel_eligible'],'Exactly the two closed measured winners required')
 require(not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT).strip(),'Commit exact source before final normal relink')
 revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();a.out.mkdir(parents=True,exist_ok=False)
 require(normal['lossless_shader_storage']['vulkan_object']==placement['lossless_shader_storage']['vulkan_object']==rollback['lossless_shader_storage']['vulkan_object'],'The exact qualified single-token GPU object must remain selected')
 require(normal['routing_sharing']['actual_sources']['cache']==placement['routing_sharing']['actual_sources']['cache']==rollback['routing_sharing']['actual_sources']['cache'],'Original installed cache planner required')
 for r in (normal,placement,rollback):
  for row in active_link_inputs(r):require(record(row['path'])==row,'Qualified compiled provider changed')
 seed=copy.deepcopy(normal);original_rollback=json.loads(Path(rollback['source_parent']['path']).read_text());common=json.loads(Path(original_rollback['source_parent']['path']).read_text())
 require(len(common['link_command'])==len(rollback['link_command']),'Position-preserving scoped rollback link required')
 roles={common['compile_commands'][0][common['compile_commands'][0].index('-o')+1],common['all_Q2_optimized_monitor']['commands'][1][common['all_Q2_optimized_monitor']['commands'][1].index('-o')+1],common['routing_sharing']['commands'][2][common['routing_sharing']['commands'][2].index('-o')+1]}
 providers=[]
 for old,new in zip(common['link_command'],rollback['link_command']):
  if old!=new and Path(old).suffix=='.o'and old not in roles:
   require(seed['link_command'].count(old)==1,'One matching normal budget provider required: '+Path(old).name);seed['link_command'][seed['link_command'].index(old)]=new;providers.append(dict(original=old,selected=record(new)))
 old_engine=normal['routing_sharing']['commands'][2];new_engine=rollback['routing_sharing']['commands'][2];old_obj=old_engine[old_engine.index('-o')+1];new_obj=new_engine[new_engine.index('-o')+1]
 require(seed['link_command'].count(old_obj)==1,'One original normal engine provider required');seed['link_command'][seed['link_command'].index(old_obj)]=new_obj
 seed['inputs_before']+=active_link_inputs(placement)+active_link_inputs(rollback)+[record(a.normal),record(a.placement),record(a.rollback),record(a.comparison)];seedpath=a.out/'seed.private.json';write_json(seedpath,seed)
 selected=rollback['four_next_rollback'];old_overlay=next(Path(x['path'])for x in selected['headers']if Path(x['path']).suffix=='.json');budget=next(Path(x['path'])for x in selected['headers']if Path(x['path']).name=='device_buffer_budget.h')
 (a.out/budget.name).write_bytes(budget.read_bytes());overlay=a.out/'normal-budget.private.json';mapping=json.loads(old_overlay.read_text())
 for item in mapping['roots']:item['external-contents']=(a.out/budget.name).resolve().as_posix()
 write_json(overlay,mapping)
 source_header=Path(placement['four_next_placement']['header']['path']);header=a.out/source_header.name;header.write_text(once(source_header.read_text(),'Q2_trial_mode=false','Q2_trial_mode=true'),newline='\n')
 scope=dict(schema='ps5-qwen-four-next-normal-v1',maximum_requests=3,active_cache_slots=3072,physical_cache_planes=3073,cache_bytes=4720619520,
  original_GPU_object=True,original_single_token_GDN_fusion=True,two_token_fusion_selected=False,Gate_Up_fusion_selected=False,
  supplemental_triplets=348,total_placement_keys=768,n_rs_seq=1,complete_speculative_capture_elision=True,
  additional_application_state_allowance_bytes=124<<20,postload_device_budget_bytes=5216120832,postload_single_buffer_bytes=1677721600,
  original_physical_Direct_Flexible_OS_minimum_workspace_and_completion=True,checkpoint_pool_and_batch_policy_preserved=True,
  checkpoint_maximum_bytes=136<<20,maximum_causal_attempts=6,original_model_and_PLE_BF16=True,benchmark_checkpoint_injections=0,persistent_caches=False,automatic_retries=0)
 ec=normal['compile_commands'][0];oc=placement['all_Q2_optimized_monitor']['commands'][1];entry=Path(ec[ec.index('-c')+1]).read_text();entry=once(entry,'qwen_app::model_postload_device_budget==5086097408ull','qwen_app::model_postload_device_budget==5216120832ull')
 entry='#include <cstdint>\nextern "C" void qwen_app_compact_rollback_select(bool);\nextern "C" void qwen_app_compact_rollback_stats(std::uint64_t*);\n'+entry
 optimized=normal['all_Q2_optimized_monitor']['scope'];new_optimized=dict(optimized,supplemental_bundles=348,total_bundled_Experts=768);entry=entry.replace(literal(optimized),literal(new_optimized))
 original_limit=normal['limit_defaults']['scope'];new_limit=dict(original_limit,Expert_supplemental_triplets=348,total_bundled_Experts=768);entry=once(entry,literal(original_limit),literal(new_limit))
 entry=once(entry,'        qwen_checkpoint_trial_select(2);','        if(policy.at("native_four_next_normal")!=Json::parse('+literal(scope)+'))throw std::runtime_error("Exact two-winner normal scope required");\n        qwen_app_compact_rollback_select(true);\n        qwen_checkpoint_trial_select(2);')
 helper='''static Json four_next_report(){std::uint64_t count[2]{};qwen_app_compact_rollback_stats(count);return {{"scope",Json::parse(SCOPE_LITERAL)},{"complete_captures_elided",count[0]},{"all_memory_rollbacks",count[1]},{"placement_keys",768},{"additional_application_state_allowance_bytes",124ull<<20}};}
'''.replace('SCOPE_LITERAL',literal(scope))
 entry=once(entry,'static Json strata_followup_report()',helper+'\nstatic Json strata_followup_report()');entry=entry.replace('{"strata_followup",strata_followup_report()}', '{"four_next",four_next_report()},{"strata_followup",strata_followup_report()}')
 entry=entry.replace('Context admission failed; restart through the ordinary OS path','Context admission stopped; close the application normally')
 owner=Path(oc[oc.index('-c')+1]).read_text();ec=ec.copy()+['-ivfsoverlay',str(overlay),'-I',str(ROOT/'native/app')];oc=oc.copy()+['-ivfsoverlay',str(overlay)]
 original_owner=normal['all_Q2_optimized_monitor']['commands'][1];oc[oc.index('-o')+1]=original_owner[original_owner.index('-o')+1]
 r,jobs,sources=link(seedpath,a.out,dict(entry=(ec,entry),owner=(oc,owner)),[Path(__file__),a.comparison,header,source_header,budget,a.out/budget.name,overlay])
 write_json(a.out/'compiled-providers.private.json',dict(result=r,commands=jobs,sources=sources))
 for key in ('normal_performance','output_Q8_normal','cold_request','resident_all_Q8','resident_cache3072','resident_small_rows','resident_weight_normal'):
  r[key]['actual_sources'].update(sources);r[key]['commands'].update(jobs)
 r['all_Q2_optimized_monitor']['actual_entry']=sources['entry'];r['all_Q2_optimized_monitor']['actual_owner']=sources['owner'];r['all_Q2_optimized_monitor']['actual_engine']=rollback['routing_sharing']['actual_sources']['engine'];r['all_Q2_optimized_monitor']['commands'][:3]=[jobs['entry'],jobs['owner'],new_engine]
 r['routing_sharing']['actual_sources']['engine']=rollback['routing_sharing']['actual_sources']['engine'];r['routing_sharing']['commands'][2]=new_engine;r['routing_winners_normal']['actual_entry']=sources['entry']
 r['all_Q2_optimized_monitor']['scope']=new_optimized;r['routing_sharing']['scope']=new_optimized;r['routing_winners_normal']['scope']=new_optimized
 for key in ('normal_performance','output_Q8_normal'):r[key]['scope']=new_optimized
 r['limit_defaults'].update(scope=new_limit,actual_sources=dict(entry=sources['entry']),commands=dict(entry=jobs['entry']))
 r['strata_followup_normal'].update(actual_entry=sources['entry'],command=jobs['entry'],source_revision=revision)
 r['four_next_normal']=dict(scope=scope,actual_sources=sources,commands=jobs,source_revision=revision,comparison=record(a.comparison),selected_engine=rollback['routing_sharing']['actual_sources']['engine'],selected_engine_command=new_engine,additional_budget_providers=providers,placement_header=record(header),placement_proof=placement['four_next_placement']['pack'],rollback_scope=selected['scope'],normal_qualification_pending=True,production_adopted=False)
 # Keep explicit provider metadata consistent with the actual budget link.
 for row in r['CPU_metadata_scope']['changed_sources']:
  for replacement in providers:
   if row['object_path']==replacement['original']:
    label=next(k for k,c in selected['commands'].items()if c[c.index('-o')+1]==replacement['selected']['path']);row.update(object_path=replacement['selected']['path'],source=selected['actual_sources'][label],command=selected['commands'][label])
 seal(r,a.workspace,a.cache,a.out);write_json(a.out/'core-safety.private.json',dict(completed=True,kind='measured_two_winner_normal',candidate=record(a.out/'receipt.private.json'),source_revision=revision,scope=scope,PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()
