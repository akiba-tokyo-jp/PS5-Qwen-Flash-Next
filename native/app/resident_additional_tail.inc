// SPDX-License-Identifier: MIT
// Dedicated finite comparisons after the original model/context admission.
        const bool prefix_comparison=RESIDENT_PREFIX_COMPARISON;
        const auto *chat_template=llama_model_chat_template(model,nullptr);
        if(!chat_template||!*chat_template)throw std::runtime_error("Original chat template required");
        qwen_native_driver_complete();resident_sample("original_model_context_completed");
        write_fresh_report(startup.admission_report+".resident.startup-memory",resident_startup_report());
        const auto run=policy.at("native_first_generation_validation").at("run_id").get<std::string>();
        const auto columns=static_cast<std::size_t>(llama_vocab_n_tokens(llama_model_get_vocab(model)));
        if(!columns||columns>262144)throw std::runtime_error("Bounded original vocabulary required");
        std::vector<float> reference_logits(33*columns);
        std::vector<std::int32_t> reference_ids;std::vector<unsigned char> reference_bytes;
        std::size_t reference_rows=0;
        std::array<CompletedRouteEvidence,9> routes;
        Json completed=Json::array();
        const auto admit_checkpoint=[&](std::uint64_t bytes){
            require_model_CPU_budget();require_unchanged_model();
            if(bytes<118038528||bytes>142606336)throw std::runtime_error("Complete checkpoint payload outside qualification");
            const auto rounded=(bytes+(2u<<20)-1)&~std::uint64_t((2u<<20)-1);
            const auto ledger=qwen_app::native_model_device_stats();const auto budget=qwen_native_allocator_budget(driver_total);
            if(ledger.live>qwen_app::model_postload_device_budget||rounded>qwen_app::model_postload_device_budget-ledger.live||
               budget.available<rounded+memory_budget.direct_reserve||observed_system_headroom()<memory_budget.flexible_reserve)
                throw std::runtime_error("Complete checkpoint cannot retain original reserves");
        };
        const unsigned request_count=prefix_comparison?9:3;
        for(unsigned ordinal=0;ordinal<request_count;++ordinal) {
            const bool second=prefix_comparison&&ordinal>0&&ordinal%2==0;
            const unsigned group=ordinal?((ordinal-1)/2):0;
            const bool reuse=prefix_comparison&&ordinal>0&&(group==1||group==2);
            const char *arm=ordinal==0?"warmup":(reuse?"prefix":"ordinary");
            require_model_CPU_budget();require_unchanged_model();qwen_app_complete_predictive_expert();
            const auto previous_cache=engine->expert_cache_metrics();
            if(!previous_cache)throw std::runtime_error("Actual process-global expert counters required");
            if(!second) {
                qwen_native_driver_begin();engine.reset();llama_free(context);context=nullptr;qwen_native_driver_complete();
                qwen_app_configure_predictive_cache(false);
                const auto started=qwen_app::ProfileClock::now();qwen_native_driver_begin();
                context=llama_init_from_model(model,qwen_app::streaming_context_params(256,cache_bytes,4));
                if(!context||qwen_app::profile_elapsed_ns(started)>600000000000ull)
                    throw std::runtime_error("Bounded additional context recreation failed");
                engine=std::make_unique<qwen_app::LlamaEngine>(model,context,4);
                engine->set_stage_observer(observed_inference_stage);
                engine->set_gpu_boundaries(qwen_native_driver_begin,qwen_native_driver_complete,
                    qwen_native_driver_retain,qwen_native_driver_checkpoint);
                qwen_native_driver_complete();require_model_CPU_budget();
                if(reuse)engine->enable_prefix_reuse(admit_checkpoint);
            }
            std::size_t rows=0;double max_error=0;bool geometry_error=false,value_error=false;
            engine->set_logits_observer([&](const float *v,std::size_t count) noexcept {
                if(!v||count!=columns||rows>=33){geometry_error=true;return;}
                if(ordinal==0){std::copy(v,v+count,reference_logits.data()+rows*columns);++reference_rows;}
                else {
                    if(rows>=reference_rows){geometry_error=true;return;}
                    for(std::size_t i=0;i<count;++i){const double a=v[i],b=reference_logits[rows*columns+i],e=std::abs(a-b);
                        if(!std::isfinite(a)||!std::isfinite(b)||e>1e-5+1e-5*std::abs(b))value_error=true;
                        max_error=std::max(max_error,e);}
                }
                ++rows;
            });
            qwen_app::FirstGeneration trial(*engine);
            engine->set_work_guard([&]{trial.require_time();require_model_CPU_budget();},64);
            const auto perf=performance_snapshot(*engine);const auto cache=engine->expert_cache_metrics();
            const auto predicted=predictive_cache_bytes();
            if(!cache)throw std::runtime_error("Actual initial expert counters required");
            if(!second)qwen_app::require_resident_context_counter_baseline(*previous_cache,*cache);
            qwen_app::begin_completed_expert_routes();
            const auto report_prefix=startup.admission_report+".arm"+std::to_string(ordinal);
            const qwen_app::Request request{run+"-"+std::to_string(ordinal),
                qwen_app::render_bounded_user_prompt(chat_template,qwen_app::demo_prompt),256,32};
            const auto &result=trial.run(request,[&](const auto &bound){
                write_fresh_report(report_prefix+".intent",{{"id",bound.id},{"arm",arm},{"pid",getpid()},
                    {"run_id",run},{"group",ordinal?Json(group):Json(nullptr)},
                    {"second_request_in_group",second},{"cache_initially_empty",!second},{"maximum_output_tokens",32}});
            },[&](const auto &token,const auto &m){
                write_fresh_report(report_prefix+".token-"+std::to_string(m.generated_tokens),{{"token_id",token.id},
                    {"piece_bytes",std::vector<unsigned char>(token.piece.begin(),token.piece.end())},
                    {"generated_tokens",m.generated_tokens},{"elapsed_ms",m.total_ms}});
            },observed_inference_stage);
            engine->set_work_guard({});engine->set_logits_observer({});qwen_app_complete_predictive_expert();
            if(!result.request_reset_completed||geometry_error||value_error||rows!=23||
               (ordinal&&rows!=reference_rows))throw std::runtime_error("Additional full F32 continuation validation failed");
            qwen_app::require_demo_sequence(result.output_bytes);
            if(!ordinal){reference_ids=result.token_ids;reference_bytes=result.output_bytes;}
            else if(result.token_ids!=reference_ids||result.output_bytes!=reference_bytes)
                throw std::runtime_error("Original additional tokens or bytes differ");
            routes[ordinal]=completed_route_evidence(*engine,perf.at("process_calls").get<std::uint64_t>(),*cache,predicted);
            if(!routes[ordinal].complete)throw std::runtime_error("Complete actual additional routes required");
            const auto p=engine->prefix_reuse_stats();
            if(p.enabled!=reuse||p.request_hit!=(reuse&&second)||p.captures!=(reuse?1u:0u)||
               p.restores!=(reuse&&second?1u:0u)||p.last_reused_prompt_tokens!=(reuse&&second?30u:0u))
                throw std::runtime_error("Actual prefix capture and restore counters differ");
            if(second) {
                const auto &first=routes[ordinal-1],&current=routes[ordinal];const unsigned offset=reuse?8*48:0;
                if(first.rows.size()!=offset+current.rows.size())throw std::runtime_error("Additional route geometry differs");
                for(std::size_t i=0;i<current.rows.size();++i){const auto &a=first.rows[i+offset],&b=current.rows[i];
                    if(a.layer!=b.layer||a.tokens!=b.tokens||!std::equal(a.ids.begin(),a.ids.begin()+10*a.tokens,b.ids.begin()))
                        throw std::runtime_error("Additional continuation expert selections differ");}
            }
            require_model_CPU_budget();require_unchanged_model();
            Json row={{"ordinal",ordinal},{"arm",arm},{"group",ordinal?Json(group):Json(nullptr)},
                {"second_request_in_group",second},{"pid",getpid()},{"run_id",run},
                {"active_cache_slots",cache_geometry.active_slots},{"cache_initially_empty",!second},
                {"token_ids",result.token_ids},{"output_bytes",result.output_bytes},{"stop_reason",result.stop_reason},
                {"request_reset_completed",true},{"metrics",{{"prompt_tokens",result.metrics.prompt_tokens},
                    {"generated_tokens",result.metrics.generated_tokens},{"prefill_ms",result.metrics.prefill_ms},
                    {"TTFT_ms",result.metrics.ttft_ms?Json(*result.metrics.ttft_ms):Json(nullptr)},
                    {"decode_ms",result.metrics.decode_ms},{"total_ms",result.metrics.total_ms},
                    {"decode_tokens_per_second",result.metrics.decode_tokens_per_second?Json(*result.metrics.decode_tokens_per_second):Json(nullptr)}}},
                {"completed_performance",performance_difference(perf,*engine)},
                {"full_F32_logit_rows_compared",ordinal?rows:0},{"maximum_absolute_logit_error",max_error},
                {"prefix",{{"enabled",p.enabled},{"request_hit",p.request_hit},{"captures",p.captures},
                    {"restores",p.restores},{"last_reused_prompt_tokens",p.last_reused_prompt_tokens},
                    {"capture_ns",p.capture_ns},{"restore_ns",p.restore_ns}}}};
            completed.push_back(row);write_fresh_report(report_prefix+".result",row);
            qwen_native_stage("resident_additional_arm_completed_positive_request_reset");
        }
        qwen_app_complete_predictive_expert();qwen_native_driver_begin();
        engine.reset();llama_free(context);context=nullptr;llama_model_free(model);model=nullptr;qwen_native_driver_complete();
        const auto source=qwen_app::native_model_source_stats();
        if(source.chunks!=source.completed_windows)throw std::runtime_error("Original source windows remain incomplete");
        qwen_app::stop_native_model_sources();const auto ledger=qwen_app::native_model_device_stats();
        if(ledger.live)throw std::runtime_error("Additional model owners remain live");
        for(unsigned i=0;i<request_count;++i){auto report=completed_route_report(routes[i]);
            report.update({{"pid",getpid()},{"run_id",run},{"ordinal",i},{"cache_reset_before_request",!prefix_comparison||!i||i%2!=0},
                {"sidecar_written_after_model_and_source_retirement",true},{"JSON_created_after_model_and_source_retirement",true}});
            write_fresh_report(startup.admission_report+".arm"+std::to_string(i)+".routes",report);}
        struct ps5_heap_stats heap{};ps5_heap_stats(&heap);
        write_fresh_report(startup.admission_report,{{"schema","ps5-qwen-resident-additional-result-v1"},
            {"kind",prefix_comparison?"prefix":"cache"},{"pid",getpid()},{"run_id",run},{"completed",true},
            {"requests",completed},{"model_loads",1},{"active_cache_slots",cache_geometry.active_slots},
            {"candidate_SELF_sha256",policy.at("native_first_generation_validation").at("candidate_SELF_sha256")},
            {"model_receipt_sha256",policy.at("native_first_generation_validation").at("model_receipt_sha256")},
            {"all_original_tokens_and_bytes_exact",true},{"full_F32_continuation_and_routes_passed",true},
            {"all_model_source_device_owners_positively_retired",true},{"device_ledger_live_bytes",0},
            {"CPU_heap_peak_bytes",heap.peak_bytes},{"device_ledger_peak_bytes",ledger.peak},
            {"source_windows",source.chunks},{"source_completed_windows",source.completed_windows},
            {"HTTP_requests",0},{"VideoOut_starts",0},{"speedup_qualified",false},{"production_adopted",false}});
        qwen_native_stage("resident_additional_completed_waiting_for_ordinary_close");
        for(;;)(void)usleep(1000000);
    }catch(const std::exception &e){
        try {if(!validation_report.empty())write_fresh_report(validation_report+".resident.startup-memory",resident_startup_report());}catch(...){}
        qwen_native_stage("resident_additional_exception_work_stopped");
        if(native_resources_started){qwen_native_driver_retain();engine.release();}
        if(!validation_report.empty())try{write_fresh_report(validation_report+".failure",{{"message",e.what()},
            {"model_loaded",model!=nullptr},{"native_resources_started",native_resources_started},
            {"CPU_worker_completion_unknown",resident_worker_completion_unknown},
            {"memory_backpressure",memory_backpressure_report()}});}catch(...){}
        for(;;)(void)usleep(1000000);
    }
}
