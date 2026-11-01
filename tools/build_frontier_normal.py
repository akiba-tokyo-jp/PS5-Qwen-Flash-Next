#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Relink the qualified normal API/display app with only completed frontier winners."""
import argparse,copy,json,subprocess,sys
from pathlib import Path
from active_native_inputs import active_link_inputs
from build_cache_capacity_1125 import literal
from build_speculative_batch_probe import once
from expert_q4 import record,require,write_json
from scoped_native_variant import link,seal
ROOT=Path(__file__).resolve().parents[1]

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in('normal','prototype','workspace','cache','out','worklog'):p.add_argument('--'+k,type=Path,required=True)
 p.add_argument('--frontier-mode',type=int,required=True);a=p.parse_args();n=json.loads(a.normal.read_text());candidate=json.loads(a.prototype.read_text());w=json.loads(a.worklog.read_text());require(all(w['stages'][str(i)]['completed']for i in range(1,5)),'Complete all four dispositions before normal composition');require(not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT).strip(),'Commit exact implementation before normal relink');revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();a.out.mkdir(parents=True,exist_ok=False)
 seed=copy.deepcopy(n);providers=candidate['frontier'];oldgpu=n['lossless_shader_storage']['vulkan_object'];newgpu=candidate['lossless_shader_storage']['vulkan_object'];replacements={oldgpu['path']:newgpu['path']}
 for role in('lifecycle','model_graph'):
  command=providers['commands'][role];obj=command[command.index('-o')+1]
  if role=='lifecycle':
   objects=[x for x in n['link_command']if Path(x).name=='lifecycle.o'];require(len(objects)==1,'One current lifecycle provider required');oldobj=objects[0]
  else:
   objects=[x for x in n['link_command']if Path(x).name=='model_graph.o'];require(len(objects)==1,'One current model graph provider required');oldobj=objects[0]
  require(seed['link_command'].count(oldobj)==1,'One linked old provider required');replacements[oldobj]=obj
 seed['link_command']=[replacements.get(x,x)for x in seed['link_command']]
 for key in('lossless_shader_storage','shader_resource_manifest','io_gpu_comparison','frontier','frontier_HC','service_completion'):seed[key]=copy.deepcopy(candidate[key])
 merged={r['path']:r for r in seed['inputs_before']};merged.update({r['path']:r for r in active_link_inputs(candidate)});seed['inputs_before']=list(merged.values());ec=n['compile_commands'][0];entry=Path(ec[ec.index('-c')+1]).read_text();entry='#include "frontier_options.h"\nextern "C" void qwen_frontier_owner_stats(std::uint64_t*);\nextern "C" void qwen_frontier_HC_stats(std::uint64_t*);\n'+('extern "C" void qwen_frontier_command_stats(std::uint64_t*);\n'if a.frontier_mode&16 else'')+entry
 split=8 if a.frontier_mode&8 else(4 if a.frontier_mode&4 else 2)
 old=n['next_five_normal']['scope'];scope=dict(old,selected_GPU_object_SHA256=newgpu['sha256'],frontier_mode=a.frontier_mode,owner_generation_checkpoint_reuse=bool(a.frontier_mode&1),HC_joined_immutable_Q8=bool(a.frontier_mode&2),HC_prefill_split_two=split==2,HC_prefill_split_K=split,recorded_command_cache=bool(a.frontier_mode&16),per_token_fsync_preserved=True)
 require(entry.count(literal(old))==3,'All normal scope copies required');entry=entry.replace(literal(old),literal(scope));seed['next_five_normal']['scope']=scope
 old=n['four_next_normal']['scope'];updated=dict(old,selected_GPU_object_SHA256=newgpu['sha256']);require(entry.count(literal(old))==2,'Both four-next scope copies required');entry=entry.replace(literal(old),literal(updated));seed['four_next_normal']['scope']=updated
 entry=once(entry,'qwen_service::mode=69;','qwen_service::mode=69;qwen_frontier::mode='+str(a.frontier_mode)+';')
 marker='            row["service_mode"]=qwen_service::mode.load();';extra='            std::uint64_t owner_epoch[4]{},hc_joint[4]{};qwen_frontier_owner_stats(owner_epoch);qwen_frontier_HC_stats(hc_joint);row["frontier_owner_totals"]=std::vector<std::uint64_t>(owner_epoch,owner_epoch+4);row["frontier_HC_totals"]=std::vector<std::uint64_t>(hc_joint,hc_joint+4);row["frontier_mode"]=qwen_frontier::mode.load();\n'
 if a.frontier_mode&16:extra+='            std::uint64_t command_totals[8]{};qwen_frontier_command_stats(command_totals);row["frontier_command_totals"]=std::vector<std::uint64_t>(command_totals,command_totals+8);\n'
 entry=once(entry,marker,extra+marker);raw=a.out/'normal-seed.private.json';write_json(raw,seed);r,jobs,sources=link(raw,a.out,dict(entry=(ec,entry)),[Path(__file__),a.normal,a.prototype,a.worklog,ROOT/'native/app/frontier_options.h',ROOT/'native/app/owner_checkpoint_certificate.h'])
 for key in('normal_performance','output_Q8_normal','cold_request','resident_all_Q8','resident_cache3072','resident_small_rows','resident_weight_normal','precision_candidate'):r[key]['actual_sources'].update(sources);r[key]['commands'].update(jobs)
 r['all_Q2_optimized_monitor']['actual_entry']=sources['entry'];r['all_Q2_optimized_monitor']['commands'][0]=jobs['entry'];r['routing_winners_normal']['actual_entry']=sources['entry'];r['limit_defaults']['actual_sources']['entry']=sources['entry'];r['limit_defaults']['commands']['entry']=jobs['entry']
 for key in('four_next_normal','next_five_normal'):r[key].update(actual_sources=sources,commands=jobs,source_revision=revision,normal_qualification_pending=True,production_adopted=False)
 r['strata_followup_normal'].update(actual_entry=sources['entry'],command=jobs['entry'],source_revision=revision)
 for key in('post_top2_normal','load_followup_normal','service_normal'):r[key].update(scope=scope,source_revision=revision,actual_sources=sources,commands=jobs)
 r['post_top2_normal']['GPU_object']=newgpu;r['frontier_normal']=dict(scope=scope,source_revision=revision,actual_sources=sources,commands=jobs,selected_providers=copy.deepcopy(providers),worklog=record(a.worklog))
 raw=a.out/'linked-seed.private.json';write_json(raw,r);subprocess.run([sys.executable,'-X','utf8','-B',ROOT/'tools/rebind_gpu_provenance.py','--linked',raw,'--out',a.out/'GPU-provenance'],check=True);r=json.loads((a.out/'GPU-provenance/receipt.private.json').read_text());seal(r,a.workspace,a.cache,a.out);write_json(a.out/'core-safety.private.json',dict(completed=True,normal_API_display_and_retirement_preserved=True,per_token_sync_preserved=True,scope=scope,PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()
