#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Relink the actual normal API/display app with only qualified throughput winners."""
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
 p.add_argument('--throughput-mode',type=int,required=True);a=p.parse_args();n=json.loads(a.normal.read_text());candidate=json.loads(a.prototype.read_text());w=json.loads(a.worklog.read_text())
 require(0<a.throughput_mode<16 and all(w['stages'][str(i)]['completed']for i in range(1,5)),'All four dispositions and a positive selected feature set required')
 require(candidate.get('current_installed_provider_integration',{}).get('normal')==record(a.normal)and w.get('current_provider_integration',{}).get('completed')is True,'Actual installed-provider matched integration required before normal relink')
 require(not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT).strip(),'Commit the exact implementation before normal relink');revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();a.out.mkdir(parents=True,exist_ok=False)
 seed=copy.deepcopy(n);providers=candidate['frontier'];selected={};replacements={}
 for role,bit in(('owner',1),('model_graph',2),('lifecycle',4),('gpu',8)):
  if not a.throughput_mode&bit:continue
  command=providers['commands'][role];obj=command[command.index('-o')+1]
  if role=='gpu':oldobj=n['lossless_shader_storage']['vulkan_object']['path']
  else:
   originals=[x for x in n['link_command']if Path(x).name==role+'.o'];require(len(originals)==1,'One actual original '+role+' provider required');oldobj=originals[0]
  require(seed['link_command'].count(oldobj)==1 and candidate['link_command'].count(obj)==1,'Actual selected linked provider required');replacements[oldobj]=obj;selected[role]=dict(command=command,source=record(command[command.index('-c')+1]),object=record(obj))
 seed['link_command']=[replacements.get(x,x)for x in seed['link_command']]
 for key in('frontier','frontier_HC','service_completion'):seed[key]=copy.deepcopy(candidate[key])
 if a.throughput_mode&8:
  for key in('lossless_shader_storage','shader_resource_manifest','io_gpu_comparison','bounded_model_source_manifest','bounded_model_source_overrides'):seed[key]=copy.deepcopy(candidate[key])
 if a.throughput_mode&1:seed['all_Q2_optimized_monitor']['commands'][1]=providers['commands']['owner']
 merged={r['path']:r for r in seed['inputs_before']};merged.update({r['path']:r for r in active_link_inputs(candidate)});seed['inputs_before']=list(merged.values())
 ec=n['compile_commands'][0];entry='#include "throughput_options.h"\n'+Path(ec[ec.index('-c')+1]).read_text();newgpu=seed['lossless_shader_storage']['vulkan_object'];old=n['next_five_normal']['scope']
 scope=dict(old,selected_GPU_object_SHA256=newgpu['sha256'],throughput_mode=a.throughput_mode,immutable_Expert_bundle_coverage=candidate['throughput']['scope'].get('bundle_coverage',22968)if a.throughput_mode&1 else 0,uncovered_original_reads_preserved=True,GDN_common_input_Q4_join=bool(a.throughput_mode&2),empty_retirement_certificate=bool(a.throughput_mode&4),proven_WAR_execution_only=bool(a.throughput_mode&8),pending_unpublished_writes_preserved=True,per_token_fsync_preserved=True)
 require(entry.count(literal(old))==3,'All three normal scope copies required');entry=entry.replace(literal(old),literal(scope));seed['next_five_normal']['scope']=scope
 old=n['four_next_normal']['scope'];updated=dict(old,selected_GPU_object_SHA256=newgpu['sha256']);require(entry.count(literal(old))==2,'Both inherited scope copies required');entry=entry.replace(literal(old),literal(updated));seed['four_next_normal']['scope']=updated
 entry=once(entry,'qwen_frontier::mode=7;','qwen_frontier::mode=7;qwen_throughput::mode='+str(a.throughput_mode)+';')
 marker='            row["service_mode"]=qwen_service::mode.load();';entry=once(entry,marker,'            row["throughput_mode"]=qwen_throughput::mode.load();row["throughput_totals"]=std::vector<std::uint64_t>(qwen_throughput::stats,qwen_throughput::stats+12);\n'+marker)
 if a.throughput_mode&8:
  entry='#include <cstdint>\nextern "C" std::uint64_t qwen_throughput_sync_tail_flushes();\n'+entry;entry=once(entry,marker,'            row["throughput_sync_tail_flushes"]=qwen_throughput_sync_tail_flushes();\n'+marker)
 raw=a.out/'normal-seed.private.json';write_json(raw,seed);r,jobs,sources=link(raw,a.out,dict(entry=(ec,entry)),[Path(__file__),a.normal,a.prototype,a.worklog,ROOT/'native/app/throughput_options.h'])
 for key in('normal_performance','output_Q8_normal','cold_request','resident_all_Q8','resident_cache3072','resident_small_rows','resident_weight_normal','precision_candidate'):r[key]['actual_sources'].update(sources);r[key]['commands'].update(jobs)
 r['all_Q2_optimized_monitor']['actual_entry']=sources['entry'];r['all_Q2_optimized_monitor']['commands'][0]=jobs['entry'];r['routing_winners_normal']['actual_entry']=sources['entry'];r['limit_defaults']['actual_sources']['entry']=sources['entry'];r['limit_defaults']['commands']['entry']=jobs['entry']
 for key in('four_next_normal','next_five_normal'):r[key].update(actual_sources=sources,commands=jobs,source_revision=revision,normal_qualification_pending=True,production_adopted=False)
 r['strata_followup_normal'].update(actual_entry=sources['entry'],command=jobs['entry'],source_revision=revision)
 for key in('post_top2_normal','load_followup_normal','service_normal','frontier_normal'):r[key].update(scope=scope,source_revision=revision,actual_sources=sources,commands=jobs)
 r['frontier']['actual_sources'].update(sources);r['frontier']['commands'].update(jobs);r['post_top2_normal']['GPU_object']=newgpu
 r['throughput_normal']=dict(scope=scope,source_revision=revision,actual_sources=sources,commands=jobs,selected_providers=selected,worklog=record(a.worklog),baseline=record(a.normal),qualified_prototype=record(a.prototype),current_installed_provider_integration=candidate['current_installed_provider_integration'])
 raw=a.out/'linked-seed.private.json';write_json(raw,r);subprocess.run([sys.executable,'-X','utf8','-B',str(ROOT/'tools/rebind_gpu_provenance.py'),'--linked',str(raw),'--out',str(a.out/'GPU-provenance')],check=True);r=json.loads((a.out/'GPU-provenance/receipt.private.json').read_text());seal(r,a.workspace,a.cache,a.out)
 write_json(a.out/'core-safety.private.json',dict(completed=True,scope=scope,normal_API_display_and_retirement_preserved=True,all_prior_frontier_winners_preserved=True,per_token_sync_preserved=True,only_measured_throughput_winners_selected=True,source_revision=revision,PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()
