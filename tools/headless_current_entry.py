#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Remove presentation/HTTP work while preserving current model/state/retirement guards."""
import json
from build_speculative_batch_probe import once


def headless_entry(text,kind,requests,report_expression,retain_reference=True):
    if requests not in (1,3):raise ValueError('One or three explicit finite requests required')
    if not retain_reference:
        if requests!=1:raise ValueError('Cross-request reference may be removed only from a one-request scope')
        text=once(text,'        std::vector<float> reference_logits(resident_reference_rows*columns);',
            '        // One request scans existing full rows without retaining an unused cross-request copy.')
        start=text.index('            engine->set_logits_observer([&](const float*v,std::size_t count)noexcept{')
        end=text.index('            qwen_app::CausalExpertSharingEngine causal',start)
        text=text[:start]+'''            engine->set_logits_observer([&](const float*v,std::size_t count)noexcept{
                qwen_load::CpuSpan measured(qwen_load::full_validation);
                if(!v||count!=columns||rows>=resident_reference_rows){geometry_error=true;return;}
                for(std::size_t i=0;i<count;++i)if(!std::isfinite(v[i]))value_error=true;
                ++rows;if(!ordinal)++reference_rows;
            });
'''+text[end:]
        if 'reference_logits' in text:raise ValueError('An unhandled cross-request reference consumer remains')
    text=once(text,'        const unsigned request_count=3;','        const unsigned request_count='+str(requests)+';')
    start=text.index('                if(ordinal){\n                    Json event')
    end=text.index('            },observed_inference_stage);',start)
    text=text[:start]+text[end:]
    start=text.index('            if(ordinal){\n                if(!result.metrics.decode_tokens_per_second')
    end=text.index('            return row;',start);text=text[:start]+text[end:]
    start=text.index('        qwen_app::HardwareInfo hardware;',text.index('        run_all_Q2_request(0,'))
    cleanup=text.index('        qwen_app_complete_predictive_expert();qwen_native_driver_begin();',start)
    remaining=''
    if requests==3:remaining='        for(unsigned ordinal=1;ordinal<3;++ordinal)run_all_Q2_request(ordinal,[]{return true;},[](const Json&){});\n'
    text=text[:start]+remaining+text[cleanup:]
    start=text.index('        write_fresh_report(startup.admission_report,{{"scheduler_slot_map_counts"',start)
    end=text.index('        qwen_native_stage("resident_additional_completed_waiting_for_ordinary_close");',start)
    terminal='''        auto audit=AUDIT_EXPRESSION;
        audit.update({{"pid",getpid()},{"run_id",run},{"candidate_SELF_sha256",policy.at("native_first_generation_validation").at("candidate_SELF_sha256")}});
        write_fresh_report(startup.admission_report+".audit",audit);
        write_fresh_report(startup.admission_report,{{"schema","ps5-qwen-headless-model-audit-completion-v1"},
            {"kind",KIND_LITERAL},{"completed",true},{"pid",getpid()},{"run_id",run},
            {"candidate_SELF_sha256",policy.at("native_first_generation_validation").at("candidate_SELF_sha256")},
            {"model_receipt_sha256",policy.at("native_first_generation_validation").at("model_receipt_sha256")},
            {"requests",completed},{"model_loads",1},{"HTTP_requests",0},{"VideoOut_starts",0},
            {"source_windows",source.chunks},{"source_completed_windows",source.completed_windows},
            {"all_model_source_device_owners_positively_retired",true},{"device_ledger_live_bytes",ledger.live},
            {"device_ledger_peak_bytes",ledger.peak},{"CPU_heap_peak_bytes",heap.peak_bytes},
            {"timings_usable_for_performance",false},{"audit",audit}});
'''.replace('AUDIT_EXPRESSION',report_expression).replace('KIND_LITERAL',json.dumps(kind))
    return text[:start]+terminal+text[end:]
