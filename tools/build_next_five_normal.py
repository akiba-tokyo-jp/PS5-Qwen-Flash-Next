#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compose measured Top2/cache/placement providers with the normal API title."""
import argparse,copy,json,subprocess
from pathlib import Path
from active_native_inputs import active_link_inputs
from build_cache_capacity_1125 import literal
from build_speculative_batch_probe import once
from expert_q4 import require,record,write_json
from scoped_native_variant import link,seal
ROOT=Path(__file__).resolve().parents[1]

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for key in ('normal','candidate','analysis','workspace','cache','out'):p.add_argument('--'+key,type=Path,required=True)
 p.add_argument('--placement',type=Path);p.add_argument('--placement-analysis',type=Path)
 p.add_argument('--cold-first-only',action='store_true')
 a=p.parse_args();normal=json.loads(a.normal.read_text());candidate=json.loads(a.candidate.read_text());proof=json.loads(a.analysis.read_text())
 require(proof['completed']and proof['speed_and_finite_quality_eligible']and proof['retired'],'Measured eligible candidate required')
 require(not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT).strip(),'Commit implementation before final relink')
 revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();a.out.mkdir(parents=True,exist_ok=False)
 require(len(normal['link_command'])==len(candidate['link_command']),'Position-preserving qualified composition required')
 require(normal['lossless_shader_storage']['vulkan_object']==candidate['lossless_shader_storage']['vulkan_object'],'Preserve qualified GPU provider')
 slots=candidate['resident_cache3072']['active_slots'];planes=slots+1;cache_bytes=candidate['resident_cache3072']['cache_budget_bytes'];cap=candidate['cold_request']['device_ledger_cap_bytes']
 supplemental=348;placement=None
 if a.placement:
  require(a.placement_analysis is not None,'Measured placement analysis required');placement=json.loads(a.placement.read_text());pp=json.loads(a.placement_analysis.read_text())
  require(pp['completed']and(pp.get('cold_prefill_latency_eligible')if a.cold_first_only else pp['speed_and_finite_quality_eligible']or pp.get('latency_with_decode_nonregression_eligible'))and pp['retired'],'Improvement must be measured in the selected cold or retained scope')
  require(not a.cold_first_only or placement['next_five_placement']['scope']['expanded_placement_prefill_only'],'Cold-first mode requires the tested prefill-only provider')
  supplemental=placement['next_five_placement']['scope']['common_file_triplets']
 changes={'active_cache_slots':slots,'active_slots':slots,'cache_slots':slots,'physical_cache_planes':planes,'physical_planes':planes,
  'cache_bytes':cache_bytes,'cache_budget_bytes':cache_bytes,'Expert_supplemental_triplets':supplemental,'supplemental_triplets':supplemental,
  'supplemental_bundles':supplemental,'total_placement_keys':420+supplemental,'total_bundled_Experts':420+supplemental,
  'postload_device_budget_bytes':cap,'postload_single_buffer_bytes':candidate['resident_cache3072'].get('postload_single_buffer_bytes',1677721600)}
 def changed(value):
  if isinstance(value,list):return[changed(x)for x in value]
  if not isinstance(value,dict):return value
  return{k:(changes[k]if k in changes and type(v)is int else 'prefill_unchanged_Top2_decode'if k=='selected_Experts'and isinstance(v,str)else changed(v))for k,v in value.items()}
 seed=copy.deepcopy(normal);ec=normal['compile_commands'][0];entry=Path(ec[ec.index('-c')+1]).read_text()
 # Rewrite the exact normal contracts, preserving their three-request/API scope.
 for key,original in normal.items():
  if not isinstance(original,dict):continue
  for member in ('scope','model_scope','probation_scope'):
   if member not in original or not isinstance(original[member],dict):continue
   old=original[member];new=changed(old)
   if key=='four_next_normal':new.update(original_model_and_PLE_BF16=False,PLE_convolution_BF16_preserved=True)
   seed[key][member]=new
   if old!=new:entry=entry.replace(literal(old),literal(new))
 entry=once(entry,'qwen_app::model_postload_device_budget==5216120832ull','qwen_app::model_postload_device_budget=='+str(cap)+'ull')
 entry=once(entry,'qwen_app::model_postload_single_buffer==1677721600ull','qwen_app::model_postload_single_buffer=='+str(changes['postload_single_buffer_bytes'])+'ull')
 entry=entry.replace('{"cache_slots",3072}','{"cache_slots",'+str(slots)+'}').replace('{"active_cache_slots",3072}','{"active_cache_slots",'+str(slots)+'}')
 entry='#include "next_five_policy.h"\nextern "C" void qwen_app_select_output_Q8_slots(unsigned);\n'+entry
 scope=dict(schema='ps5-qwen-next-five-normal-v1',maximum_requests=3,decode_Experts=2,prefill_routing_unchanged=True,
  active_cache_slots=slots,physical_cache_planes=planes,cache_bytes=cache_bytes,placement_keys=420+supplemental,supplemental_triplets=supplemental,
  resident_precision='108 additional matrices Q4_0'if candidate.get('precision_candidate',{}).get('scope',{}).get('mode')=='dense-Q4'else'Q8_0',
  Attention_KV='F32',recurrent_S='F32',PLE_convolution='BF16',maximum_causal_attempts=6,n_rs_seq=1,original_GPU_object=True,
  original_OS_minimum_physical_reserves_completion_and_close=True,CI_runs=0,automatic_retries=0)
 scope.update(approximate_model_quality_reported_separately=True,semantic_misanswer_does_not_quarantine_completed_GPU_work=True)
 entry=once(entry,'            if(!counting_quality)throw std::runtime_error("Completed all-Expert Q2 counting response failed normal-app quality");',
  '            // Report approximate-answer quality without misclassifying returned inference as an unknown GPU completion.')
 if placement:scope.update(expanded_placement_prefill_only=placement['next_five_placement']['scope']['expanded_placement_prefill_only'],decode_placement_keys=768 if placement['next_five_placement']['scope']['expanded_placement_prefill_only']else 420+supplemental,expanded_placement_only_first_request=a.cold_first_only,later_request_placement_keys=768 if a.cold_first_only else 420+supplemental)
 marker='{"four_next",four_next_report()}'
 require(entry.count(marker)==2,'Both normal progress and terminal contracts required')
 entry=entry.replace(marker,marker+',{ "next_five",Json::parse('+literal(scope)+')}')
 if placement:
  entry='#include <cstdint>\nextern "C" std::uint64_t qwen_app_large_bundle_index_hits();\nextern "C" std::uint64_t qwen_app_large_bundle_decode_index_hits();\n'+entry
  entry=entry.replace(marker,marker+',{ "large_bundle_high_index_hits_total",qwen_app_large_bundle_index_hits()},{ "large_bundle_high_index_decode_hits_total",qwen_app_large_bundle_decode_index_hits()}')
  if a.cold_first_only:
   entry='extern "C" void qwen_app_io_trial_select(bool);\n'+entry
   entry=once(entry,'qwen_app_select_current_bundle(true);','qwen_app_select_current_bundle(true);qwen_app_io_trial_select(ordinal==0);')
 entry=once(entry,'        qwen_native_stage("model_load_started_after_memory_admission");',
  '        if(policy.at("native_next_five_normal")!=Json::parse('+literal(scope)+'))throw std::runtime_error("Exact measured next-five composition required");\n'
  '        qwen_next_select(2);\n        qwen_native_stage("model_load_started_after_memory_admission");')
 if slots!=3072:
  entry=once(entry,'                resident_reset_empty_context(context,model,startup.admission_report);',
   '                qwen_app_select_output_Q8_slots('+str(slots)+');\n                resident_reset_empty_context(context,model,startup.admission_report);')
 old_entry=ec[ec.index('-o')+1];candidate_entry=candidate['compile_commands'][0];position=normal['link_command'].index(old_entry)
 require(candidate['link_command'][position]==candidate_entry[candidate_entry.index('-o')+1],'Entry positions must match')
 seed['link_command']=candidate['link_command'].copy();seed['link_command'][position]=old_entry
 merged={r['path']:r for r in normal['inputs_before']};merged.update({r['path']:r for r in active_link_inputs(candidate)});seed['inputs_before']=list(merged.values())
 # Actual source-reader and shader manifests must describe the selected cache.
 for key in ('bounded_model_source_manifest','bounded_model_source_overrides','shader_resource_manifest','lossless_shader_storage','CPU_metadata_scope','resident_cache3072','additional_cache_geometry','additional_cache_layout','cache_capacity1125','shared_cache1381'):
  if key in candidate:seed[key]=copy.deepcopy(candidate[key])
 seed['next_five_comparison']=copy.deepcopy(candidate['next_five_comparison']);seed['routing_sharing']['commands'][1:]=candidate['routing_sharing']['commands'][1:]
 seed['routing_sharing']['actual_sources'].update({k:v for k,v in candidate['routing_sharing']['actual_sources'].items()if k!='entry'})
 seed['all_Q2_optimized_monitor']['commands'][1]=candidate['all_Q2_optimized_monitor']['commands'][1]
 seed['all_Q2_optimized_monitor']['actual_owner']=candidate['all_Q2_optimized_monitor']['actual_owner']
 for key in ('precision_candidate',):
  if key in candidate:seed[key]=copy.deepcopy(candidate[key])
 for index,x in enumerate(candidate_entry[:-1]):
  if x=='-ivfsoverlay'and candidate_entry[index+1]not in ec:ec=ec+['-ivfsoverlay',candidate_entry[index+1]]
 seedpath=a.out/'seed.private.json';write_json(seedpath,seed);variants=dict(entry=(ec,entry));dependencies=[Path(__file__),a.normal,a.candidate,a.analysis,ROOT/'native/app/next_five_policy.h']
 if placement:
  source_header=Path(placement['next_five_placement']['header']['path']);header=a.out/source_header.name
  header.write_text(once(source_header.read_text(),'Q2_trial_mode=false','Q2_trial_mode=true'),newline='\n')
  reader_original=Path(placement['next_five_placement']['source_reader']['path']);reader=a.out/reader_original.name;reader.write_bytes(reader_original.read_bytes())
  oc=candidate['all_Q2_optimized_monitor']['commands'][1];pc=placement['all_Q2_optimized_monitor']['commands'][1];owner_source=Path(pc[pc.index('-c')+1]);variants['owner']=(oc,owner_source.read_text());dependencies+=[a.placement,a.placement_analysis,source_header,header,reader_original,reader,owner_source]
 r,jobs,sources=link(seedpath,a.out,variants,dependencies)
 # Some normal ancestors predate the headless comparison metadata.
 for key in ('normal_performance','output_Q8_normal','cold_request','resident_all_Q8','resident_cache3072','resident_small_rows','resident_weight_normal'):
  r[key]['actual_sources'].update(sources);r[key]['commands'].update(jobs)
 r['all_Q2_optimized_monitor']['actual_entry']=sources['entry'];r['all_Q2_optimized_monitor']['commands'][0]=jobs['entry'];r['routing_winners_normal']['actual_entry']=sources['entry']
 if 'owner'in sources:r['all_Q2_optimized_monitor']['actual_owner']=sources['owner'];r['all_Q2_optimized_monitor']['commands'][1]=jobs['owner']
 r['four_next_normal'].update(actual_sources=sources,commands=jobs,source_revision=revision,normal_qualification_pending=True,production_adopted=False)
 r['strata_followup_normal'].update(actual_entry=sources['entry'],command=jobs['entry'],source_revision=revision)
 r['limit_defaults']['actual_sources']['entry']=sources['entry'];r['limit_defaults']['commands']['entry']=jobs['entry']
 r['next_five_normal']=dict(scope=scope,actual_sources=sources,commands=jobs,source_revision=revision,normal_qualification_pending=True,production_adopted=False)
 r['resident_weight_normal']['active_slots']=slots;r['cold_request']['device_ledger_cap_bytes']=cap
 seal(r,a.workspace,a.cache,a.out);write_json(a.out/'core-safety.private.json',dict(completed=True,kind='measured_next_five_normal_composition',source_revision=revision,scope=scope,candidate=record(a.out/'receipt.private.json'),PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()
