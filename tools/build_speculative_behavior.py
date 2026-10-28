#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build eight-input causal behavior and explicit accepted/rejected path coverage."""
import argparse
import copy
import json
import os
from pathlib import Path
import subprocess
from audit_native_imports import audit
from driver_table_storage import audit_linked_storage
from native_dispatch import audit as dispatch
from shader_storage import record

ROOT=Path(__file__).resolve().parents[1]
SCOPE=dict(schema='ps5-qwen-resident-comparison-v1',enabled=True,CPU_startup_calibration=False,
    CPU_preparation_uses_operational_floor=True,maximum_requests=28,warmup_requests=0,matched_arms_per_candidate=0,
    forced_rejection_requests=4,context_tokens=256,prefill_tokens=4,active_cache_slots=53,maximum_output_tokens=32,
    model_loads=1,GPU_start_reference_pages=3563,HTTP_requests=0,VideoOut_starts=0,
    legacy_transport_scope_overridden=True,all_original_precision_preserved=True,automatic_retries=0,performance_adoption_enabled=False)

LOOP=r'''
        const auto run=policy.at("native_first_generation_validation").at("run_id").get<std::string>();
        const auto columns=std::size_t(llama_vocab_n_tokens(llama_model_get_vocab(model)));
        if(columns!=248320)throw std::runtime_error("Original complete vocabulary required");
        std::vector<float> reference_logits(33*columns),scratch(columns);
        std::vector<std::int32_t> reference_ids;std::vector<unsigned char> reference_bytes;
        std::size_t reference_rows=0;std::string reference_reason;std::int32_t reference_minimum=-1,reference_maximum=-1;
        std::vector<CompletedRouteEvidence> routes;routes.reserve(28);
        Json completed=Json::array();
        unsigned accepted_total=0,accepted_causal=0,accepted_coverage=0,rejected_total=0;
        bool all_exact=true,forced_rejection_passed=true,coverage_complete=true;
        const auto admit_checkpoint=[&](std::uint64_t bytes){
            require_model_CPU_budget();require_unchanged_model();
            if(bytes<118038528||bytes>142606336)throw std::runtime_error("Complete checkpoint payload outside qualification");
            const auto rounded=(bytes+(2u<<20)-1)&~std::uint64_t((2u<<20)-1);
            const auto ledger=qwen_app::native_model_device_stats();const auto budget=qwen_native_allocator_budget(driver_total);
            if(ledger.live>qwen_app::model_postload_device_budget||rounded>qwen_app::model_postload_device_budget-ledger.live||
               budget.available<rounded+memory_budget.direct_reserve||observed_system_headroom()<memory_budget.flexible_reserve)
                throw std::runtime_error("Complete checkpoint cannot retain original reserves");
        };
        const auto run_arm=[&](unsigned group,const std::string &kind,unsigned forced_position){
            const unsigned ordinal=unsigned(completed.size());
            const bool control=kind=="ordinary",adaptive=kind=="causal",reject=kind=="forced-rejection",coverage=kind=="accepted-coverage";
            if(ordinal>=28)throw std::runtime_error("Finite behavior request bound exceeded");
            require_model_CPU_budget();require_unchanged_model();qwen_app_complete_predictive_expert();
            const auto previous_cache=engine->expert_cache_metrics();
            if(!previous_cache)throw std::runtime_error("Actual process-global expert counters required");
            resident_reuse_sample("before_engine_release");qwen_native_driver_begin();engine.reset();qwen_native_driver_complete();
            resident_reuse_sample("after_engine_release");qwen_app_configure_predictive_cache(false);
            qwen_native_driver_begin();resident_reset_empty_context(context,model,startup.admission_report);
            engine=std::make_unique<qwen_app::LlamaEngine>(model,context,4);
            engine->set_stage_observer(observed_inference_stage);
            engine->set_gpu_boundaries(qwen_native_driver_begin,qwen_native_driver_complete,qwen_native_driver_retain,qwen_native_driver_checkpoint);
            qwen_native_driver_complete();require_model_CPU_budget();
            if(adaptive){
                struct Cost {qwen_app::OnlineExpertVerification planner;std::uint64_t source=0;};
                auto state=std::make_shared<Cost>();qwen_app::ExpertVerificationHooks hooks;
                hooks.before_process=[state]{state->source=qwen_app::native_model_source_stats().read_ns;};
                hooks.completed_ordinary=[state](int token,std::uint64_t ns){
                    const auto after=qwen_app::native_model_source_stats().read_ns;
                    if(after<state->source||!ns)throw std::runtime_error("Incomplete causal source timing");
                    state->planner.observe(token,qwen_app::last_completed_single_token_routes(),double(ns)/1e9,double(std::min(after-state->source,ns))/1e9);
                };
                hooks.choose=[state](int pending,int draft){return state->planner.choose(pending,draft);};
                hooks.verified=[state](bool accepted,double capture,double restore){state->planner.verified(accepted,capture,restore);};
                engine->enable_expert_aware_speculation(admit_checkpoint,std::move(hooks));
            }
            if(reject||coverage)engine->enable_speculative_step_prototype(admit_checkpoint);
            const auto &input=policy.at("native_speculative_workloads").at("requests").at(group);
            const auto rendered=qwen_app::render_bounded_user_prompt(chat_template,input.at("prompt").get<std::string>());
            if(rendered!=input.at("rendered_prompt"))throw std::runtime_error("Native original chat rendering differs from frozen metadata");
            std::array<llama_token,64> tokenized{};
            const auto n=llama_tokenize(llama_model_get_vocab(model),rendered.data(),int(rendered.size()),tokenized.data(),64,true,true);
            const auto expected_ids=input.at("prompt_token_ids").get<std::vector<llama_token>>();
            if(n<=0||n>64||expected_ids.size()!=std::size_t(n)||!std::equal(expected_ids.begin(),expected_ids.end(),tokenized.begin()))
                throw std::runtime_error("Native original token IDs differ from the frozen host metadata");
            if(control){reference_rows=0;reference_ids.clear();reference_bytes.clear();}
            std::size_t seen=0;bool geometry=false,nonfinite=false,history_equal=true;
            std::array<qwen_app::LogitDifference,33> differences{};std::array<bool,33> equal_history{},has_reference{};
            engine->set_logits_observer([&](const float *values,std::size_t count)noexcept{
                if(!values||count!=columns||seen>=33){geometry=true;return;}
                for(std::size_t i=0;i<count;++i)if(!std::isfinite(values[i]))nonfinite=true;
                equal_history[seen]=history_equal;
                if(control){std::copy(values,values+count,reference_logits.data()+seen*columns);++reference_rows;}
                else if(seen<reference_rows){has_reference[seen]=true;differences[seen]=qwen_app::compare_logits(values,reference_logits.data()+seen*columns,count,scratch.data());}
                ++seen;
            });
            const bool force_possible=(coverage||reject)&&reference_ids.size()>forced_position;
            const auto correct=force_possible?reference_ids[forced_position]:0;
            const auto draft=coverage?correct:(correct==0?1:0);
            class CoverageControl final:public qwen_app::Engine{
                qwen_app::LlamaEngine&e;llama_context*context;bool force;unsigned position,calls=0;int draft;
            public:std::int32_t ending_minimum=-1,ending_maximum=-1;
                CoverageControl(qwen_app::LlamaEngine&v,llama_context*c,bool f,unsigned p,int d):e(v),context(c),force(f),position(p),draft(d){}
                std::uint32_t tokenize(const std::string&s)override{return e.tokenize(s);}
                void prefill(std::uint32_t n)override{e.prefill(n);}
                qwen_app::Token next()override{return force&&calls++==position?e.next_with_one_draft(draft):e.next();}
                void finish()override{const auto memory=llama_get_memory(context);ending_minimum=llama_memory_seq_pos_min(memory,0);
                    ending_maximum=llama_memory_seq_pos_max(memory,0);e.finish();}
                std::optional<qwen_app::ExpertCacheMetrics>expert_cache_metrics()const override{return e.expert_cache_metrics();}
            }adapter(*engine,context,force_possible,forced_position,draft);
            qwen_app::FirstGeneration trial(adapter);engine->set_work_guard([&]{trial.require_time();require_model_CPU_budget();},64);
            const auto perf=performance_snapshot(*engine);const auto cache=engine->expert_cache_metrics();const auto predicted=predictive_cache_bytes();
            if(!cache)throw std::runtime_error("Actual initial cache counters required");
            qwen_app::require_resident_context_counter_baseline(*previous_cache,*cache);qwen_app::begin_completed_expert_routes();
            const auto prefix=startup.admission_report+".arm"+std::to_string(ordinal);
            std::size_t emitted=0;
            const qwen_app::Request request{run+"-"+std::to_string(ordinal),rendered,256,32};
            const auto &result=trial.run(request,[&](const auto &bound){write_fresh_report(prefix+".intent",{
                {"id",bound.id},{"ordinal",ordinal},{"group",group},{"kind",kind},{"pid",getpid()},{"run_id",run},
                {"cache_initially_empty",true},{"maximum_output_tokens",32},{"known_control_draft",coverage},
                {"speed_measurement",false},{"native_renderer_and_token_IDs_exact",true}});},
                [&](const auto &token,const auto &m){
                    if(!control&&(emitted>=reference_ids.size()||token.id!=reference_ids[emitted]))history_equal=false;
                    ++emitted;write_fresh_report(prefix+".token-"+std::to_string(m.generated_tokens),{
                        {"token_id",token.id},{"generated_tokens",m.generated_tokens},{"elapsed_ms",m.total_ms}});
                },observed_inference_stage);
            engine->set_work_guard({});qwen_app_complete_predictive_expert();engine->set_logits_observer({});
            if(!result.request_reset_completed||geometry||nonfinite)throw std::runtime_error("Behavior request failed finite full-row/reset geometry");
            require_model_CPU_budget();require_unchanged_model();
            bool exact=control||(result.token_ids==reference_ids&&result.output_bytes==reference_bytes&&result.stop_reason==reference_reason&&
                (result.stop_reason!="end_of_generation"||(adapter.ending_minimum==reference_minimum&&adapter.ending_maximum==reference_maximum)));
            if(control){reference_ids=result.token_ids;reference_bytes=result.output_bytes;reference_reason=result.stop_reason;
                reference_minimum=adapter.ending_minimum;reference_maximum=adapter.ending_maximum;}
            const auto stats=engine->speculative_step_stats();double maximum=0;std::uint64_t outside=0;Json distribution=Json::array();
            if(!control)for(std::size_t i=0;i<seen;++i){
                auto row=qwen_app::logit_difference_report(differences[i]);row["same_committed_history"]=equal_history[i];row["reference_available"]=has_reference[i];
                distribution.push_back(row);maximum=std::max(maximum,differences[i].maximum);outside+=differences[i].outside_tolerance;
            }
            const bool rejection_ok=!reject||(stats.attempts==1&&stats.rejected==1&&!stats.accepted&&seen==reference_rows&&
                maximum==0&&exact&&reference_ids.size()>=forced_position+4);
            const bool coverage_ok=!coverage||(stats.attempts==1&&stats.accepted==1&&!stats.rejected&&stats.queued_bonus_samples==1&&exact);
            all_exact=all_exact&&exact;forced_rejection_passed=forced_rejection_passed&&rejection_ok;coverage_complete=coverage_complete&&coverage_ok;
            accepted_total+=stats.accepted;accepted_causal+=adaptive?stats.accepted:0;accepted_coverage+=coverage?stats.accepted:0;
            rejected_total+=reject?stats.rejected:0;
            routes.push_back(completed_route_evidence(*engine,perf.at("process_calls").get<std::uint64_t>(),*cache,predicted));
            Json row={{"ordinal",ordinal},{"group",group},{"name",input.at("name")},{"arm",kind},{"pid",getpid()},{"run_id",run},
                {"token_ids",result.token_ids},{"output_bytes",result.output_bytes},{"stop_reason",result.stop_reason},
                {"request_reset_completed",result.request_reset_completed},{"prompt_tokens",result.metrics.prompt_tokens},
                {"prefill_ms",result.metrics.prefill_ms},{"total_ms",result.metrics.total_ms},
                {"decode_tokens_per_second",result.metrics.decode_tokens_per_second?Json(*result.metrics.decode_tokens_per_second):Json(nullptr)},
                {"completed_performance",performance_difference(perf,*engine)},
                {"speculation",{{"attempts",stats.attempts},{"accepted",stats.accepted},{"rejected",stats.rejected},{"queued_bonus_samples",stats.queued_bonus_samples},
                    {"cost_checks",stats.cost_checks},{"cost_ordinary",stats.cost_ordinary},{"cost_width_two",stats.cost_width_two}}},
                {"full_F32_rows_observed",seen},{"reference_rows",reference_rows},{"maximum_absolute_logit_error",maximum},
                {"outside_original_tolerance",outside},{"token_IDs_and_bytes_match_control",exact},
                {"forced_rejection_F32_restore_passed",rejection_ok},{"accepted_coverage_passed",coverage_ok},
                {"known_control_draft_used",coverage},{"forced_position",(reject||coverage)?Json(forced_position):Json(nullptr)},
                {"ending_memory_minimum",adapter.ending_minimum},{"ending_memory_maximum",adapter.ending_maximum},
                {"native_renderer_and_token_IDs_exact",true},{"speed_measurement",false}};
            write_fresh_report(prefix+".logit-distribution",{{"rows",distribution},{"full_vocabulary",columns},{"timing_qualification",false}});
            completed.push_back(row);write_fresh_report(prefix+".result",row);
            resident_reuse_sample("after_completed_request");qwen_native_stage("resident_comparison_arm_completed_positive_request_reset");
            return stats.accepted;
        };
        for(unsigned group=0;group<8;++group){
            run_arm(group,"ordinary",0);
            const auto accepted=run_arm(group,"causal",0);
            if(!accepted)run_arm(group,"accepted-coverage",1);
            if(group>=1&&group<=3)run_arm(group,"forced-rejection",group);
            if(group==5)run_arm(group,"forced-rejection",4);
        }
        coverage_complete=coverage_complete&&accepted_total>=8&&rejected_total==4;
'''

def generate(text):
    text='#include "speculative_behavior_policy.h"\n'+text
    for old,new in (('resident_reuse_VM[96]','resident_reuse_VM[160]'),
                    ('resident_reuse_VM_count>=96','resident_reuse_VM_count>=160')):
        if text.count(old)!=1:raise ValueError('One exact bounded VM observer required')
        text=text.replace(old,new)
    begin=text.index('        qwen_app::require_resident_comparison_policy(policy);')
    end=text.index('\n',text.index('Exact same-batch diagnostic scope required',begin))
    text=text[:begin]+'        require_speculative_behavior_policy(policy);'+text[end:]
    begin=text.index('        const auto run=policy.at("native_first_generation_validation")',text.index('int main('))
    end=text.index('        qwen_app_complete_predictive_expert();qwen_native_driver_begin();',begin)
    text=text[:begin]+LOOP+text[end:]
    text=text.replace('if(ledger.live||!forced_rejection_passed)','if(ledger.live)')
    text=text.replace('{"all_original_tokens_and_bytes_exact",true},{"forced_rejection_and_full_F32_restore_passed",true}',
        '{"all_original_tokens_and_bytes_exact",all_exact},{"forced_rejection_and_full_F32_restore_passed",forced_rejection_passed},'
        '{"accepted_path_coverage_complete",coverage_complete},{"actual_accepted_batches",accepted_total},'
        '{"causal_accepted_batches",accepted_causal},{"diagnostic_known_control_accepted_batches",accepted_coverage},'
        '{"actual_forced_rejections",rejected_total},{"all_eight_native_inputs_executed",true},{"speed_measurement",false}')
    return text

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in('parent','workloads','workspace','cache','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();prior=json.loads(a.parent.read_text());workloads=json.loads(a.workloads.read_text())
    if len(workloads['requests'])!=8 or not workloads['ordinary_metadata_control_token_ids_match']:raise ValueError('Eight original frozen inputs required')
    frozen=list({row['path']:row for row in prior['inputs_before']+[prior['artifact']]}.values())
    for row in frozen:
        if record(row['path'])!=row:raise ValueError('Frozen diagnostic input changed: '+row['path'])
    a.out.mkdir(parents=True);(a.out/'tmp').mkdir();command=prior['compile_commands'][0].copy()
    template=Path(command[command.index('-c')+1]);source=a.out/'resident-comparison-eight-inputs.private.cpp'
    source.write_text(generate(template.read_text()),newline='\n')
    for path in template.parent.glob('*.h'):(a.out/path.name).write_bytes(path.read_bytes())
    trace=ROOT/'native/app/resident_startup_trace.h'
    trace_text=trace.read_text()
    if trace_text.count('std::array<ResidentStartupSample,64>')!=1:raise ValueError('Original bounded startup trace required')
    (a.out/trace.name).write_text(trace_text.replace('std::array<ResidentStartupSample,64>',
        'std::array<ResidentStartupSample,128>'),newline='\n')
    scope=json.dumps(json.dumps(SCOPE,separators=(',',':')));inputs=json.dumps(json.dumps(dict(requests=workloads['requests']),separators=(',',':')))
    header=a.out/'speculative_behavior_policy.h'
    header.write_text('''#pragma once
#include "resident_comparison_policy.h"
inline void require_speculative_behavior_policy(const nlohmann::json&p){
 qwen_app::require_first_generation_policy(p,false);
 const auto scope=nlohmann::json::parse(SCOPE_LITERAL);
 if(p.at("native_resident_comparison")!=scope||p.at("native_speculative_workloads")!=nlohmann::json::parse(INPUTS_LITERAL)||
 p.at("allowed_modes")!=nlohmann::json::array({"first-generation-validation"})||p.at("deployment_enabled")!=false||
 p.at("console_operations_enabled")!=true||p.at("console_validation_enabled")!=true||
 p.at("native_prefill").at("tokens")!=4||p.at("native_padded_expert_cache").at("active_slots")!=53||
 p.contains("native_large_cache_scope")||p.contains("native_prefix_validation")||p.contains("native_predictive_cache")||
 p.contains("native_model_free_speculation")||p.contains("native_speculative_same_batch_probe"))
 throw std::runtime_error("Exact finite eight-input behavior policy required");
}
'''.replace('SCOPE_LITERAL',scope).replace('INPUTS_LITERAL',inputs),newline='\n')
    old=command[command.index('-o')+1];obj=a.out/'behavior.o';command[command.index('-c')+1]=str(source);command[command.index('-o')+1]=str(obj)
    command[1:1]=['-I',str(a.out)];command+=['-I',str(template.parent)]
    link=[str(obj)if x==old else x for x in prior['link_command']];image=a.out/'qwen-native.pie.elf';link[link.index('-o')+1]=str(image)
    link=[('-Map='+str(a.out/'native-link.private.map'))if x.startswith('-Map=')else x for x in link]
    frozen+=[record(x)for x in(a.parent,a.workloads,Path(__file__),template,source,trace,ROOT/'config/speculative-qualification-workloads.json',*a.out.glob('*.h'))]
    for i,c in enumerate((command,link)):
        result=subprocess.run(c,cwd=ROOT,capture_output=True,timeout=600,env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp')))
        (a.out/f'{i}.private.log').write_bytes(result.stdout+result.stderr)
        if result.returncode:raise RuntimeError(result.stderr.decode(errors='replace')[-6000:])
        print(json.dumps(dict(eight_input_build_step=i+1,total=2)),flush=True)
    for row in frozen:
        if record(row['path'])!=row:raise ValueError('Eight-input build dependency changed')
    receipt=copy.deepcopy(prior);receipt.update(artifact=record(image),compile_commands=[command],link_command=link,source_parent=record(a.parent),
        inputs_before=frozen+[record(obj)],speculative_behavior_qualification=dict(scope=SCOPE,workloads=dict(requests=workloads['requests']),
            actual_entry=record(source),policy_header=record(header),actual_input_count=8,maximum_requests=28,
            ordinary_controls=8,causal_controllers=8,conditional_known_control_coverage_maximum=8,forced_rejections=4,
            diagnostic_known_control_drafts_never_used_for_speed=True,engine_unchanged_from_same_batch_gate=True),
        lossless_driver_table_geometry=audit_linked_storage(image,prior['lossless_driver_tables']))
    path=a.out/'receipt.private.json';path.write_text(json.dumps(receipt,indent=2)+'\n')
    receipt['real_module_import_audit']=audit(a.workspace,a.cache,a.out)
    receipt['native_dispatch_audit']=dispatch(a.workspace,a.workspace/'driver-work/PS5-Vulkan-Inference-qwen-872cc126',image,a.out/'dispatch')
    if receipt['real_module_import_audit']['missing']or not receipt['native_dispatch_audit']['passed']:raise ValueError('Native import/dispatch audit failed')
    path.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(dict(eight_input_behavior_built=True,PS5_calls=0)),flush=True)

if __name__=='__main__':main()
