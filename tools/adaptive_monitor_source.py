#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Generate a separately qualified passive adaptive profile and keep counting available."""
import json
from build_speculative_batch_probe import once
from wide_verification_source import generate as wide_engine
from wide_batch_probe_source import engine_source as wide_probe_engine
from build_resident_adaptive import engine_source as replacement_engine


def engine_source(original,legacy):
    text=replacement_engine(wide_probe_engine(wide_engine(original)))
    text='#include "adaptive_monitor_profile.h"\n#include "prefix_speculative_handoff.h"\n'+text
    begin=legacy.index('void LlamaEngine::enable_expert_aware_speculation(')
    end=legacy.index('void LlamaEngine::capture_checkpoint_in_active_epoch()',begin)
    a=text.index('void LlamaEngine::enable_expert_aware_speculation(');b=text.index('void LlamaEngine::capture_checkpoint_in_active_epoch()',a)
    text=text[:a]+legacy[begin:end]+text[b:]
    marker='''void LlamaEngine::enable_speculative_step_prototype(std::function<void(std::uint64_t)> admit) {
    require_healthy();'''
    return once(text,marker,marker+'''
    if(adaptive_final_prefix.pending(this,context_)){
        if(producer_!=std::this_thread::get_id()||failed_||!checkpoint_||!checkpoint_->saved()||!ready_||
           position_!=25||pending_!=LLAMA_TOKEN_NULL||!prefix_stats_.enabled||!prefix_stats_.request_hit||
           prefix_stats_.captures!=1||prefix_stats_.restores!=1||prefix_stats_.last_reused_prompt_tokens!=25||
           checkpoint_stats_.enabled||speculative_stats_.enabled||!admit||!gpu_begin_||!gpu_complete_||!gpu_retain_||!gpu_checkpoint_)
            throw std::runtime_error("Adaptive activation requires the complete positively restored original prefix");
        adaptive_final_prefix.consume(this,context_,checkpoint_->payload_bytes(),position_);
        checkpoint_admit_=std::move(admit);speculative_stats_.enabled=true;return;
    }''')


def entry_source(text,scope,prompt_ids,expected_ids):
    text='#include "adaptive_monitor_profile.h"\n#include "causal_wide_engine.h"\n#include "snapshot_replacement_runtime.h"\n#include "wide_batch_probe.h"\n'+text
    marker='        const bool monitor_spec_probe=policy.at("native_speculative_same_width_diagnostic").get<bool>();'
    text=once(text,marker,marker+'''
        if(policy.at("native_causal_adaptive_monitor")!=Json::parse(SCOPE)||!policy.at("native_causal_adaptive_selected").is_boolean())
            throw std::runtime_error("Exact qualified adaptive monitor provenance is required");
        const bool monitor_adaptive=policy.at("native_causal_adaptive_selected").get<bool>();
        qwen_app::adaptive_monitor_selected=monitor_adaptive;
        if(!monitor_adaptive&&monitor_spec_probe)throw std::runtime_error("The counting control retains its closed normal-mode reference");
'''.replace('SCOPE',json.dumps(json.dumps(scope,separators=(',',':')))))
    # The manual adaptive wrapper must not enable the engine's independent
    # width-two controller. Report its actual mixed widths explicitly instead.
    text=once(text,'    if(speculation.controller_enabled) {',
        '    if(speculation.controller_enabled||(qwen_app::adaptive_monitor_selected&&speculation.enabled)) {')
    text=once(text,'report.update({{"schema","ps5-qwen-completed-performance-v6"},',
        'report.update({{"schema",qwen_app::adaptive_monitor_selected?"ps5-qwen-completed-performance-v7":"ps5-qwen-completed-performance-v6"},')
    marker='''            {"ordinary_generated_token_batch_tokens",1},{"target_verification_batch_tokens",2},'''
    text=once(text,marker,marker+'\n            {"target_verification_batch_widths",qwen_app::adaptive_monitor_selected?Json::array({2,4}):Json::array({2})},')
    text=once(text,'{"target_verification_batch_tokens",2}',
        '{qwen_app::adaptive_monitor_selected?"maximum_target_verification_batch_tokens":"target_verification_batch_tokens",qwen_app::adaptive_monitor_selected?4:2}')
    text=once(text,'            const auto admit_complete_checkpoint=', '            qwen_app::snapshot_replacement_budget.bind(context);\n            const auto admit_complete_checkpoint=')
    old='''                const auto rounded=qwen_app::final_prefix_handoff.new_allocation(context,bytes);
                if(qwen_app::final_prefix_handoff.consumed()) {'''
    new='''                const auto before_snapshot=qwen_app::native_model_device_stats();
                const auto rounded=qwen_app::begin_snapshot_replacement(context,buffer_type,bytes,before_snapshot.live,qwen_app::model_postload_device_budget);
                {'''
    text=once(text,old,new)
    text=once(text,'            qwen_app::SpeculativeBatchProbe monitor_same_batch(monitor_columns);',
        '            qwen_app::SpeculativeBatchProbe monitor_same_batch(monitor_columns);\n            std::unique_ptr<qwen_app::WideBatchProbe>monitor_wide_batch;\n            if(monitor_adaptive&&monitor_spec_probe)monitor_wide_batch=std::make_unique<qwen_app::WideBatchProbe>(monitor_columns);\n            std::uint64_t monitor_prefix_payload=0;')
    text=text.replace('monitor_reference_logits(23*monitor_columns)','monitor_reference_logits((monitor_adaptive?13u:23u)*monitor_columns)')
    text=text.replace('std::array<qwen_app::LogitDifference,23> monitor_differences','std::array<qwen_app::LogitDifference,33> monitor_differences')
    text=text.replace('std::array<std::array<unsigned char,32>,23> monitor_hashes[2]','std::array<std::array<unsigned char,32>,33> monitor_hashes[2]')
    marker='            const auto monitor_expected_ids='
    begin=text.index(marker);end=text.index(';',begin)
    text=text[:begin]+text[begin:end].replace('=','=monitor_adaptive?Json::parse('+json.dumps(json.dumps(expected_ids,separators=(',',':')))+').get<std::vector<std::int32_t>>():',1)+text[end:]
    text=once(text,'                    monitor_same_batch.arm(ordinal==2&&monitor_spec_probe);',
        '                    monitor_same_batch.arm(false);if(monitor_wide_batch)monitor_wide_batch->arm(ordinal==2);')
    text=text.replace('monitor_rows>=23','monitor_rows>=33')
    text=once(text,'qwen_app::LlamaEngine&e;llama_context*c;bool enabled;std::function<void(std::uint64_t)>admit;',
        'qwen_app::LlamaEngine&e;llama_context*c;bool enabled,adaptive;std::function<void(std::uint64_t)>admit;std::unique_ptr<qwen_app::CausalWideEngine>wide;')
    text=once(text,'FinalConsumer(qwen_app::LlamaEngine&v,llama_context*x,bool on,std::function<void(std::uint64_t)>a):e(v),c(x),enabled(on),admit(std::move(a)){}',
        'FinalConsumer(qwen_app::LlamaEngine&v,llama_context*x,bool on,bool use_adaptive,std::function<void(std::uint64_t)>a):e(v),c(x),enabled(on),adaptive(use_adaptive),admit(std::move(a)){}')
    marker='''                            const auto p=e.prefix_reuse_stats();'''
    text=once(text,marker,marker+'''
                            if(adaptive){
                                qwen_app::adaptive_final_prefix.arm(&e,c,2,p.request_hit&&p.restores==1&&p.last_reused_prompt_tokens==25);
                                e.enable_speculative_step_prototype(admit);
                                wide=std::make_unique<qwen_app::CausalWideEngine>(e,c,qwen_app::CausalWideMode::adaptive,
                                    Json::parse(IDS).get<std::vector<std::int32_t>>(),8);return;
                            }
'''.replace('IDS',json.dumps(json.dumps(prompt_ids,separators=(',',':')))))
    text=once(text,'qwen_app::Token next()override{return e.next();}', 'qwen_app::Token next()override{return wide?wide->next():e.next();}')
    text=once(text,'void finish()override{e.finish();}', 'void finish()override{if(wide)wide->finish();else e.finish();}')
    text=once(text,'}monitor_consumer(*engine,context,ordinal==2,admit_complete_checkpoint);',
        '}monitor_consumer(*engine,context,ordinal==2,monitor_adaptive,admit_complete_checkpoint);')
    text=text.replace('qwen_app::demo_prompt','qwen_app::adaptive_monitor_prompt()')
    old='''                        qwen_app::final_prefix_handoff.certify(engine.get(),context,engine->checkpoint_validation_stats().maximum_payload_bytes,generated.request_reset_completed);'''
    text=once(text,old,'''                        monitor_prefix_payload=engine->checkpoint_validation_stats().maximum_payload_bytes;
                        if(monitor_adaptive)qwen_app::adaptive_final_prefix.certify(engine.get(),context,monitor_prefix_payload,generated.request_reset_completed);
                        else qwen_app::final_prefix_handoff.certify(engine.get(),context,engine->checkpoint_validation_stats().maximum_payload_bytes,generated.request_reset_completed);''')
    old='''                        if(monitor_spec_stats.attempts!=1||monitor_spec_stats.accepted!=1||monitor_spec_stats.rejected||monitor_spec_stats.queued_bonus_samples!=1||!qwen_app::final_prefix_handoff.consumed())'''
    text=once(text,old,'''                        if(monitor_adaptive?(!monitor_spec_stats.attempts||monitor_spec_stats.attempts>8||!monitor_spec_stats.accepted||monitor_spec_stats.rejected||monitor_spec_stats.queued_bonus_samples<3||!qwen_app::adaptive_final_prefix.consumed()):
                           (monitor_spec_stats.attempts!=1||monitor_spec_stats.accepted!=1||monitor_spec_stats.rejected||monitor_spec_stats.queued_bonus_samples!=1||!qwen_app::final_prefix_handoff.consumed()))''')
    text=once(text,'if(monitor_spec_probe){monitor_probe=monitor_same_batch.report();', 'if(monitor_spec_probe){monitor_probe=monitor_wide_batch->report();')
    text=text.replace('monitor_rows!=23','monitor_rows!=monitor_expected_ids.size()+1')
    text=text.replace('monitor_reference_rows!=23||monitor_compared_rows!=23','monitor_reference_rows!=monitor_expected_ids.size()+1||monitor_compared_rows!=monitor_expected_ids.size()+1')
    text=text.replace('prefix_second.last_reused_prompt_tokens!=30','prefix_second.last_reused_prompt_tokens!=(monitor_adaptive?25u:30u)')
    text=once(text,'                    qwen_app::require_demo_sequence(generated.output_bytes);',
        '                    if(!monitor_adaptive)qwen_app::require_demo_sequence(generated.output_bytes);')
    text=once(text,'for(const auto &hash:monitor_hashes[request_index]){',
        'for(std::size_t row=0;row<monitor_reference_rows;++row){const auto&hash=monitor_hashes[request_index][row];')
    text=once(text,'            for(const auto &d:monitor_differences)monitor_distribution.push_back(qwen_app::logit_difference_report(d));',
        '            for(std::size_t row=0;row<monitor_compared_rows;++row)monitor_distribution.push_back(qwen_app::logit_difference_report(monitor_differences[row]));')
    text=once(text,'{"second_request_reused_prompt_tokens",30}', '{"second_request_reused_prompt_tokens",monitor_adaptive?25:30}')
    text=once(text,'{"schema_extension","ps5-qwen-prefix-speculative-monitor-v1"}',
        '{"schema_extension",monitor_adaptive?"ps5-qwen-adaptive-prefix-monitor-v1":"ps5-qwen-prefix-speculative-monitor-v1"},{"adaptive_profile_selected",monitor_adaptive},{"snapshot_replacements",qwen_app::snapshot_replacement_budget.replacements()},{"snapshot_F32_sections",qwen_app::snapshot_witness_sections}')
    old='''{"snapshot_replacement",{{"old_logical_bytes",qwen_app::FinalPrefixHandoff::prefix_bytes},{"new_logical_bytes",qwen_app::FinalPrefixHandoff::speculative_bytes},
                    {"equal_rounded_capacity_bytes",qwen_app::FinalPrefixHandoff::rounded(qwen_app::FinalPrefixHandoff::prefix_bytes)},{"old_buffer_freed_before_new_allocation",true},{"new_Direct_metadata_allowance_pages",19}}}'''
    new='''{"snapshot_replacement",monitor_adaptive?Json{{"old_logical_bytes",monitor_prefix_payload},{"new_logical_bytes",qwen_app::snapshot_replacement_budget.payload()},
                    {"each_actual_layout_witnessed",true},{"old_buffer_freed_before_new_allocation",true},{"new_Direct_metadata_allowance_pages",19}}:
                    Json{{"old_logical_bytes",qwen_app::FinalPrefixHandoff::prefix_bytes},{"new_logical_bytes",qwen_app::FinalPrefixHandoff::speculative_bytes},
                    {"equal_rounded_capacity_bytes",qwen_app::FinalPrefixHandoff::rounded(qwen_app::FinalPrefixHandoff::prefix_bytes)},{"old_buffer_freed_before_new_allocation",true},{"new_Direct_metadata_allowance_pages",19}}}'''
    text=once(text,old,new)
    return text
