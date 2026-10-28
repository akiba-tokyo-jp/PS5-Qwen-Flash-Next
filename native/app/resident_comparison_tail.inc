// SPDX-License-Identifier: MIT
// Included after the frozen original model/context admission and engine setup.
        const auto *chat_template=llama_model_chat_template(model,nullptr);
        if(!chat_template||!*chat_template)throw std::runtime_error("Original chat template required");
        qwen_native_driver_complete();
        resident_sample("original_model_context_completed");
        write_fresh_report(startup.admission_report+".resident.startup-memory",resident_startup_report());
        const auto run=policy.at("native_first_generation_validation").at("run_id").get<std::string>();
        std::array<CompletedRouteEvidence,10> routes;
        Json completed=Json::array();
        std::vector<std::int32_t> reference_ids;
        std::vector<unsigned char> reference_bytes;
        const auto logit_columns=static_cast<std::size_t>(llama_vocab_n_tokens(llama_model_get_vocab(model)));
        if(!logit_columns||logit_columns>262144)throw std::runtime_error("Bounded original vocabulary required");
        // Reserve outside all active GPU epochs. Validation callbacks neither
        // allocate nor throw: report differences after positive request reset.
        std::vector<float> reference_logits(33*logit_columns);
        std::size_t reference_rows=0;
        bool forced_rejection_passed=false;
        const auto admit_checkpoint=[&](std::uint64_t bytes){
            require_model_CPU_budget();require_unchanged_model();
            if(bytes<118038528||bytes>142606336)throw std::runtime_error("Complete checkpoint payload outside qualification");
            const auto rounded=(bytes+(2u<<20)-1)&~std::uint64_t((2u<<20)-1);
            const auto ledger=qwen_app::native_model_device_stats();
            const auto budget=qwen_native_allocator_budget(driver_total);
            if(ledger.live>qwen_app::model_postload_device_budget||rounded>qwen_app::model_postload_device_budget-ledger.live||
               budget.available<rounded+memory_budget.direct_reserve||observed_system_headroom()<memory_budget.flexible_reserve)
                throw std::runtime_error("Complete checkpoint cannot retain original reserves");
        };
        // Each measured arm gets its own empty expert cache and identical
        // context. File/pipeline warming precedes all eight matched arms.
        const std::array<const char *,10> arms{{"warmup","ordinary","predictive","predictive","ordinary",
            "ordinary","speculative","speculative","ordinary","forced-rejection"}};
        for(unsigned ordinal=0;ordinal<arms.size();++ordinal) {
            require_model_CPU_budget();require_unchanged_model();
            qwen_app_complete_predictive_expert();
            const auto previous_cache=engine->expert_cache_metrics();
            if(!previous_cache)throw std::runtime_error("Actual process-global expert counters required");
            qwen_native_driver_begin();engine.reset();llama_free(context);context=nullptr;
            qwen_native_driver_complete();
            qwen_app_configure_predictive_cache(std::string(arms[ordinal])=="predictive");
            const auto context_begin=qwen_app::ProfileClock::now();
            qwen_native_driver_begin();
            context=llama_init_from_model(model,qwen_app::streaming_context_params(256,cache_bytes,4));
            if(!context||qwen_app::profile_elapsed_ns(context_begin)>600000000000ull)
                throw std::runtime_error("Bounded resident context recreation failed");
            engine=std::make_unique<qwen_app::LlamaEngine>(model,context,4);
            engine->set_stage_observer(observed_inference_stage);
            engine->set_gpu_boundaries(qwen_native_driver_begin,qwen_native_driver_complete,
                qwen_native_driver_retain,qwen_native_driver_checkpoint);
            qwen_native_driver_complete();require_model_CPU_budget();
            if(std::string(arms[ordinal])=="speculative") {
                struct Cost {qwen_app::OnlineExpertVerification planner;std::uint64_t source=0;};
                auto state=std::make_shared<Cost>();qwen_app::ExpertVerificationHooks hooks;
                hooks.before_process=[state]{state->source=qwen_app::native_model_source_stats().read_ns;};
                hooks.completed_ordinary=[state](int token,std::uint64_t ns){
                    const auto after=qwen_app::native_model_source_stats().read_ns;
                    if(after<state->source||!ns)throw std::runtime_error("Incomplete online source timing");
                    state->planner.observe(token,qwen_app::last_completed_single_token_routes(),double(ns)/1e9,
                        double(std::min(after-state->source,ns))/1e9);
                };
                hooks.choose=[state](int pending,int draft){return state->planner.choose(pending,draft);};
                hooks.verified=[state](bool accepted,double capture,double restore){state->planner.verified(accepted,capture,restore);};
                engine->enable_expert_aware_speculation(admit_checkpoint,std::move(hooks));
            }
            const bool rejection=ordinal==9;
            if(rejection)engine->enable_speculative_step_prototype(admit_checkpoint);
            std::size_t logits_seen=0;double max_error=0;bool logit_geometry_error=false,logit_value_error=false;
            // The forced rejected branch must restore the same full F32
            // continuation logits, not merely the same selected token.
            if(ordinal==0||rejection)engine->set_logits_observer([&](const float *v,std::size_t count) noexcept {
                if(!v||count!=logit_columns||logits_seen>=33){logit_geometry_error=true;return;}
                if(ordinal==0) {
                    std::copy(v,v+count,reference_logits.data()+logits_seen*logit_columns);
                    ++reference_rows;
                }
                else {
                    if(logits_seen>=reference_rows){logit_geometry_error=true;return;}
                    for(std::size_t i=0;i<count;++i){const double a=v[i],b=reference_logits[logits_seen*logit_columns+i],e=std::abs(a-b);
                        if(!std::isfinite(a)||!std::isfinite(b)||e>1e-5+1e-5*std::abs(b))
                            logit_value_error=true;
                        max_error=std::max(max_error,e);
                    }
                }
                ++logits_seen;
            });
            class RejectionControl final:public qwen_app::Engine {
                qwen_app::LlamaEngine &e;bool reject;unsigned calls=0;
            public:RejectionControl(qwen_app::LlamaEngine &v,bool r):e(v),reject(r){}
                std::uint32_t tokenize(const std::string&s)override{return e.tokenize(s);}
                void prefill(std::uint32_t n)override{e.prefill(n);}
                qwen_app::Token next()override{return reject&&calls++==1?e.next_with_one_draft(0):e.next();}
                void finish()override{e.finish();}
                std::optional<qwen_app::ExpertCacheMetrics> expert_cache_metrics()const override{return e.expert_cache_metrics();}
            } adapter(*engine,rejection);
            qwen_app::FirstGeneration trial(adapter);
            engine->set_work_guard([&]{trial.require_time();require_model_CPU_budget();},64);
            const auto perf=performance_snapshot(*engine);const auto cache=engine->expert_cache_metrics();
            const auto predicted=predictive_cache_bytes();
            if(!cache)throw std::runtime_error("Actual initial expert counters required");
            qwen_app::require_resident_context_counter_baseline(*previous_cache,*cache);
            qwen_app::begin_completed_expert_routes();
            const auto prefix=startup.admission_report+".arm"+std::to_string(ordinal);
            const qwen_app::Request request{run+"-"+std::to_string(ordinal),
                qwen_app::render_bounded_user_prompt(chat_template,qwen_app::demo_prompt),256,32};
            const auto &result=trial.run(request,[&](const auto &bound){
                write_fresh_report(prefix+".intent",{{"id",bound.id},{"arm",arms[ordinal]},{"pid",getpid()},
                    {"run_id",run},{"cache_initially_empty",true},{"maximum_output_tokens",32}});
            },[&](const auto &token,const auto &m){
                write_fresh_report(prefix+".token-"+std::to_string(m.generated_tokens),{{"token_id",token.id},
                    {"piece_bytes",std::vector<unsigned char>(token.piece.begin(),token.piece.end())},
                    {"generated_tokens",m.generated_tokens},{"elapsed_ms",m.total_ms}});
            },observed_inference_stage);
            engine->set_work_guard({});qwen_app_complete_predictive_expert();
            engine->set_logits_observer({});
            if(!result.request_reset_completed||logit_geometry_error||logit_value_error)
                throw std::runtime_error("Completed request full F32 logit validation failed");
            require_model_CPU_budget();require_unchanged_model();
            qwen_app::require_demo_sequence(result.output_bytes);
            if(ordinal==0){reference_ids=result.token_ids;reference_bytes=result.output_bytes;
                if(reference_ids.size()<3||reference_ids[1]==0)throw std::runtime_error("Controlled rejection requires a distinct fixed draft");}
            else if(result.token_ids!=reference_ids||result.output_bytes!=reference_bytes)
                throw std::runtime_error("Original control tokens or bytes differ");
            routes[ordinal]=completed_route_evidence(*engine,perf.at("process_calls").get<std::uint64_t>(),*cache,predicted);
            const auto s=engine->speculative_step_stats();qwen_predictive_cache_stats p{};qwen_app_predictive_cache_counters(&p);
            if(p.loads!=p.useful+p.unused||p.proposals!=p.loads+p.ineligible||p.logical_bytes!=p.loads*9830400ull)
                throw std::runtime_error("Every predicted delivery must be counted");
            if(rejection){
                if(s.attempts!=1||s.rejected!=1||s.accepted||logits_seen!=reference_rows)
                    throw std::runtime_error("The controlled rejected branch was not fully restored");
                forced_rejection_passed=true;
            }
            Json row={{"ordinal",ordinal},{"arm",arms[ordinal]},{"pid",getpid()},{"run_id",run},
                {"initial_expert_cache_counters",{{"hits",cache->hits},{"misses",cache->misses},
                    {"uploaded_bytes",cache->uploaded_bytes},{"prefetch_advice_bytes",cache->prefetch_advice_bytes}}},
                {"token_ids",result.token_ids},{"output_bytes",result.output_bytes},{"stop_reason",result.stop_reason},
                {"request_reset_completed",result.request_reset_completed},{"prompt_tokens",result.metrics.prompt_tokens},
                {"prefill_ms",result.metrics.prefill_ms},{"total_ms",result.metrics.total_ms},
                {"decode_tokens_per_second",result.metrics.decode_tokens_per_second?Json(*result.metrics.decode_tokens_per_second):Json(nullptr)},
                {"completed_performance",performance_difference(perf,*engine)},
                {"predictive",{{"loads",p.loads},{"proposals",p.proposals},{"useful",p.useful},{"unused",p.unused},
                    {"logical_bytes",p.logical_bytes},{"ineligible",p.ineligible}}},
                {"speculation",{{"attempts",s.attempts},{"accepted",s.accepted},{"rejected",s.rejected},
                    {"cost_checks",s.cost_checks},{"cost_ordinary",s.cost_ordinary},{"cost_width_two",s.cost_width_two}}},
                {"full_F32_logit_rows_compared",rejection?logits_seen:0},{"maximum_absolute_logit_error",max_error}};
            completed.push_back(row);write_fresh_report(prefix+".result",row);
            qwen_native_stage("resident_comparison_arm_completed_positive_request_reset");
        }
        qwen_app_complete_predictive_expert();qwen_native_driver_begin();
        engine.reset();llama_free(context);context=nullptr;llama_model_free(model);model=nullptr;
        qwen_native_driver_complete();
        const auto source_stats=qwen_app::native_model_source_stats();
        if(source_stats.chunks!=source_stats.completed_windows)
            throw std::runtime_error("Some original source windows did not positively complete");
        qwen_app::stop_native_model_sources();
        const auto ledger=qwen_app::native_model_device_stats();
        if(ledger.live||!forced_rejection_passed)throw std::runtime_error("Resident cohort retirement or rejection proof incomplete");
        for(unsigned i=0;i<routes.size();++i){
            auto r=completed_route_report(routes[i]);
            r.update({{"pid",getpid()},{"run_id",run},{"ordinal",i},{"cache_reset_before_request",true},
                {"sidecar_written_after_model_and_source_retirement",true},{"JSON_created_after_model_and_source_retirement",true}});
            write_fresh_report(startup.admission_report+".arm"+std::to_string(i)+".routes",r);
        }
        struct ps5_heap_stats heap{};ps5_heap_stats(&heap);
        write_fresh_report(startup.admission_report,{{"schema","ps5-qwen-resident-comparison-result-v1"},
            {"pid",getpid()},{"run_id",run},{"completed",true},{"requests",completed},{"model_loads",1},
            {"candidate_SELF_sha256",policy.at("native_first_generation_validation").at("candidate_SELF_sha256")},
            {"model_receipt_sha256",policy.at("native_first_generation_validation").at("model_receipt_sha256")},
            {"all_original_tokens_and_bytes_exact",true},{"forced_rejection_and_full_F32_restore_passed",true},
            {"all_model_source_device_owners_positively_retired",true},{"device_ledger_live_bytes",0},
            {"CPU_heap_peak_bytes",heap.peak_bytes},{"device_ledger_peak_bytes",ledger.peak},
            {"source_windows",source_stats.chunks},{"source_completed_windows",source_stats.completed_windows},
            {"source_physical_read_bytes",source_stats.physical_read_bytes},
            {"source_physical_read_calls",source_stats.physical_read_calls},
            {"memory_backpressure",memory_backpressure_report()},
            {"HTTP_requests",0},{"VideoOut_starts",0},{"speedup_qualified",false},{"production_adopted",false}});
        qwen_native_stage("resident_comparison_completed_waiting_for_ordinary_close");
        for(;;)(void)usleep(1000000);
    }catch(const std::exception &e){
        try {if(!validation_report.empty())write_fresh_report(validation_report+".resident.startup-memory",resident_startup_report());}catch(...){}
        qwen_native_stage("resident_comparison_exception_work_stopped");
        if(native_resources_started){qwen_native_driver_retain();engine.release();}
        if(!validation_report.empty())try{write_fresh_report(validation_report+".failure",{{"message",e.what()},
            {"last_model_load_error",qwen_app::resident_last_model_error()},
            {"model_loaded",model!=nullptr},{"native_resources_started",native_resources_started},
            {"CPU_worker_completion_unknown",resident_worker_completion_unknown},
            {"memory_backpressure",memory_backpressure_report()}});}catch(...){}
        for(;;)(void)usleep(1000000);
    }
}
