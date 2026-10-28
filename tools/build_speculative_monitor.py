#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build the bounded prefix/delivery monitor with a final-consumer handoff."""
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
from build_speculative_batch_probe import engine_source as probed_engine
from build_speculative_speed import once

ROOT=Path(__file__).resolve().parents[1]

def engine_source(text):
    text=probed_engine(text)
    text='#include "prefix_speculative_handoff.h"\n'+text
    old='    enable_model_free_speculation(std::move(admit));expert_hooks_=std::move(hooks);'
    new='''    if(final_prefix_handoff.pending(this,context_)) {
        if(producer_!=std::this_thread::get_id()||failed_||!checkpoint_||!checkpoint_->saved()||
           !ready_||position_!=30||pending_!=LLAMA_TOKEN_NULL||!prefix_stats_.enabled||!prefix_stats_.request_hit||
           prefix_stats_.captures!=1||prefix_stats_.restores!=1||prefix_stats_.last_reused_prompt_tokens!=30||
           checkpoint_stats_.enabled||speculative_stats_.enabled||!admit||!gpu_begin_||!gpu_complete_||!gpu_retain_||!gpu_checkpoint_)
            throw std::runtime_error("Final prefix handoff requires its exact completed original state");
        final_prefix_handoff.consume(this,context_,checkpoint_->payload_bytes(),position_);
        checkpoint_admit_=std::move(admit);speculative_stats_.enabled=true;speculative_stats_.controller_enabled=true;
        speculative_committed_tokens_.reserve(32);
    } else enable_model_free_speculation(std::move(admit));
    expert_hooks_=std::move(hooks);'''
    return once(text,old,new)

def entry_source(text,scope,expected):
    text='#include "prefix_speculative_handoff.h"\n#include "speculative_batch_probe.h"\nextern "C" {\n#include "hash/sha256/sha256.h"\n}\n'+text
    marker='        const Json production_scope='
    at=text.index(marker)
    guard='''        if(policy.at("native_prefix_speculative_handoff")!=Json::parse(SCOPE)||
           !policy.at("native_speculative_same_width_diagnostic").is_boolean())
            throw std::runtime_error("Exact closed speculative handoff provenance required");
        const bool monitor_spec_probe=policy.at("native_speculative_same_width_diagnostic").get<bool>();
'''.replace('SCOPE',json.dumps(json.dumps(scope,separators=(',',':'))))
    text=text[:at]+guard+text[at:]
    text=once(text,'                const auto rounded=(bytes+(2u<<20)-1)&~std::uint64_t((2u<<20)-1);',
        '''                const auto rounded=qwen_app::final_prefix_handoff.new_allocation(context,bytes);
                if(qwen_app::final_prefix_handoff.consumed()) {
                    const auto observed=qwen_app::observe_native_system_memory();
                    if(observed.kernel_minimum!=898||observed.kernel_reserved!=206||observed.kernel_free<981)
                        throw qwen_app::KernelMemoryPressure();
                }''')
    text=once(text,'if(rounded>qwen_app::model_postload_device_budget-stats.live)',
        'if(stats.live>qwen_app::model_postload_device_budget||rounded>qwen_app::model_postload_device_budget-stats.live)')
    setup='''
            qwen_app::SpeculativeBatchProbe monitor_same_batch(monitor_columns);
            std::vector<float> monitor_scratch(monitor_columns);
            std::array<qwen_app::LogitDifference,23> monitor_differences{};
            std::array<std::array<unsigned char,32>,23> monitor_hashes[2]{};
            std::vector<std::int32_t> monitor_control_ids;
            std::vector<unsigned char> monitor_control_bytes;
            qwen_app::SpeculativeStepStats monitor_spec_stats{};
            Json monitor_probe=nullptr;
            const auto monitor_expected_ids=Json::parse(EXPECTED).get<std::vector<std::int32_t>>();
'''.replace('EXPECTED',json.dumps(json.dumps(expected,separators=(',',':'))))
    text=once(text,'            double monitor_maximum_F32_error=0;',setup+'\n            double monitor_maximum_F32_error=0;')
    begin=text.index('                    std::size_t monitor_rows=0;',text.index('const auto demo ='))
    end=text.index('                    if(ordinal==1)engine->enable_prefix_reuse',begin)
    text=text[:begin]+'''                    monitor_same_batch.arm(ordinal==2&&monitor_spec_probe);
                    std::size_t monitor_rows=0;bool monitor_geometry_error=false,monitor_value_error=false;
                    engine->set_logits_observer([&](const float *values,std::size_t count)noexcept{
                        if(!values||count!=monitor_columns||monitor_rows>=23){monitor_geometry_error=true;return;}
                        for(std::size_t i=0;i<count;++i)if(!std::isfinite(values[i]))monitor_value_error=true;
                        sha256_hash(monitor_hashes[ordinal-1][monitor_rows].data(),reinterpret_cast<const unsigned char*>(values),count*sizeof(float));
                        if(ordinal==1){std::copy(values,values+count,monitor_reference_logits.data()+monitor_rows*monitor_columns);++monitor_reference_rows;}
                        else if(monitor_rows>=monitor_reference_rows){monitor_geometry_error=true;return;}
                        else {auto &d=monitor_differences[monitor_rows];d=qwen_app::compare_logits(values,monitor_reference_logits.data()+monitor_rows*monitor_columns,count,monitor_scratch.data());
                            monitor_value_error=monitor_value_error||!d.finite||d.candidate_top[0]!=d.reference_top[0];
                            monitor_maximum_F32_error=std::max(monitor_maximum_F32_error,d.maximum);++monitor_compared_rows;}
                        ++monitor_rows;
                    });
'''+text[end:]
    old='                    qwen_app::FirstGeneration attempt(*engine);'
    new='''                    class FinalConsumer final:public qwen_app::Engine {
                        qwen_app::LlamaEngine&e;llama_context*c;bool enabled;std::function<void(std::uint64_t)>admit;
                    public:
                        FinalConsumer(qwen_app::LlamaEngine&v,llama_context*x,bool on,std::function<void(std::uint64_t)>a):e(v),c(x),enabled(on),admit(std::move(a)){}
                        std::uint32_t tokenize(const std::string&s)override{return e.tokenize(s);}
                        void prefill(std::uint32_t n)override{
                            e.prefill(n);if(!enabled)return;
                            const auto p=e.prefix_reuse_stats();
                            qwen_app::final_prefix_handoff.arm(&e,c,2,p.request_hit&&p.restores==1&&p.last_reused_prompt_tokens==30);
                            struct Cost {qwen_app::OnlineExpertVerification planner;std::uint64_t source=0;bool used=false;};
                            auto state=std::make_shared<Cost>();qwen_app::ExpertVerificationHooks hooks;
                            hooks.before_process=[state]{state->source=qwen_app::native_model_source_stats().read_ns;};
                            hooks.completed_ordinary=[state](int token,std::uint64_t ns){const auto after=qwen_app::native_model_source_stats().read_ns;
                                if(after<state->source||!ns)throw std::runtime_error("Completed causal source timing required");
                                state->planner.observe(token,qwen_app::last_completed_single_token_routes(),double(ns)/1e9,double(std::min(after-state->source,ns))/1e9);};
                            hooks.choose=[state](int pending,int draft){return state->used?1:state->planner.choose(pending,draft);};
                            hooks.verified=[state](bool accepted,double capture,double restore){state->planner.verified(accepted,capture,restore);state->used=true;};
                            e.enable_expert_aware_speculation(admit,std::move(hooks));
                        }
                        qwen_app::Token next()override{return e.next();}
                        void finish()override{e.finish();}
                        std::optional<qwen_app::ExpertCacheMetrics>expert_cache_metrics()const override{return e.expert_cache_metrics();}
                    }monitor_consumer(*engine,context,ordinal==2,admit_complete_checkpoint);
                    qwen_app::FirstGeneration attempt(monitor_consumer);'''
    # This line appears only in the active bounded API callback.
    text=once(text,old,new)
    marker='                    monitor_prefix_stats.at(ordinal-1)=engine->prefix_reuse_stats();'
    text=once(text,marker,marker+'''
                    if(generated.token_ids!=monitor_expected_ids)throw std::runtime_error("Actual API output differs from closed ordinary counting tokens");
                    if(ordinal==1){monitor_control_ids=generated.token_ids;monitor_control_bytes=generated.output_bytes;
                        qwen_app::final_prefix_handoff.certify(engine.get(),context,engine->checkpoint_validation_stats().maximum_payload_bytes,generated.request_reset_completed);}
                    else {
                        if(generated.token_ids!=monitor_control_ids||generated.output_bytes!=monitor_control_bytes)
                            throw std::runtime_error("Actual handoff greedy continuation differs");
                        monitor_spec_stats=engine->speculative_step_stats();
                        if(monitor_spec_stats.attempts!=1||monitor_spec_stats.accepted!=1||monitor_spec_stats.rejected||monitor_spec_stats.queued_bonus_samples!=1||!qwen_app::final_prefix_handoff.consumed())
                            throw std::runtime_error("Final prefix handoff requires one actual accepted causal batch and bonus");
                        if(monitor_spec_probe){monitor_probe=monitor_same_batch.report();
                            if(!monitor_probe.at("same_width_logits_within_original_tolerance").get<bool>()||
                               !monitor_probe.at("ordinary_repeat_active_state_bit_exact").get<bool>()||
                               !monitor_probe.at("candidate_active_state_bit_exact").get<bool>())
                                throw std::runtime_error("Actual passive handoff same-width reference or complete state differs");}
                    }
''')
    # The original performance helper selects v6 from actual engine counters.
    # Keep the older prefill-time speculative activation branch disabled.
    if text.count('if(speculative_model_candidate&&ordinal==2)')!=1:
        raise ValueError('Exact historical activation boundary required')
    begin=text.index('            if(!monitor_first.complete||!monitor_second.complete||')
    end=text.index('            const auto &prefix_first=',begin)
    text=text[:begin]+'''            if(!monitor_first.complete||!monitor_second.complete)
                throw std::runtime_error("Both complete original native route captures required");
'''+text[end:]
    text=once(text,'{"maximum_absolute_F32_error",monitor_maximum_F32_error},{"all_original_expert_selections_exact",true}',
        '{"maximum_absolute_F32_error",monitor_maximum_F32_error},{"all_original_expert_geometry_present",true}')
    marker='            write_fresh_report(startup.admission_report+".cache128-monitor",'
    at=text.index(marker)
    report='''            Json monitor_hash_report=Json::array(),monitor_distribution=Json::array();
            static const char monitor_hex[]="0123456789abcdef";
            for(unsigned request_index=0;request_index<2;++request_index){Json hashes=Json::array();
                for(const auto &hash:monitor_hashes[request_index]){std::string value;value.reserve(64);for(auto b:hash){value+=monitor_hex[b>>4];value+=monitor_hex[b&15];}hashes.push_back(value);}
                monitor_hash_report.push_back(hashes);}
            for(const auto &d:monitor_differences)monitor_distribution.push_back(qwen_app::logit_difference_report(d));
'''
    text=text[:at]+report+text[at:]
    marker='{"maximum_absolute_F32_error",monitor_maximum_F32_error},'
    text=once(text,marker,marker+'''
                {"schema_extension","ps5-qwen-prefix-speculative-monitor-v1"},{"same_width_probe_enabled",monitor_spec_probe},
                {"same_width_probe",monitor_probe},{"full_F32_row_SHA256",monitor_hash_report},{"full_F32_distribution",monitor_distribution},
                {"prefix_snapshot_handed_off_after_positive_final_restore",true},{"known_control_drafts_used",false},
                {"speculation",{{"attempts",monitor_spec_stats.attempts},{"accepted",monitor_spec_stats.accepted},{"rejected",monitor_spec_stats.rejected},{"queued_bonus_samples",monitor_spec_stats.queued_bonus_samples}}},
                {"snapshot_replacement",{{"old_logical_bytes",qwen_app::FinalPrefixHandoff::prefix_bytes},{"new_logical_bytes",qwen_app::FinalPrefixHandoff::speculative_bytes},
                    {"equal_rounded_capacity_bytes",qwen_app::FinalPrefixHandoff::rounded(qwen_app::FinalPrefixHandoff::prefix_bytes)},{"old_buffer_freed_before_new_allocation",true},{"new_Direct_metadata_allowance_pages",19}}},
''')
    return text

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in('parent','speed-native','reference','speed-review','behavior-review','probe-review','application-recipe','workspace','cache','out'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();reviews=[json.loads(x.read_text())for x in(a.speed_review,a.behavior_review,a.probe_review)]
    if not all(r['summary']['passed']for r in reviews):raise ValueError('All three closed correctness/speed gates required')
    prior=json.loads(a.parent.read_text());speed=json.loads(a.speed_native.read_text());reference=json.loads(a.reference.read_text())
    frozen=list({x['path']:x for r in(prior,speed,reference)for x in r['inputs_before']+[r['artifact']]}.values())
    for row in frozen:
        if record(row['path'])!=row:raise ValueError('Qualified compiled dependency changed: '+row['path'])
    pinned=a.cache/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569/src/llama-context.cpp'
    writer=pinned.read_text();segment=writer[writer.index('class llama_io_write_device'):writer.index('class llama_io_read_device')]
    if segment.count('mbuf_cur = std::move(mbuf);')!=2 or segment.index('mbuf_cur = std::move(mbuf);')>segment.index('mbuf_cur.buf.reset(ggml_backend_alloc_ctx_tensors_from_buft'):
        raise ValueError('Pinned replacement must release the old owner before allocating the new buffer')
    a.out.mkdir(parents=True);(a.out/'tmp').mkdir()
    scope=dict(schema='ps5-qwen-prefix-speculative-handoff-v1',final_request_ordinal=2,maximum_actual_attempts=1,
        same_engine_class_layout=True,old_prefix_snapshot_bytes=119881728,new_speculative_snapshot_bytes=120311808,
        old_buffer_freed_before_new_allocation=True,allocator_caps_changed=False,
        speed_review_SHA256=record(a.speed_review)['sha256'],behavior_review_SHA256=record(a.behavior_review)['sha256'],probe_review_SHA256=record(a.probe_review)['sha256'])
    command=prior['compile_commands'][0].copy();base=Path(command[command.index('-c')+1]);source=a.out/'speculative-monitor.private.cpp'
    expected=json.loads((a.cache/'hardware-first-generation-5720/native-arm0.result.private.json').read_text())['token_ids']
    source.write_text(entry_source(base.read_text(),scope,expected),newline='\n')
    for path in base.parent.glob('*.h'):(a.out/path.name).write_bytes(path.read_bytes())
    for name in('prefix_speculative_handoff.h','speculative_batch_probe.h','logit_difference.h'):(a.out/name).write_bytes((ROOT/'native/app'/name).read_bytes())
    qualified_engine=Path(speed['speculative_speed_qualification']['actual_engine']['path'])
    engine=a.out/'llama_engine.handoff.private.cpp';engine.write_text(engine_source(qualified_engine.read_text()),newline='\n')
    app=json.loads(a.application_recipe.read_text());ec=next(c.copy()for c in app['compile_commands']if '-c'in c and Path(c[c.index('-c')+1]).name=='llama_engine.cpp')
    old_engine=next(x for x in prior['link_command']if Path(x).name.startswith('llama_engine-')and x.endswith('.o'))
    old_main=command[command.index('-o')+1];objects=[];commands=[]
    for i,(c,src)in enumerate(((ec,engine),(command,source))):
        obj=a.out/f'{i}.o';c[c.index('-c')+1]=str(src);c[c.index('-o')+1]=str(obj);c[1:1]=['-I',str(a.out)];c+=['-I',str(base.parent),'-I',str(ROOT/'native/app')];commands.append(c);objects.append(obj)
    helper=next(x for x in reference['link_command']if Path(x).name=='1.o'and 'speculative-same-batch-'in x)
    link=[str(objects[0])if x==old_engine else str(objects[1])if x==old_main else x for x in prior['link_command']]
    link.insert(link.index(str(objects[0])),helper);image=a.out/'qwen-native.pie.elf';link[link.index('-o')+1]=str(image)
    link=[('-Map='+str(a.out/'native-link.private.map'))if x.startswith('-Map=')else x for x in link]
    frozen+=[record(x)for x in(a.parent,a.speed_native,a.reference,a.speed_review,a.behavior_review,a.probe_review,a.application_recipe,
        Path(__file__),ROOT/'tools/build_speculative_batch_probe.py',ROOT/'tools/build_speculative_speed.py',pinned,base,qualified_engine,source,engine,*a.out.glob('*.h'))]
    for i,c in enumerate(commands+[link]):
        r=subprocess.run(c,cwd=ROOT,capture_output=True,timeout=600,env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp')))
        (a.out/f'{i}.private.log').write_bytes(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace')[-6500:])
        print(json.dumps(dict(speculative_monitor_build_step=i+1,total=3)),flush=True)
    for row in frozen:
        if record(row['path'])!=row:raise ValueError('Frozen monitor input changed')
    receipt=copy.deepcopy(prior);receipt.update(artifact=record(image),compile_commands=[commands[-1]],link_command=link,inputs_before=frozen+[record(x)for x in objects],
        speculative_monitor=dict(scope=scope,original_engine_class_layout_unchanged=True,original_ggml_and_driver_unchanged=True,
            qualification_and_normal_mode_same_SELF=True,actual_entry=record(source),actual_engine=record(engine),commands=commands),
        lossless_driver_table_geometry=audit_linked_storage(image,prior['lossless_driver_tables']))
    path=a.out/'receipt.private.json';path.write_text(json.dumps(receipt,indent=2)+'\n')
    receipt['real_module_import_audit']=audit(a.workspace,a.cache,a.out)
    receipt['native_dispatch_audit']=dispatch(a.workspace,a.workspace/'driver-work/PS5-Vulkan-Inference-qwen-872cc126',image,a.out/'dispatch')
    if receipt['real_module_import_audit']['missing']or not receipt['native_dispatch_audit']['passed']:raise ValueError('Monitor import/dispatch audit failed')
    path.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(dict(speculative_monitor_built=True,PS5_calls=0)),flush=True)

if __name__=='__main__':main()
