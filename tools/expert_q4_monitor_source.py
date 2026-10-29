#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Add the original passive monitor and bounded API to the qualified Q4 entry."""
import json
from expert_q4_model_source import SCOPE,entry_source
from build_speculative_batch_probe import once

MONITOR_SCOPE=dict(SCOPE,schema='ps5-qwen-expert-q4-monitor-comparison-v1',HTTP_requests=2,VideoOut_starts=1)

def monitor_entry_source(text):
    text=entry_source(text)
    text=once(text,json.dumps(json.dumps(SCOPE,separators=(',',':'))),json.dumps(json.dumps(MONITOR_SCOPE,separators=(',',':'))))
    text=once(text,'        const bool direct_frame_candidate=false;',
        '        const bool direct_frame_candidate=true;')
    begin=text.index('        const unsigned request_count=3;\n        for(unsigned ordinal=0;ordinal<request_count;++ordinal) {')
    end=text.index('        qwen_app_complete_predictive_expert();qwen_native_driver_begin();',begin)
    loop=text[begin:end]
    loop=once(loop,'        const unsigned request_count=3;\n        for(unsigned ordinal=0;ordinal<request_count;++ordinal) {',
        '''        const auto external_metrics=[](const qwen_app::Metrics&v){
            Json m{{"prompt_tokens",v.prompt_tokens},{"generated_tokens",v.generated_tokens},
                {"prefill_ms",v.prefill_ms},{"decode_ms",v.decode_ms},{"total_ms",v.total_ms},
                {"ttft_ms",v.ttft_ms?Json(*v.ttft_ms):Json(nullptr)},
                {"decode_tokens_per_second",v.decode_tokens_per_second?Json(*v.decode_tokens_per_second):Json(nullptr)}};
            return m;
        };
        const unsigned request_count=3;
'''
        '        const auto run_Q4_request=[&](unsigned ordinal,const std::function<bool()>&alive,\n'
        '            const std::function<void(const Json&)>&publish)->Json {')
    loop=once(loop,'engine->set_work_guard([&]{trial.require_time();require_model_CPU_budget();},64);',
        'engine->set_work_guard([&]{trial.require_time();require_model_CPU_budget();\n'
        '                if(ordinal&&!alive())throw std::runtime_error("Q4 API observer disconnected; no retry");},64);')
    loop=once(loop,'                    {"generated_tokens",m.generated_tokens},{"elapsed_ms",m.total_ms}});',
        '                    {"generated_tokens",m.generated_tokens},{"elapsed_ms",m.total_ms}});\n'
        '''                if(ordinal){
                    Json event{{"id",request.id},{"type","token"},{"state","generating"},{"error",0},
                        {"ordinal",m.generated_tokens},{"token_id",token.id},
                        {"piece_bytes",std::vector<unsigned char>(token.piece.begin(),token.piece.end())},
                        {"elapsed_ms",m.total_ms},{"metrics",external_metrics(m)}};
                    const auto counter=engine->expert_cache_metrics();
                    if(counter)event["expert_cache"]={{"hits",counter->hits},{"misses",counter->misses},
                        {"uploaded_bytes",counter->uploaded_bytes},{"prefetch_advice_bytes",counter->prefetch_advice_bytes}};
                    publish(event);
                }''')
    # A known bad answer is a completed experiment, but cannot pass normal-app adoption.
    loop=once(loop,'            completed.push_back(row);write_fresh_report(report_prefix+".result",row);',
        '            completed.push_back(row);write_fresh_report(report_prefix+".result",row);\n'
        '            if(!counting_quality)throw std::runtime_error("Completed Q4 counting response failed normal-app quality");')
    marker='            resident_reuse_sample("after_completed_request");qwen_native_stage("resident_additional_arm_completed_positive_request_reset");\n        }\n'
    loop=once(loop,marker,'''            resident_reuse_sample("after_completed_request");qwen_native_stage("resident_additional_arm_completed_positive_request_reset");
            if(ordinal){
                if(!result.metrics.decode_tokens_per_second||!result.metrics.ttft_ms||display->failed())
                    throw std::runtime_error("Measurable Q4 request and healthy passive presentation required");
                publish({{"id",request.id},{"type","completion_pending"},{"state","finalizing frame evidence"},
                    {"error",0},{"metrics",external_metrics(result.metrics)}});
                const auto frame=display->capture(report_prefix+".display.bmp",request.id,result.token_ids.size());
                write_fresh_report(report_prefix+".display.json",{{"schema","ps5-qwen-Q4-displayed-frame-v1"},
                    {"pid",getpid()},{"run_id",run},{"id",frame.request_id},{"width",1920},{"height",1080},
                    {"BMP_bytes",8294454},{"generated_tokens",frame.generated_tokens},{"epoch_ms",frame.epoch_ms},
                    {"clock_calibrated",frame.clock_calibrated},{"model_loaded",frame.model_loaded},
                    {"decode_tokens_per_second",frame.tokens_per_second?Json(*frame.tokens_per_second):Json(nullptr)},
                    {"positive_VideoOut_completion",true}});
                publish({{"id",request.id},{"type","finished"},{"state","completed"},{"error",0},
                    {"metrics",external_metrics(result.metrics)},{"stop_reason",result.stop_reason}});
            }
            return row;
        };
        run_Q4_request(0,[]{return true;},[](const Json&){});
        qwen_app::HardwareInfo hardware;
        hardware.cpu_name=screen.cpu_name;hardware.logical_cpu_threads=screen.cpu_threads;
        hardware.sample_process_cpu=false;
        if(device){const char*description=ggml_backend_dev_description(device);if(description)hardware.gpu_name=description;}
        hardware.gpu_total_bytes=driver_total;
        hardware.gpu_free_bytes=qwen_native_allocator_budget(driver_total).available;
        std::int64_t display_physical=0;std::size_t display_available=0;
        const auto display_pool=sceKernelGetDirectMemorySize();
        if(display_pool<=0||sceKernelAvailableDirectMemorySize(0,display_pool,65536,&display_physical,&display_available)<0||
            display_available<memory_budget.direct_reserve+(32u<<20))
            throw std::runtime_error("Fresh model-resident display headroom is insufficient");
        screen.state="Expert Q4_0 model ready";screen.model_loaded=true;screen.gpu_name=hardware.gpu_name;
        screen.gpu_total_bytes=hardware.gpu_total_bytes;screen.gpu_free_bytes=hardware.gpu_free_bytes;
        screen.message="EXPERT Q4_0 / OTHER BF16 F32 / PASSIVE MONITOR";
        display=std::make_unique<qwen_app::NativeDisplay>(direct_frame_candidate);display->start(screen);
        qwen_native_stage("Q4_model_resident_passive_frame_completed");
        const auto demo=qwen_app::serve_bounded_demo(run,startup.web_assets,"0.0.0.0",startup.port,hardware,
            [&](unsigned ordinal,const std::function<bool()>&alive,const std::function<void(const Json&)>&publish){
                return run_Q4_request(ordinal,alive,publish);
            },[&](const qwen_app::MonitorSnapshot&snapshot){
                if(display->failed())throw std::runtime_error("Q4 passive native presentation failed");
                auto shown=snapshot;shown.message="EXPERT Q4_0 / OTHER BF16 F32 / PASSIVE MONITOR";display->publish(shown);
            },[&](const Json&ready){write_fresh_report(startup.admission_report+".demo.ready",ready);});
        if(demo.at("external_requests_accepted")!=2||demo.at("external_requests_completed")!=2||
            demo.at("listener_stopped")!=true||demo.at("finish_acknowledgement_delivered")!=true||
            demo.at("all_monitor_assets_requested")!=true||display->failed())
            throw std::runtime_error("Both Q4 API requests, passive assets, finish and listener retirement required");
''')
    text=text[:begin]+loop+text[end:]
    text=once(text,'{"HTTP_requests",0},{"VideoOut_starts",0}',
        '{"HTTP_requests",2},{"VideoOut_starts",1},{"passive_monitor_and_API_completed",true},{"demo",demo}')
    return text
