#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Integrate measured checkpoint/GPU winners while preserving decode-priority3072."""
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
 for k in('normal','checkpoint','providers','comparison','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();normal=json.loads(a.normal.read_text());cp=json.loads(a.checkpoint.read_text());gpu=json.loads(a.providers.read_text());proof=json.loads(a.comparison.read_text())
 require(proof['candidate_comparisons_completed']and proof['checkpoint_pool_eligible']and proof['checkpoint_batch_eligible'],'Closed actual-model checkpoint winners required')
 use_gpu=proof['GDN_eligible'];selected=gpu if use_gpu else cp
 for row in active_link_inputs(selected)+active_link_inputs(normal):require(record(row['path'])==row,'Qualified provider changed')
 require(not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT).strip(),'Commit exact source before the final relink')
 revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();a.out.mkdir(parents=True,exist_ok=False)
 scope=dict(schema='ps5-qwen-strata-followup-normal-v1',maximum_requests=3,active_cache_slots=3072,physical_cache_planes=3073,
  cache_bytes=4720619520,checkpoint_pool_capacity_quantum_bytes=2<<20,checkpoint_maximum_bytes=136<<20,
  checkpoint_metadata_arena_reuse=True,independent_same_operation_copy_batch=True,
  convolution_SiLU_QK_RMS_scale_fusion=use_gpu,fusion_single_token_F32_only=use_gpu,
  independent_single_token_QK_normalizations_before_head_repeats=use_gpu,Vulkan_fusion_span_and_external_input_allocation_dependencies=use_gpu,
  original_PLE_BF16_and_all_model_payloads=True,original_driver_physical_OS_minimum_workspace_and_completion=True,
  unknown_owner_retention=True,persistent_caches=False,benchmark_checkpoint_injections=0,automatic_retries=0)
 seed=copy.deepcopy(normal);before=seed['lossless_shader_storage']['vulkan_object'];after=selected['lossless_shader_storage']['vulkan_object']
 require(seed['link_command'].count(before['path'])==1,'Unique GPU replacement required');seed['link_command'][seed['link_command'].index(before['path'])]=after['path']
 for key in('bounded_model_source_manifest','bounded_model_source_overrides','shader_resource_manifest','lossless_shader_storage'):seed[key]=selected[key]
 context=cp['checkpoint_model_comparison'];archive=next(x for x in seed['link_command']if Path(x).name=='libllama.a')
 ctxobj=context['context_object'];require(ctxobj['path']not in seed['link_command'],'New explicit pooled context required');seed['link_command'].insert(seed['link_command'].index(archive),ctxobj['path'])
 if use_gpu:
  model=gpu['GDN_model_graph_order'];seed['link_command'].insert(seed['link_command'].index(archive),model['object']['path'])
  asset=gpu['GDN_model_comparison'];found=[]
  for row in seed['CPU_metadata_scope']['changed_sources']:
   if row['object_path']in seed['link_command']and 'extern "C" const void *qwen_app_prepare_shader_code('in Path(row['source']['path']).read_text():found.append(row)
  require(len(found)==1,'One original shader asset provider required');row=found[0];seed['link_command'][seed['link_command'].index(row['object_path'])]=asset['asset_object']['path']
  row.update(source=asset['asset_source'],object_path=asset['asset_object']['path'],command=asset['asset_command'])
  seed['GDN_model_graph_order']=model;seed['GDN_model_planner']=gpu['GDN_model_planner']
 seed['io_gpu_comparison']=selected['io_gpu_comparison'];seed['inputs_before'] +=active_link_inputs(cp)+active_link_inputs(gpu)+[record(a.normal),record(a.checkpoint),record(a.providers),record(a.comparison)]
 seedpath=a.out/'seed.private.json';write_json(seedpath,seed)
 ec=normal['compile_commands'][0];entry=Path(ec[ec.index('-c')+1]).read_text()
 prefix='''#include <cstdint>
#include "device_buffer_budget.h"
static_assert(qwen_app::model_postload_device_budget==5086097408ull,"Original3072 device budget required");
static_assert(qwen_app::model_postload_single_buffer==1677721600ull,"Original1600MiB bank bound required");
extern "C" void qwen_checkpoint_trial_select(unsigned);
extern "C" void qwen_checkpoint_trial_stats(std::uint64_t*);
'''
 if use_gpu:prefix+='''#include "additional_shader_assets.h"
extern "C" void qwen_app_conv_norm_trial_select(bool);
extern "C" std::uint64_t qwen_app_conv_norm_trial_selections();
extern "C" void qwen_app_conv_norm_trial_release();
extern "C" void qwen_app_conv_norm_planner_stats(std::uint64_t*);
'''
 entry=prefix+entry;select='        qwen_checkpoint_trial_select(2);\n'
 entry=entry.replace('Model load failed; restart through the ordinary OS path','Loading stopped; keep the current state and close the application normally')
 if use_gpu:select+='        if(qwen_app_additional_shaders_verified()!=1)throw std::runtime_error("One immutable SHA256-admitted GDN shader required");qwen_app_conv_norm_trial_select(true);\n'
 entry=once(entry,'        screen.state="loading original BF16 model";',
  '        if(policy.at("native_strata_followup_normal")!=Json::parse('+literal(scope)+'))throw std::runtime_error("Exact measured Strata policy required");\n'+select+'        screen.state="loading original BF16 model";')
 helper='''static Json strata_followup_report(){std::uint64_t counters[5]{};qwen_checkpoint_trial_stats(counters);
 Json out={{"scope",Json::parse(SCOPE_LITERAL)},{"checkpoint_pool_stats",{counters[0],counters[1],counters[2],counters[3],counters[4]}}};GPU_REPORT return out;}
'''.replace('SCOPE_LITERAL',literal(scope)).replace('GPU_REPORT',
  'std::uint64_t planner[8]{};qwen_app_conv_norm_planner_stats(planner);out["GDN_planner_stats"]=std::vector<std::uint64_t>(planner,planner+8);out["GDN_pipeline_selections"]=qwen_app_conv_norm_trial_selections();out["additional_shaders_verified"]=qwen_app_additional_shaders_verified();'if use_gpu else'out["GDN_pipeline_selections"]=0;')
 entry=once(entry,'static Json memory_backpressure_report()',helper+'\nstatic Json memory_backpressure_report()')
 entry=once(entry,'{"memory_backpressure",memory_backpressure_report()}','{"strata_followup",strata_followup_report()},{"memory_backpressure",memory_backpressure_report()}')
 if use_gpu:entry=once(entry,'engine.reset();llama_free(context);context=nullptr;llama_model_free(model);model=nullptr;qwen_native_driver_complete();',
  'engine.reset();llama_free(context);context=nullptr;llama_model_free(model);model=nullptr;qwen_app_conv_norm_trial_release();qwen_native_driver_complete();')
 command=ec.copy();command+=['-I',str(ROOT/'native/app')]
 r,jobs,sources=link(seedpath,a.out,dict(entry=(command,entry)),[Path(__file__),a.comparison,ROOT/'native/app/checkpoint_device_pool_trial.h',ROOT/'native/app/additional_shader_assets.h'])
 write_json(a.out/'compiled-providers.private.json',dict(result=r,commands=jobs,sources=sources))
 for key in('normal_performance','output_Q8_normal','cold_request','resident_all_Q8','resident_cache3072','resident_small_rows','resident_weight_normal'):
  r[key]['actual_sources']['entry']=sources['entry'];r[key]['commands']['entry']=jobs['entry']
 r['all_Q2_optimized_monitor']['actual_entry']=sources['entry'];r['all_Q2_optimized_monitor']['commands'][0]=jobs['entry'];r['routing_winners_normal']['actual_entry']=sources['entry']
 r['limit_defaults'].update(actual_sources=dict(entry=sources['entry']),commands=dict(entry=jobs['entry']))
 r['strata_followup_normal']=dict(scope=scope,actual_entry=sources['entry'],command=jobs['entry'],source_revision=revision,comparison=record(a.comparison),
  selected_context=context,selected_GPU=after,normal_qualification_pending=True,production_adopted=False,
  cache3424_not_selected='Retained decode regresses despite improved TTFT/whole response; keep decode-priority3072')
 rebind_cache(r,a.out/'cache-provenance',r['routing_sharing']['commands'][1],r['routing_sharing']['actual_sources']['cache'])
 seal(r,a.workspace,a.cache,a.out)
 write_json(a.out/'core-safety.private.json',dict(completed=True,kind='measured_strata_followup_normal',cache_slots=3072,GDN=use_gpu,
  checkpoint_injections=0,original_model_driver_physical_OS_workspace_and_completion=True,candidate=record(a.out/'receipt.private.json'),source_revision=revision,PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()
