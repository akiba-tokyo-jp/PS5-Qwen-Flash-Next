#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compare real complete model checkpoint paths, with exact unmodified continuation."""
import argparse,copy,json,re
from pathlib import Path
from active_native_inputs import active_link_inputs
from external_shader_storage import validate_shader_resources
from build_cache_capacity_1125 import literal
from build_speculative_batch_probe import once
from expert_q4 import require,record,write_json
from scoped_native_variant import link,seal
ROOT=Path(__file__).resolve().parents[1]
SCOPE=dict(schema='ps5-qwen-complete-model-checkpoint-comparison-v1',model_loads=1,requests=16,active_cache_slots=3424,
 paired_modes=[0,0,2,2,0,1,2,1],warmup_requests_without_state_operations=2,
 complete_capture_restore_pairs_per_timed_request=7,state_operations_after_sampled_token_before_next_decode=True,
 separate_admitted_capture_and_restore_epochs=True,unknown_completion_retains_checkpoint_owner=True,
 exact_original_application_checkpoint_class=True,metadata_maximum_bytes=1<<20,logits_maximum_bytes=1<<20,
 full_F32_bytes_routes_tokens_and_output_exact=True,capacity_bucket_bytes=2<<20,maximum_checkpoint_capacity_bytes=136<<20,
 metrics_include_injected_state_operations=True,ordinary_generation_speed_claim=False,
 original_model_payloads_driver_physical_OS_minimum_and_completion=True,HTTP_requests=0,VideoOut_starts=0,automatic_retries=0,CI_runs=0)
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in('parent','pool','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();n=json.loads(a.parent.read_text());pool=json.loads(a.pool.read_text());a.out.mkdir(parents=True,exist_ok=False)
 for row in active_link_inputs(pool):require(record(row['path'])==row,'Qualified pooled provider input changed')
 require(pool['routing_sharing']['actual_sources']['cache']==n['routing_sharing']['actual_sources']['cache'],'Exact cache must accompany checkpoint GPU reuse')
 validate_shader_resources(pool['shader_resource_manifest']['path'],pool['bounded_model_source_manifest']['path'],pool['engine_receipt']['path'])
 seed=copy.deepcopy(n);original_gpu=n['lossless_shader_storage']['vulkan_object'];new_gpu=pool['lossless_shader_storage']['vulkan_object'];require(seed['link_command'].count(original_gpu['path'])==1,'One current GPU object required')
 seed['link_command'][seed['link_command'].index(original_gpu['path'])]=new_gpu['path']
 contextcmd=pool['checkpoint_device_fixture']['commands']['context'];context_source=pool['checkpoint_device_fixture']['actual_sources']['context'];context_object=record(contextcmd[contextcmd.index('-o')+1]);archive=next(x for x in seed['link_command']if x.endswith('libllama.a'));seed['link_command'].insert(seed['link_command'].index(archive),context_object['path'])
 for k in('bounded_model_source_manifest','bounded_model_source_overrides','shader_resource_manifest','lossless_shader_storage'):seed[k]=pool[k]
 seed['inputs_before']+=active_link_inputs(pool)+[record(a.pool),context_source,context_object];seedpath=a.out/'checkpoint-seed.private.json';write_json(seedpath,seed)
 ec=n['compile_commands'][0];entry=Path(ec[ec.index('-c')+1]).read_text();epoch_header=ROOT/'native/app/checkpoint_model_epoch.h';entry='#include '+json.dumps(epoch_header.as_posix())+'\n#include "model_checkpoint.h"\nextern "C" void qwen_checkpoint_trial_select(unsigned);\nextern "C" void qwen_checkpoint_trial_stats(std::uint64_t*);\n'+entry
 changes={}
 for key,member in(('all_Q2_optimized_monitor','scope'),('expert_q2_model','scope'),('output_Q8_normal','probation_scope'),('resident_all_Q8','scope'),('cold_request','scope'),('limit_margin_probe','scope')):
  old=n[key][member];new=copy.deepcopy(old)
  if new.get('maximum_requests')==14:new['maximum_requests']=16
  if literal(old)in entry:entry=entry.replace(literal(old),literal(new))
  changes[(key,member)]=new
 entry=once(entry,'constexpr unsigned request_count=14;','constexpr unsigned request_count=16;')
 guard='        if(policy.at("native_checkpoint_model_comparison")!=Json::parse('+literal(SCOPE)+'))throw std::runtime_error("Exact complete model checkpoint comparison scope required");\n'
 entry,count=re.subn(r'^        if\(policy\.at\("native_strata_cache_comparison"\)[^\n]*\n',lambda _:guard,entry,flags=re.M);require(count==1,'Replace only the inherited cache-specific test scope')
 entry=once(entry,'const bool second=false;const unsigned phase=ordinal/2,task=ordinal<10?0:ordinal-10;constexpr unsigned order[]={0,0,1,1,0};const unsigned arm=ordinal<10?order[phase]:1,hash_arm=ordinal%2;const bool compare=ordinal>=2&&ordinal<10,keep=ordinal<10&&hash_arm!=0;',
     'const bool second=false;const unsigned phase=ordinal/2,task=0;constexpr unsigned order[]={0,0,2,2,0,1,2,1};const unsigned arm=order[phase],hash_arm=ordinal%2;const bool compare=ordinal>=2,keep=hash_arm!=0;')
 entry=once(entry,'const char *arm_name=arm==0?"cache3072":"cache3424";',
     'const char *arm_name=arm==0?"checkpoint-original":arm==1?"checkpoint-pooled":"checkpoint-pooled-batch";qwen_checkpoint_trial_select(arm);')
 entry=once(entry,'qwen_app_select_output_Q8_slots(arm?3424:3072);','qwen_app_select_output_Q8_slots(3424);')
 entry=entry.replace('{"cache_slots",3072}','{"cache_slots",qwen_app_output_Q8_slots()}')
 entry=once(entry,'{"cache_reset_before_request",i>=10||i%2==0},{"active_slots",i<10&&i/2!=2&&i/2!=3?3072:3424}',
     '{"cache_reset_before_request",i%2==0},{"active_slots",3424}')
 entry=once(entry,'std::size_t rows=0;double max_error=0;bool geometry_error=false,value_error=false;',
     'std::size_t rows=0;double max_error=0;bool geometry_error=false,value_error=false,bitwise_error=false;')
 entry=once(entry,'std::copy_n(v,count,io_current.data()+rows*columns);auto&ref=io_reference[hash_arm];',
     'std::copy_n(v,count,io_current.data()+rows*columns);auto&ref=io_reference[hash_arm];if(compare&&std::memcmp(v,ref.data()+rows*columns,count*sizeof(float)))bitwise_error=true;')
 entry=once(entry,'if(compare&&arm==0&&io_max_error!=0)','if(compare&&(io_max_error!=0||bitwise_error))')
 # Equal F32 bytes imply zero KL and equal top1 without millions of redundant
 # exponentials. This remains outside the request timer in every arm.
 entry=once(entry,'if(compare){double total_kl=0;','if(compare&&io_max_error!=0){double total_kl=0;')
 entry=once(entry,'            row["phase"]=phase;',
     '            if(compare&&!bitwise_error)row["quality_distribution"]={{"positions",rows},{"mean_KL",0.0},{"top1_agreement",1.0},{"same_prefix_tokens",true},{"outside_request_timer",true},{"derived_from_exact_full_F32_bytes",true}};\n            row["phase"]=phase;')
 setup='''            std::unique_ptr<qwen_app::ModelCheckpoint>real_checkpoint(new qwen_app::ModelCheckpoint(model,context));Json checkpoint_samples=Json::array();std::uint64_t checkpoint_before[5]{},checkpoint_after[5]{};qwen_checkpoint_trial_stats(checkpoint_before);
            const auto checkpoint_prompt_text=qwen_app::render_bounded_user_prompt(chat_template,qwen_app::demo_prompt);
            const auto*checkpoint_vocab=llama_model_get_vocab(model);const int checkpoint_prompt_count=-llama_tokenize(checkpoint_vocab,checkpoint_prompt_text.data(),int(checkpoint_prompt_text.size()),nullptr,0,true,true);
            if(checkpoint_prompt_count<=0||checkpoint_prompt_count>64)throw std::runtime_error("Exact bounded checkpoint prompt required");
            std::vector<llama_token>checkpoint_prompt(checkpoint_prompt_count);
            if(llama_tokenize(checkpoint_vocab,checkpoint_prompt_text.data(),int(checkpoint_prompt_text.size()),checkpoint_prompt.data(),checkpoint_prompt_count,true,true)!=checkpoint_prompt_count)throw std::runtime_error("Checkpoint prompt tokenization changed");
'''
 entry=once(entry,'            qwen_app::CheckpointValidationStats checkpoint_baseline{};',setup+'            qwen_app::CheckpointValidationStats checkpoint_baseline{};')
 injection='''                if(ordinal>=2&&m.generated_tokens<=7){
                    if(!rows||rows>resident_reference_rows)throw std::runtime_error("Completed full-vocabulary checkpoint source required");
                    qwen_app::CheckpointApplicationState cursor;cursor.request_epoch=ordinal+1;cursor.position=llama_memory_seq_pos_max(llama_get_memory(context),0)+1;
                    cursor.pending=token.id;cursor.ready=false;cursor.prompt=checkpoint_prompt;
                    try{
                        const auto positive=[&]{llama_synchronize(context);qwen_native_driver_checkpoint();require_model_CPU_budget();};
                        const auto began=qwen_app::ProfileClock::now();{
                            qwen_app::CheckpointModelEpoch epoch(qwen_native_driver_begin,qwen_native_driver_complete,qwen_native_driver_retain);
                            real_checkpoint->capture(cursor,io_current.data()+(rows-1)*columns,columns,admit_checkpoint,qwen_native_stage,positive);epoch.complete();
                        }
                        const auto capture_ns=qwen_app::profile_elapsed_ns(began);saved_payload=real_checkpoint->payload_bytes();
                        const auto restoring=qwen_app::ProfileClock::now();{
                            qwen_app::CheckpointModelEpoch epoch(qwen_native_driver_begin,qwen_native_driver_complete,qwen_native_driver_retain);
                            const auto&restored=real_checkpoint->restore(cursor.request_epoch,qwen_native_stage,positive);
                            if(restored.position!=cursor.position||restored.pending!=cursor.pending||restored.prompt!=cursor.prompt||restored.ready)throw std::runtime_error("Complete checkpoint application cursor differs");epoch.complete();
                        }
                        const auto restore_ns=qwen_app::profile_elapsed_ns(restoring);
                        checkpoint_samples.push_back({{"generated_tokens",m.generated_tokens},{"position",cursor.position},{"payload_bytes",real_checkpoint->payload_bytes()},
                            {"metadata_bytes",real_checkpoint->metadata_bytes()},{"capture_ns",capture_ns},{"restore_ns",restore_ns},{"positions_and_application_cursor_exact",true}});
                    }catch(...){real_checkpoint.release();throw;}
                }
'''
 entry=once(entry,'            },observed_inference_stage);',injection+'            },observed_inference_stage);')
 entry=once(entry,'            engine->set_work_guard({});engine->set_logits_observer({});qwen_app_complete_predictive_expert();',
     '            qwen_checkpoint_trial_stats(checkpoint_after);\n            if(checkpoint_samples.size()!=(ordinal>=2?7u:0u))throw std::runtime_error("Declared complete model checkpoint pairs were not executed");\n            engine->set_work_guard({});engine->set_logits_observer({});qwen_app_complete_predictive_expert();')
 entry=once(entry,'            if(!routes.at(ordinal).complete)throw std::runtime_error("Complete actual additional routes required");',
     '            if(!routes.at(ordinal).complete)throw std::runtime_error("Complete actual additional routes required");\n            if(compare&&completed_route_report(routes.at(ordinal)).at("records")!=completed_route_report(routes.at(hash_arm)).at("records"))throw std::runtime_error("Checkpoint changed complete ordered Expert routes");')
 entry=once(entry,'            row["phase"]=phase;',
     '            std::array<std::uint64_t,5>checkpoint_delta{};for(unsigned c=0;c<5;++c)checkpoint_delta[c]=checkpoint_after[c]-checkpoint_before[c];\n            row["complete_model_checkpoint"]={{"mode",arm},{"samples",checkpoint_samples},{"counter_delta",checkpoint_delta},{"exact_full_F32_bytes",!bitwise_error},{"ordered_routes_exact",true},{"metrics_include_state_operations",ordinal>=2}};\n            row["phase"]=phase;')
 r,jobs,sources=link(seedpath,a.out,dict(entry=(ec,entry)),[Path(__file__),a.pool,epoch_header,ROOT/'native/app/model_checkpoint.h',ROOT/'native/app/checkpoint_device_pool_trial.h'])
 write_json(a.out/'compiled-providers.private.json',dict(result=r,commands=jobs,sources=sources))
 for(key,member),value in changes.items():r[key][member]=value
 scope=r['all_Q2_optimized_monitor']['scope'];modelscope=r['expert_q2_model']['scope']
 for key in('normal_performance','output_Q8_normal','routing_sharing','routing_winners_normal'):r[key].update(scope=scope,model_scope=modelscope)
 for key in('normal_performance','output_Q8_normal','cold_request','resident_all_Q8','resident_cache3072','resident_small_rows','resident_weight_normal','memory_quality_cohort'):
  r[key]['actual_sources']['entry']=sources['entry'];r[key]['commands']['entry']=jobs['entry']
 r['all_Q2_optimized_monitor']['actual_entry']=sources['entry'];r['all_Q2_optimized_monitor']['commands'][0]=jobs['entry'];r['routing_winners_normal']['actual_entry']=sources['entry']
 r['memory_quality_cohort'].update(requests=16,scope=scope,model_scope=modelscope);r['small_rows_cohort']['requests']=16;r['speed_followup']['requests']=16;r['strata_cache_comparison']['active_for_this_test']=False
 r['checkpoint_model_comparison']=dict(scope=SCOPE,context_source=context_source,context_object=context_object,context_command=contextcmd,pooled_GPU_source=pool['checkpoint_device_fixture']['actual_sources']['gpu'],pooled_GPU_command=pool['checkpoint_device_fixture']['commands']['gpu'],entry=sources['entry'])
 seal(r,a.workspace,a.cache,a.out);write_json(a.out/'core-safety.private.json',dict(completed=True,kind='actual_model_checkpoint_comparison',requests=16,cache_slots=3424,maximum_CPU_checkpoint_metadata_and_logits_bytes=2<<20,exact_application_checkpoint_class=True,all_original_physical_OS_minimum_and_completion=True,CPU_heap_limit_bytes=512<<20,candidate=record(a.out/'receipt.private.json'),PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()
