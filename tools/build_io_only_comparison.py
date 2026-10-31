#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Isolate bundle placement with the exact installed Vulkan application object."""
import argparse,copy,json,shlex
from pathlib import Path
from build_speculative_batch_probe import once
from build_cache_capacity_1125 import literal
from active_native_inputs import active_link_inputs
from expert_q4 import record,write_json,require
from scoped_native_variant import link,seal
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in('parent','control','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();n=json.loads(a.parent.read_text());control=json.loads(a.control.read_text());a.out.mkdir(parents=True,exist_ok=False)
 seed=copy.deepcopy(n);old=n['io_gpu_comparison']['GPU_command'];old_object=old[old.index('-o')+1];original=control['lossless_shader_storage']['vulkan_object'];require(seed['link_command'].count(old_object)==1,'One application Vulkan provider required');seed['link_command'][seed['link_command'].index(old_object)]=original['path']
 for k in('bounded_model_source_manifest','bounded_model_source_overrides','shader_resource_manifest','lossless_shader_storage'):
  seed[k]=control[k]
 rows={r['path']:r for r in seed['inputs_before']}
 for r in active_link_inputs(control):
  if r['path']in rows:require(rows[r['path']]==r,'Conflicting original input')
  rows[r['path']]=r
 seed['inputs_before']=list(rows.values());seed_path=a.out/'seed.private.json';write_json(seed_path,seed)
 ec=n['compile_commands'][0];entry=Path(ec[ec.index('-c')+1]).read_text();scopes=[]
 for old_scope in(n['all_Q2_optimized_monitor']['scope'],n['expert_q2_model']['scope'],n['output_Q8_normal']['probation_scope']):
  new=dict(old_scope,maximum_requests=10);entry=once(entry,literal(old_scope),literal(new));scopes.append(new)
 entry=once(entry,'constexpr unsigned request_count=16;','constexpr unsigned request_count=10;');entry=once(entry,'constexpr unsigned order[]={0,0,1,1,0,2,2,0};','constexpr unsigned order[]={0,0,1,1,0};')
 for line in('extern "C" void qwen_app_gdn_trial_select(bool);\n','extern "C" std::uint64_t qwen_app_gdn_trial_selections();\n','extern "C" void qwen_app_gdn_trial_release();\n'):
  entry=once(entry,line,'')
 entry=once(entry,'qwen_app_gdn_trial_select(arm==2);','');entry=once(entry,'qwen_app_gdn_trial_release();','');entry=entry.replace('qwen_app_gdn_trial_selections()','std::uint64_t(0)')
 result,jobs,sources=link(seed_path,a.out,dict(entry=(ec,entry)),[Path(__file__),a.parent,a.control])
 for k in('normal_performance','output_Q8_normal','cold_request','resident_all_Q8','resident_cache3072','resident_small_rows','resident_weight_normal','memory_quality_cohort'):
  result[k]['actual_sources'].update(sources);result[k]['commands'].update(jobs)
 scope,model,probation=scopes
 for k in('normal_performance','output_Q8_normal','routing_sharing','routing_winners_normal'):result[k].update(scope=scope,model_scope=model)
 result['output_Q8_normal']['probation_scope']=probation;result['expert_q2_model']['scope']=model;result['all_Q2_optimized_monitor'].update(scope=scope,actual_entry=sources['entry']);result['all_Q2_optimized_monitor']['commands'][0]=jobs['entry'];result['routing_winners_normal']['actual_entry']=sources['entry']
 result['memory_quality_cohort'].update(requests=10,independent_pairs=5,scope=scope,model_scope=model);result['small_rows_cohort']['requests']=10;result['speed_followup'].update(requests=10,phases=['warmup','A','B','B','A'])
 result['io_gpu_comparison'].update(requests=10,pairs=5,order=[0,0,1,1,0],GPU_application_object=original,unchanged_installed_GPU_application=True,GPU_candidate_included=False)
 result['io_only_comparison']=dict(requests=10,original_GPU_application_object=original,original_SPIRV_and_driver_unchanged=True,all_original_reserves=True)
 seal(result,a.workspace,a.cache,a.out);write_json(a.out/'core-safety.private.json',dict(completed=True,kind='io_only_current_miss_comparison',original_physical_and_kernel_guards_preserved=True,CPU_heap_limit_bytes=512<<20,cache_slots=3072,driver_unchanged=True,original_GPU_application_object=original,candidate=record(a.out/'receipt.private.json'),PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()
