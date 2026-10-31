#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compare ordinary model decoding, with checkpoint coverage in untimed tasks."""
import argparse,copy,json
from pathlib import Path
from active_native_inputs import active_link_inputs
from external_shader_storage import validate_shader_resources
from build_cache_capacity_1125 import literal
from build_speculative_batch_probe import once
from expert_q4 import require,record,write_json
from scoped_native_variant import link,seal
ROOT=Path(__file__).resolve().parents[1]
SCOPE=dict(schema='ps5-qwen-GDN-ordinary-model-comparison-v1',model_loads=1,requests=14,active_cache_slots=3424,
 warmup_requests=2,ordinary_benchmark_requests=8,ordinary_paired_fusion_order=[0,0,1,1,0],quality_tasks=4,
 benchmark_checkpoint_injections=0,quality_checkpoint_pairs='min(7,generated_tokens)',checkpoint_mode=2,
 full_F32_finite_and_distributions=True,baseline_F32_bytes_and_routes_exact=True,candidate_full_vocab_bit_equality_required=False,
 all_counting_tokens_and_outputs_equal=True,original_model_payloads=True,original_PLE_BF16_preserved=True,
 additional_immutable_shader_count=1,additional_shader_SHA256_before_Vulkan=True,original_shader_registry_unchanged=True,
 original_driver_physical_OS_minimum_and_positive_completion=True,HTTP_requests=0,VideoOut_starts=0,automatic_retries=0,CI_runs=0)
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in('parent','gdn','fixture','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 p.add_argument('--reuse-compiled-GPU',type=Path)
 a=p.parse_args();n=json.loads(a.parent.read_text());g=json.loads(a.gdn.read_text());proof=json.loads(a.fixture.read_text());a.out.mkdir(parents=True,exist_ok=False)
 require(proof['completed']and proof['GPU_graphs']==144 and proof['F64_reference_all_outputs_passed']and proof['additional_shader_verified']==1,'Completed full-state F64 shader fixture required')
 for row in active_link_inputs(g):require(record(row['path'])==row,'Qualified GDN input changed')
 require(g['routing_sharing']['actual_sources']['cache']==n['routing_sharing']['actual_sources']['cache'],'One exact cache must accompany the GDN provider')
 validate_shader_resources(g['shader_resource_manifest']['path'],g['bounded_model_source_manifest']['path'],g['engine_receipt']['path'])
 seed=copy.deepcopy(n);oldgpu=n['lossless_shader_storage']['vulkan_object'];qualified_gpu=g['lossless_shader_storage']['vulkan_object'];seed['link_command'][seed['link_command'].index(oldgpu['path'])]=qualified_gpu['path']
 assetcmd=g['GDN_conv_normalization_fixture']['commands']['assets'];asset_source=g['GDN_conv_normalization_fixture']['actual_sources']['assets'];asset_obj=record(assetcmd[assetcmd.index('-o')+1]);old_asset=None
 for row in seed['CPU_metadata_scope']['changed_sources']:
  if row['object_path']in seed['link_command']and 'extern "C" const void *qwen_app_prepare_shader_code('in Path(row['source']['path']).read_text():
   require(old_asset is None,'Unique shader asset provider required');old_asset=row['object_path'];row.update(source=asset_source,object_path=asset_obj['path'],command=assetcmd)
 require(old_asset is not None,'Selected shader asset provider required');seed['link_command'][seed['link_command'].index(old_asset)]=asset_obj['path']
 for k in('bounded_model_source_manifest','bounded_model_source_overrides','shader_resource_manifest','lossless_shader_storage'):seed[k]=g[k]
 seed['inputs_before']+=active_link_inputs(g)+[record(a.gdn),record(a.fixture),asset_source,asset_obj];seedpath=a.out/'GDN-model-seed.private.json';write_json(seedpath,seed)
 gpu_cmd=g['GDN_conv_normalization_fixture']['commands']['gpu'];gpu_text=Path(g['GDN_conv_normalization_fixture']['actual_sources']['gpu']['path']).read_text()
 # Keep the F64-qualified shader and dispatch unchanged. Decline non-convolution
 # nodes before loading their operands; this does not alter any accepted shape.
 body=(ROOT/'native/app/gdn_conv_norm_backend.inc').read_text();body=once(body,'    QwenConvNormMatch out;','    QwenConvNormMatch out;\n    if(graph->nodes[first]->op!=GGML_OP_SSM_CONV)return out;')
 backend=a.out/'gdn_conv_norm_model_backend.private.inc';backend.write_text(body,newline='\n')
 gpu_text=once(gpu_text,'#include "gdn_conv_norm_backend.inc"','#include "gdn_conv_norm_model_backend.private.inc"')+'\n#include "checkpoint_vk_batch.inc"\n'
 ec=n['compile_commands'][0];entry=Path(ec[ec.index('-c')+1]).read_text();entry='#include <cstdint>\n#include "additional_shader_assets.h"\nextern "C" void qwen_app_conv_norm_trial_select(bool);\nextern "C" std::uint64_t qwen_app_conv_norm_trial_selections();\nextern "C" void qwen_app_conv_norm_trial_release();\n'+entry
 changes={}
 for key,member in(('all_Q2_optimized_monitor','scope'),('expert_q2_model','scope'),('output_Q8_normal','probation_scope'),('resident_all_Q8','scope'),('cold_request','scope'),('limit_margin_probe','scope')):
  old=n[key][member];new=copy.deepcopy(old)
  if new.get('maximum_requests')==16:new['maximum_requests']=14
  if literal(old)in entry:entry=entry.replace(literal(old),literal(new))
  changes[(key,member)]=new
 entry=once(entry,'constexpr unsigned request_count=16;','constexpr unsigned request_count=14;')
 entry=once(entry,'policy.at("native_checkpoint_model_comparison")!=Json::parse('+literal(n['checkpoint_model_comparison']['scope'])+')',
     'policy.at("native_GDN_model_comparison")!=Json::parse('+literal(SCOPE)+')')
 entry=once(entry,'        screen.state="loading original BF16 model";',
     '        if(qwen_app_additional_shaders_verified()!=1)throw std::runtime_error("One separately SHA256-admitted convolution normalization shader required");\n        screen.state="loading original BF16 model";')
 entry=once(entry,'const bool second=false;const unsigned phase=ordinal/2,task=0;constexpr unsigned order[]={0,0,2,2,0,1,2,1};const unsigned arm=order[phase],hash_arm=ordinal%2;const bool compare=ordinal>=2,keep=hash_arm!=0;',
     'const bool second=false;const unsigned phase=ordinal/2,task=ordinal<10?0:ordinal-10;constexpr unsigned order[]={0,0,1,1,0};const unsigned arm=ordinal<10?order[phase]:1,hash_arm=ordinal%2;const bool compare=ordinal>=2&&ordinal<10,keep=ordinal<10&&hash_arm!=0;')
 entry=once(entry,'const char *arm_name=arm==0?"checkpoint-original":arm==1?"checkpoint-pooled":"checkpoint-pooled-batch";qwen_checkpoint_trial_select(arm);',
     'const char *arm_name=arm==0?"original-convolution-normalization":"fused-convolution-normalization";qwen_checkpoint_trial_select(2);qwen_app_conv_norm_trial_select(arm==1);')
 entry=once(entry,'const auto checkpoint_prompt_text=qwen_app::render_bounded_user_prompt(chat_template,qwen_app::demo_prompt);',
     'const auto checkpoint_prompt_text=qwen_app::render_bounded_user_prompt(chat_template,task?speed_prompts[task-1]:qwen_app::demo_prompt);')
 entry=once(entry,'if(ordinal>=2&&m.generated_tokens<=7)','if(ordinal>=10&&m.generated_tokens<=7)')
 entry=once(entry,'checkpoint_samples.size()!=(ordinal>=2?7u:0u)','checkpoint_samples.size()!=(ordinal>=10?std::min<std::size_t>(7,result.metrics.generated_tokens):0u)')
 entry=once(entry,'if(compare&&(io_max_error!=0||bitwise_error))','if(compare&&arm==0&&(io_max_error!=0||bitwise_error))')
 entry=once(entry,'if(compare&&completed_route_report(routes.at(ordinal)).at("records")!=completed_route_report(routes.at(hash_arm)).at("records"))throw std::runtime_error("Checkpoint changed complete ordered Expert routes");',
     'const bool same_routes=!compare||completed_route_report(routes.at(ordinal)).at("records")==completed_route_report(routes.at(hash_arm)).at("records");if(compare&&arm==0&&!same_routes)throw std::runtime_error("Original GDN changed complete ordered Expert routes");')
 entry=once(entry,'{"mode",arm},{"samples",checkpoint_samples}', '{"mode",2},{"samples",checkpoint_samples}')
 entry=once(entry,'{"ordered_routes_exact",true},{"metrics_include_state_operations",ordinal>=2}',
     '{"ordered_routes_exact",same_routes},{"routes_comparison_performed",compare},{"metrics_include_state_operations",ordinal>=10}')
 entry=once(entry,'{"cache_reset_before_request",i%2==0},{"active_slots",3424}',
     '{"cache_reset_before_request",i>=10||i%2==0},{"active_slots",3424}')
 entry=once(entry,'const auto gdn_before=0ull;','const auto gdn_before=qwen_app_conv_norm_trial_selections();')
 entry=once(entry,'row["GDN_candidate_pipeline_selections"]=0ull-gdn_before;',
     'row["GDN_candidate_pipeline_selections"]=qwen_app_conv_norm_trial_selections()-gdn_before;')
 entry=once(entry,'llama_model_free(model);model=nullptr;qwen_native_driver_complete();',
     'llama_model_free(model);model=nullptr;qwen_app_conv_norm_trial_release();qwen_native_driver_complete();')
 # The asset header is unique; preserve every existing include precedence.
 entrycmd=ec.copy();entrycmd+=['-I',str(ROOT/'native/app')]
 inputs=[Path(__file__),a.gdn,a.fixture,backend,ROOT/'native/app/checkpoint_vk_batch.inc',ROOT/'native/app/additional_shader_assets.h',*[
     Path(v['path'])for v in g['GDN_conv_normalization_fixture']['headers']]]
 variants=dict(gpu=(gpu_cmd,gpu_text),entry=(entrycmd,entry));reused=None
 if a.reuse_compiled_GPU:
  prior=a.reuse_compiled_GPU;src=prior/'gpu.private.cpp';obj=prior/'gpu.o';inc=prior/backend.name
  require(src.read_text()==gpu_text and inc.read_bytes()==backend.read_bytes(),'Reused GPU source and private include must be exactly equal')
  require(obj.is_file()and obj.stat().st_mtime_ns>=src.stat().st_mtime_ns,'Compiled GPU object required')
  require((prior/'0.private.log').is_file(),'Prior GPU compile log required')
  actual=gpu_cmd.copy();oldsrc=Path(actual[actual.index('-c')+1]);actual[actual.index('-c')+1]=str(src);actual[actual.index('-o')+1]=str(obj);actual[1:1]=['-I',str(oldsrc.parent),'-I',str(prior)]
  if '-MF'in actual:actual[actual.index('-MF')+1]=str(prior/'gpu.private.d')
  seed['link_command'][seed['link_command'].index(qualified_gpu['path'])]=str(obj);seed['inputs_before'] +=[record(src),record(obj),record(inc),record(prior/'0.private.log')];write_json(seedpath,seed)
  inputs +=[src,obj,inc,prior/'0.private.log'];variants=dict(entry=(entrycmd,entry));reused=dict(source=record(src),object=record(obj),actual_include=record(inc),expected_include=record(backend),command=actual,source_and_private_include_exact=True)
 r,jobs,sources=link(seedpath,a.out,variants,inputs)
 if reused:jobs['gpu']=reused['command'];sources['gpu']=reused['source'];r['reused_GDN_GPU_compile']=reused
 write_json(a.out/'compiled-providers.private.json',dict(result=r,commands=jobs,sources=sources))
 for(key,member),value in changes.items():r[key][member]=value
 scope=r['all_Q2_optimized_monitor']['scope'];modelscope=r['expert_q2_model']['scope']
 for key in('normal_performance','output_Q8_normal','routing_sharing','routing_winners_normal'):r[key].update(scope=scope,model_scope=modelscope)
 for key in('normal_performance','output_Q8_normal','cold_request','resident_all_Q8','resident_cache3072','resident_small_rows','resident_weight_normal','memory_quality_cohort'):
  r[key]['actual_sources']['entry']=sources['entry'];r[key]['commands']['entry']=jobs['entry']
 r['all_Q2_optimized_monitor']['actual_entry']=sources['entry'];r['all_Q2_optimized_monitor']['commands'][0]=jobs['entry'];r['routing_winners_normal']['actual_entry']=sources['entry']
 r['memory_quality_cohort'].update(requests=14,scope=scope,model_scope=modelscope);r['small_rows_cohort']['requests']=14;r['speed_followup']['requests']=14;r['checkpoint_model_comparison']['active_for_this_test']=False
 r['io_gpu_comparison'].update(GPU_command=jobs['gpu'],GPU_source=sources['gpu'])
 r['GDN_model_comparison']=dict(scope=SCOPE,actual_sources=sources,commands=jobs,asset_source=asset_source,asset_object=asset_obj,asset_command=assetcmd,
     F64_fixture=record(a.fixture),original_shader_header=next(v for v in g['GDN_conv_normalization_fixture']['headers']if v['path'].endswith('qwen_conv_norm_spirv.private.h')),backend=record(backend),pool_context=n['checkpoint_model_comparison'])
 unsealed=a.out/'unsealed-link.private.json';write_json(unsealed,r)
 done=__import__('subprocess').run([__import__('sys').executable,'-X','utf8','-B',str(ROOT/'tools/rebind_gpu_provenance.py'),'--linked',str(unsealed),'--out',str(a.out/'GPU-provenance')],capture_output=True,timeout=600)
 (a.out/'GPU-provenance.private.log').write_bytes(done.stdout+done.stderr);require(done.returncode==0,done.stderr.decode(errors='replace')[-3500:])
 r=json.loads((a.out/'GPU-provenance/receipt.private.json').read_text());seal(r,a.workspace,a.cache,a.out)
 write_json(a.out/'core-safety.private.json',dict(completed=True,kind='ordinary_GDN_model_comparison',requests=14,cache_slots=3424,benchmark_requests_have_no_injected_state_work=True,four_semantic_tasks_include_checkpoint_coverage=True,all_original_model_driver_physical_OS_minimum_and_completion=True,candidate=record(a.out/'receipt.private.json'),PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()
