#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Validate eight causal inputs against frozen ordinary outputs and full states."""
import argparse,copy,json,os,subprocess
from pathlib import Path
from shader_storage import record
from audit_native_imports import audit
from native_dispatch import audit as dispatch
from driver_table_storage import audit_linked_storage
from wide_batch_probe_source import header_source,cpp_source,engine_source
from wide_verification_source import generate as wide_engine
ROOT=Path(__file__).resolve().parents[1]
SCOPE=dict(schema='ps5-qwen-eight-causal-adaptive-behavior-v1',enabled=True,
    CPU_startup_calibration=False,CPU_preparation_uses_operational_floor=True,maximum_requests=8,
    context_tokens=256,prefill_tokens=4,active_cache_slots=53,maximum_output_tokens=32,
    model_loads=1,HTTP_requests=0,VideoOut_starts=0,known_control_drafts=False,
    maximum_actual_attempts_per_request=8,full_state_reference_width=4,automatic_retries=0,
    speed_measurement=False,all_original_precision_preserved=True)

LOOP=r'''
        const auto run=policy.at("native_first_generation_validation").at("run_id").get<std::string>();
        const auto columns=std::size_t(llama_vocab_n_tokens(llama_model_get_vocab(model)));
        if(columns!=248320)throw std::runtime_error("Original complete F32 vocabulary required");
        qwen_app::WideBatchProbe same_width(columns);
        std::vector<CompletedRouteEvidence>routes;routes.reserve(8);Json completed=Json::array();
        bool all_exact=true;unsigned wide_probes=0,accepted_total=0,rejected_total=0;
        const auto admit_checkpoint=[&](std::uint64_t bytes){
            require_model_CPU_budget();require_unchanged_model();
            if(bytes<118038528||bytes>142606336)throw std::runtime_error("Complete original checkpoint bound exceeded");
            const auto rounded=(bytes+(2u<<20)-1)&~std::uint64_t((2u<<20)-1);
            const auto ledger=qwen_app::native_model_device_stats();const auto budget=qwen_native_allocator_budget(driver_total);
            if(ledger.live>qwen_app::model_postload_device_budget||rounded>qwen_app::model_postload_device_budget-ledger.live||
               budget.available<rounded+memory_budget.direct_reserve||observed_system_headroom()<memory_budget.flexible_reserve)
                throw std::runtime_error("Complete snapshot cannot retain original reserves");
        };
        for(unsigned ordinal=0;ordinal<8;++ordinal){
            require_model_CPU_budget();require_unchanged_model();qwen_app_complete_predictive_expert();
            const auto previous_cache=engine->expert_cache_metrics();if(!previous_cache)throw std::runtime_error("Original cache counters required");
            resident_reuse_sample("before_engine_release");qwen_native_driver_begin();engine.reset();qwen_native_driver_complete();
            resident_reuse_sample("after_engine_release");qwen_app_configure_predictive_cache(false);
            qwen_native_driver_begin();resident_reset_empty_context(context,model,startup.admission_report);
            engine=std::make_unique<qwen_app::LlamaEngine>(model,context,4);engine->set_stage_observer(observed_inference_stage);
            engine->set_gpu_boundaries(qwen_native_driver_begin,qwen_native_driver_complete,qwen_native_driver_retain,qwen_native_driver_checkpoint);
            qwen_native_driver_complete();require_model_CPU_budget();engine->enable_speculative_step_prototype(admit_checkpoint);
            const auto&input=policy.at("native_speculative_workloads").at("requests").at(ordinal);
            const auto rendered=qwen_app::render_bounded_user_prompt(chat_template,input.at("prompt").get<std::string>());
            if(rendered!=input.at("rendered_prompt"))throw std::runtime_error("Original bounded native rendering differs");
            std::array<llama_token,64>tokenized{};const auto n=llama_tokenize(llama_model_get_vocab(model),rendered.data(),int(rendered.size()),tokenized.data(),64,true,true);
            const auto ids=input.at("prompt_token_ids").get<std::vector<std::int32_t>>();
            if(n<=0||n>64||std::size_t(n)!=ids.size()||!std::equal(ids.begin(),ids.end(),tokenized.begin()))
                throw std::runtime_error("Original native token IDs differ from the frozen metadata");
            qwen_app::CausalWideEngine adapter(*engine,context,qwen_app::CausalWideMode::adaptive,ids,8);
            qwen_app::FirstGeneration trial(adapter);engine->set_work_guard([&]{trial.require_time();require_model_CPU_budget();},64);
            same_width.arm(true);std::size_t rows=0;bool finite=true;
            std::array<std::array<unsigned char,32>,33>hashes{};
            engine->set_logits_observer([&](const float*v,std::size_t count)noexcept{
                if(!v||count!=columns||rows>=33){finite=false;return;}
                for(std::size_t i=0;i<count;++i)if(!std::isfinite(v[i]))finite=false;
                sha256_hash(hashes[rows].data(),reinterpret_cast<const unsigned char*>(v),count*sizeof(float));++rows;
            });
            const auto perf=performance_snapshot(*engine);const auto cache=engine->expert_cache_metrics();const auto predicted=predictive_cache_bytes();
            qwen_app::require_resident_context_counter_baseline(*previous_cache,*cache);qwen_app::begin_completed_expert_routes();
            const auto prefix=startup.admission_report+".arm"+std::to_string(ordinal);
            const qwen_app::Request request{run+"-"+std::to_string(ordinal),rendered,256,32};
            const auto&result=trial.run(request,[&](const auto&bound){write_fresh_report(prefix+".intent",{
                {"id",bound.id},{"ordinal",ordinal},{"pid",getpid()},{"run_id",run},{"known_control_drafts",false},{"speed_measurement",false}});},
                [&](const auto&token,const auto&m){write_fresh_report(prefix+".token-"+std::to_string(m.generated_tokens),{
                    {"token_id",token.id},{"generated_tokens",m.generated_tokens},{"elapsed_ms",m.total_ms}});},observed_inference_stage);
            engine->set_work_guard({});engine->set_logits_observer({});qwen_app_complete_predictive_expert();
            const bool exact=result.token_ids==input.at("expected_token_ids").get<std::vector<std::int32_t>>()&&
                result.output_bytes==input.at("expected_output_bytes").get<std::vector<unsigned char>>()&&result.stop_reason==input.at("expected_stop_reason")&&
                (result.stop_reason!="end_of_generation"||(adapter.ending_minimum==input.at("expected_minimum")&&adapter.ending_maximum==input.at("expected_maximum")));
            const auto stats=engine->speculative_step_stats();const auto probe=same_width.report();
            const bool probed=probe.at("observations")==3;
            if(probed){++wide_probes;if(!probe.at("same_width_logits_within_original_tolerance").get<bool>()||
                !probe.at("ordinary_repeat_active_state_bit_exact").get<bool>()||!probe.at("candidate_active_state_bit_exact").get<bool>())
                throw std::runtime_error("Actual width-four same-graph full state reference differs");}
            if(!result.request_reset_completed||!finite||!rows)throw std::runtime_error("Eight-input causal request failed its complete F32/reset gate");
            accepted_total+=stats.accepted;rejected_total+=stats.rejected;all_exact=all_exact&&exact;
            routes.push_back(completed_route_evidence(*engine,perf.at("process_calls").get<std::uint64_t>(),*cache,predicted));
            Json digests=Json::array();for(std::size_t i=0;i<rows;++i){std::string value;for(auto b:hashes[i]){value+="0123456789abcdef"[b>>4];value+="0123456789abcdef"[b&15];}digests.push_back(value);}
            Json row={{"ordinal",ordinal},{"name",input.at("name")},{"arm","adaptive"},{"pid",getpid()},{"run_id",run},
                {"token_ids",result.token_ids},{"output_bytes",result.output_bytes},{"stop_reason",result.stop_reason},
                {"request_reset_completed",result.request_reset_completed},{"native_renderer_and_token_IDs_exact",true},
                {"token_IDs_and_bytes_match_control",exact},{"full_F32_rows_observed",rows},{"all_full_rows_finite",finite},
                {"full_F32_row_SHA256",digests},{"same_width_probe",probed?probe:Json(nullptr)},
                {"speculation",{{"attempts",stats.attempts},{"accepted",stats.accepted},{"rejected",stats.rejected},{"queued_bonus_samples",stats.queued_bonus_samples}}},
                {"ending_memory_minimum",adapter.ending_minimum},{"ending_memory_maximum",adapter.ending_maximum},
                {"controller_decisions",adapter.decisions()},{"controller_ns",adapter.decision_ns()},
                {"diagnostic_references_excluded_from_speed_claims",true},{"completed_performance",performance_difference(perf,*engine)}};
            completed.push_back(row);write_fresh_report(prefix+".result",row);
            resident_reuse_sample("after_completed_request");qwen_native_stage("resident_comparison_arm_completed_positive_request_reset");
        }
'''


def entry_source(text):
    text='#include "wide_batch_probe.h"\nextern "C" {\n#include "hash/sha256/sha256.h"\n}\n'+text
    begin=text.index('        qwen_app::configure_native_six_bank_refill(true);',text.index('int main('))
    end=text.index('        qwen_app_complete_predictive_expert();qwen_native_driver_begin();',begin)
    text=text[:begin]+LOOP+text[end:]
    text=text.replace('require_causal_wide_policy(policy);','require_adaptive_behavior_policy(policy);')
    text=text.replace('{"forced_rejection_and_full_F32_restore_passed",forced_rejection_passed}',
        '{"prior_three_position_rejection_qualification_reused",true}')
    begin=text.index('{"accepted_path_coverage_complete",coverage_complete}')
    end=text.index('{"all_model_source_device_owners_positively_retired"',begin)
    text=text[:begin]+'''{"eight_input_adaptive_behavior",true},{"full_width_four_state_probes",wide_probes},
            {"actual_accepted_batches",accepted_total},{"actual_rejected_batches",rejected_total},{"speed_measurement",false},
            '''+text[end:]
    return text


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in('parent','behavior-result','workspace','cache','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();prior=json.loads(a.parent.read_text());behavior=json.loads(a.behavior_result.read_text())
    frozen=list({r['path']:r for r in prior['inputs_before']+[prior['artifact']]}.values())
    for r in frozen:
        if record(r['path'])!=r:raise ValueError('Actual causal engine dependency changed: '+r['path'])
    a.out.mkdir(parents=True);(a.out/'tmp').mkdir();command=prior['compile_commands'][0].copy();template=Path(command[command.index('-c')+1])
    for h in template.parent.glob('*.h'):(a.out/h.name).write_bytes(h.read_bytes())
    workloads=copy.deepcopy(prior['causal_wide']['workloads'])
    for group,item in enumerate(workloads['requests']):
        old=next(r for r in behavior['requests']if r['group']==group and r['arm']=='ordinary')
        if not old['request_reset_completed']:raise ValueError('Every frozen ordinary request must be positively closed')
        item.update(expected_token_ids=old['token_ids'],expected_output_bytes=old['output_bytes'],expected_stop_reason=old['stop_reason'],
            expected_minimum=old['ending_memory_minimum'],expected_maximum=old['ending_memory_maximum'])
    header=a.out/'speculative_behavior_policy.h';header.write_text('''#pragma once
#include "resident_comparison_policy.h"
inline void require_adaptive_behavior_policy(const nlohmann::json&p){qwen_app::require_first_generation_policy(p,false);
 if(p.at("native_resident_comparison")!=nlohmann::json::parse(SCOPE)||p.at("native_speculative_workloads")!=nlohmann::json::parse(INPUTS)||
 p.at("native_prefill").at("tokens")!=4||p.at("native_padded_expert_cache").at("active_slots")!=53||
 p.contains("native_large_cache_scope")||p.contains("native_predictive_cache")||p.contains("native_model_free_speculation"))
 throw std::runtime_error("Exact eight-input causal behavior and full-state diagnostic scope required");}
'''.replace('SCOPE',json.dumps(json.dumps(SCOPE,separators=(',',':')))).replace('INPUTS',json.dumps(json.dumps(workloads,separators=(',',':')))),newline='\n')
    ph=ROOT/'native/app/speculative_batch_probe.h';pc=ROOT/'native/app/speculative_batch_probe.cpp';original_engine=ROOT/'native/app/llama_engine.cpp'
    wh=a.out/'wide_batch_probe.h';wc=a.out/'wide_batch_probe.private.cpp';wh.write_text(header_source(ph.read_text()),newline='\n');wc.write_text(cpp_source(pc.read_text()),newline='\n')
    engine=a.out/'llama_engine.wide-behavior.private.cpp';engine.write_text(engine_source(wide_engine(original_engine.read_text())),newline='\n')
    source=a.out/'resident-eight-adaptive-behavior.private.cpp';source.write_text(entry_source(template.read_text()),newline='\n')
    recipe=prior['causal_wide']['commands'][0].copy();old_engine=recipe[recipe.index('-o')+1];old_entry=command[command.index('-o')+1]
    commands=[];objects=[]
    for c,src in((recipe,engine),(recipe,wc),(command,source)):
        c=c.copy();obj=a.out/(src.stem+'.o');c[c.index('-c')+1]=str(src);c[c.index('-o')+1]=str(obj)
        c[1:1]=['-I',str(a.out)];c+=['-I',str(template.parent),'-I',str(ROOT/'native/app')];commands.append(c);objects.append(obj)
    replacements={old_engine:str(objects[0]),old_entry:str(objects[2])}
    link=[replacements.get(x,x)for x in prior['link_command']];link.insert(link.index(str(objects[0])),str(objects[1]))
    image=a.out/'qwen-native.pie.elf';link[link.index('-o')+1]=str(image);link=[('-Map='+str(a.out/'native-link.private.map'))if x.startswith('-Map=')else x for x in link]
    frozen +=[record(x)for x in(a.parent,a.behavior_result,Path(__file__),ROOT/'tools/wide_batch_probe_source.py',ph,pc,original_engine,
        template,source,engine,wc,*a.out.glob('*.h'))]
    for i,c in enumerate(commands+[link]):
        r=subprocess.run(c,cwd=ROOT,capture_output=True,timeout=600,env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp')))
        (a.out/f'{i}.private.log').write_bytes(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace')[-5000:])
        print(json.dumps(dict(adaptive_behavior_build_step=i+1,total=4)),flush=True)
    for r in frozen:
        if record(r['path'])!=r:raise ValueError('Frozen adaptive behavior source changed')
    receipt=copy.deepcopy(prior);receipt.update(artifact=record(image),compile_commands=[commands[-1]],link_command=link,
        source_parent=record(a.parent),inputs_before=frozen+[record(x)for x in objects],
        adaptive_behavior=dict(scope=SCOPE,workloads=workloads,commands=commands,actual_entry=record(source),actual_engine=record(engine),
            full_state_probe_header=record(wh),full_state_probe_source=record(wc),ordinary_reference_reused=record(a.behavior_result),
            known_control_drafts=False),lossless_driver_table_geometry=audit_linked_storage(image,prior['lossless_driver_tables']))
    target=a.out/'receipt.private.json';target.write_text(json.dumps(receipt,indent=2)+'\n')
    receipt['real_module_import_audit']=audit(a.workspace,a.cache,a.out)
    receipt['native_dispatch_audit']=dispatch(a.workspace,a.workspace/'driver-work/PS5-Vulkan-Inference-qwen-872cc126',image,a.out/'dispatch')
    if receipt['real_module_import_audit']['missing']or not receipt['native_dispatch_audit']['passed']:raise ValueError('Adaptive behavior import/dispatch audit failed')
    target.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(dict(adaptive_behavior_native_build_complete=True,PS5_calls=0)),flush=True)


if __name__=='__main__':main()
