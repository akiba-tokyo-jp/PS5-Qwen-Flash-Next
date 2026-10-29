// SPDX-License-Identifier: MIT
// Included only after the original complete model/context admission.
        const auto *chat_template=llama_model_chat_template(model,nullptr);
        if(!chat_template||!*chat_template)throw std::runtime_error("Original chat template required");
        if(policy.at("native_Expert_Q2_bundle_comparison")!=Json::parse(routing_comparison_scope))
            throw std::runtime_error("Exact routing and sharing comparison scope required");
        qwen_native_driver_complete();resident_sample("original_model_context_completed");
        write_fresh_report(startup.admission_report+".resident.startup-memory",resident_startup_report());
        const auto run=policy.at("native_first_generation_validation").at("run_id").get<std::string>();
        const auto columns=static_cast<std::size_t>(llama_vocab_n_tokens(llama_model_get_vocab(model)));
        if(!columns||columns>262144)throw std::runtime_error("Bounded original vocabulary required");
        constexpr unsigned request_count=20;
        constexpr unsigned counting_modes[]={0,0,4,4,0};
        const char*quality_prompts[]={
            "Translate to English. Output only the translation: おはようございます。",
            "Compute 17 + 26. Output only the integer.",
            "Return only a JSON object with city set to Tokyo and count set to 3."};
        std::array<CompletedRouteEvidence,request_count>routes;
        Json completed=Json::array();
        std::vector<float>reference_logits(33*columns);
        std::vector<std::int32_t>reference_ids;std::size_t reference_rows=0;
        std::uint64_t last_payload=0,saved_payload=0,observed_captures=0;
        const auto admit_checkpoint=[&](std::uint64_t bytes){
            require_model_CPU_budget();require_unchanged_model();
            if(bytes<118038528||bytes>142606336)throw std::runtime_error("Complete checkpoint payload outside qualification");
            const auto captures=engine->checkpoint_validation_stats().captures;
            if(captures!=observed_captures){
                if(captures!=observed_captures+1||!last_payload)throw std::runtime_error("Checkpoint replacement lacks positive prior capture");
                saved_payload=last_payload;observed_captures=captures;
            }
            const auto rounded=qwen_app::checkpoint_replacement_growth(bytes,saved_payload);
            const auto ledger=qwen_app::native_model_device_stats();const auto budget=qwen_native_allocator_budget(driver_total);
            const auto admission="model_checkpoint_replacement_admission payload="+std::to_string(bytes)+" completed_payload="+std::to_string(saved_payload)+
                " additional_upper="+std::to_string(rounded)+" device_live="+std::to_string(ledger.live)+" direct_available="+std::to_string(budget.available);
            qwen_native_stage(admission.c_str());
            if(ledger.live>qwen_app::model_postload_device_budget||rounded>qwen_app::model_postload_device_budget-ledger.live||
               budget.available<rounded+memory_budget.direct_reserve||observed_system_headroom()<memory_budget.flexible_reserve)
                throw std::runtime_error("Complete checkpoint cannot retain original reserves");
            last_payload=bytes;
        };
        for(unsigned ordinal=0;ordinal<request_count;++ordinal){
            const bool counting=ordinal<5;const unsigned mode=counting?counting_modes[ordinal]:(ordinal-5)%5;
            const unsigned task=counting?0:(ordinal-5)/5;
            require_model_CPU_budget();require_unchanged_model();qwen_app_complete_predictive_expert();
            const auto previous=engine->expert_cache_metrics();if(!previous)throw std::runtime_error("Actual cache counters required");
            qwen_native_driver_begin();engine.reset();qwen_native_driver_complete();
            qwen_native_driver_begin();
            qwen_app_select_Q2_probation(true);qwen_app_select_Q2_bundle(true);qwen_app_select_Q2_reader(1);
            qwen_app_select_Q2_adjacent(true);qwen_app_select_Q2_normal_IO(5);qwen_app_select_Q2_temporal(0);
            resident_reset_empty_context(context,model,startup.admission_report);
            qwen_app_route_begin(mode);
            engine=std::make_unique<qwen_app::LlamaEngine>(model,context,4);
            observed_captures=0;
            engine->set_stage_observer(observed_inference_stage);
            engine->set_gpu_boundaries(qwen_native_driver_begin,qwen_native_driver_complete,qwen_native_driver_retain,qwen_native_driver_checkpoint);
            qwen_native_driver_complete();require_model_CPU_budget();
            if(mode==4)engine->enable_speculative_step_prototype(admit_checkpoint);
            std::size_t rows=0;double max_error=0;bool finite=true;
            engine->set_logits_observer([&](const float*v,std::size_t count)noexcept{
                if(!v||count!=columns||rows>=33){finite=false;return;}
                for(std::size_t i=0;i<count;++i){
                    if(!std::isfinite(v[i]))finite=false;
                    if(counting&&!ordinal)reference_logits[rows*columns+i]=v[i];
                    else if(counting&&rows<reference_rows)max_error=std::max(max_error,std::abs(double(v[i])-reference_logits[rows*columns+i]));
                }
                ++rows;
            });
            qwen_app::RepeatedExpertQ2SpeculativeEngine adapter(*engine,model,context,mode==4);
            qwen_app::FirstGeneration trial(adapter);
            engine->set_work_guard([&]{trial.require_time();require_model_CPU_budget();},64);
            const auto perf=performance_snapshot(*engine);const auto cache=engine->expert_cache_metrics();
            if(!cache)throw std::runtime_error("Initial source/cache counters required");
            qwen_app::require_resident_context_counter_baseline(*previous,*cache);
            const auto predicted=predictive_cache_bytes();qwen_app::begin_completed_expert_routes();
            const auto prefix=startup.admission_report+".arm"+std::to_string(ordinal);
            const qwen_app::Request request{run+"-"+std::to_string(ordinal),qwen_app::render_bounded_user_prompt(chat_template,
                counting?qwen_app::demo_prompt:quality_prompts[task]),256,32};
            const auto &result=trial.run(request,[&](const auto&bound){
                write_fresh_report(prefix+".intent",{{"id",bound.id},{"pid",getpid()},{"run_id",run},{"mode",mode},
                    {"counting",counting},{"quality_task",counting?Json(nullptr):Json(task)},{"maximum_output_tokens",32}});
            },[&](const auto&token,const auto&m){
                write_fresh_report(prefix+".token-"+std::to_string(m.generated_tokens),{{"token_id",token.id},
                    {"piece_bytes",std::vector<unsigned char>(token.piece.begin(),token.piece.end())},
                    {"generated_tokens",m.generated_tokens},{"elapsed_ms",m.total_ms},{"completed_performance",performance_snapshot(*engine)}});
            },observed_inference_stage);
            engine->set_work_guard({});engine->set_logits_observer({});qwen_app_complete_predictive_expert();
            if(!result.request_reset_completed||!finite||!rows)throw std::runtime_error("Finite complete vocabulary and positive request reset required");
            if(counting&&!ordinal){reference_rows=rows;reference_ids=result.token_ids;}
            if(counting&&mode==0&&(rows!=reference_rows||max_error!=0||result.token_ids!=reference_ids))
                throw std::runtime_error("Unchanged routing controls must retain exact full F32 and emitted tokens");
            routes[ordinal]=completed_route_evidence(*engine,perf.at("process_calls").get<std::uint64_t>(),*cache,predicted);
            if(!routes[ordinal].complete)throw std::runtime_error("Actual variable-k routes must reconcile with all source transfers");
            const auto spec=engine->speculative_step_stats();const auto checkpoints=engine->checkpoint_validation_stats();
            if(spec.attempts){if(checkpoints.captures!=spec.attempts||spec.attempts!=spec.accepted+spec.rejected||checkpoints.restores!=spec.rejected)
                    throw std::runtime_error("Every speculative attempt requires complete capture and a verified decision");
                saved_payload=last_payload;}
            std::uint64_t routing[3]{};qwen_app_route_stats(routing);
            bool counting_pass=false;if(counting)try{qwen_app::require_demo_sequence(result.output_bytes);counting_pass=true;}catch(const std::exception&){}
            Json row={{"ordinal",ordinal},{"mode",mode},{"counting",counting},{"quality_task",counting?Json(nullptr):Json(task)},
                {"metrics",{{"prompt_tokens",result.metrics.prompt_tokens},{"generated_tokens",result.metrics.generated_tokens},
                    {"TTFT_ms",result.metrics.ttft_ms?Json(*result.metrics.ttft_ms):Json(nullptr)},
                    {"prefill_ms",result.metrics.prefill_ms},{"decode_ms",result.metrics.decode_ms},
                    {"decode_tokens_per_second",result.metrics.decode_tokens_per_second?Json(*result.metrics.decode_tokens_per_second):Json(nullptr)},
                    {"total_ms",result.metrics.total_ms}}},
                {"token_ids",result.token_ids},{"output_bytes",result.output_bytes},{"stop_reason",result.stop_reason},
                {"request_reset_completed",result.request_reset_completed},{"full_F32_finite",finite},{"full_F32_logit_rows",rows},
                {"maximum_absolute_logit_error",counting?Json(max_error):Json(nullptr)},
                {"counting_quality_passed",counting_pass},{"same_counting_tokens_as_control",counting&&result.token_ids==reference_ids},
                {"completed_performance",performance_difference(perf,*engine)},
                {"cache_rank_calls",routing[0]},{"cache_rank_resident_scores",routing[1]},{"cache_rank_CPU_ns",routing[2]},
                {"speculation",{{"attempts",spec.attempts},{"accepted",spec.accepted},{"rejected",spec.rejected},
                    {"snapshot_captures",checkpoints.captures},{"snapshot_restores",checkpoints.restores},{"payload_bytes",last_payload}}}};
            completed.push_back(row);write_fresh_report(prefix+".result",row);
            resident_reuse_sample("after_completed_request");qwen_native_stage("resident_additional_arm_completed_positive_request_reset");
        }
        qwen_app_complete_predictive_expert();qwen_native_driver_begin();
        engine.reset();llama_free(context);context=nullptr;llama_model_free(model);model=nullptr;qwen_native_driver_complete();
        const auto source=qwen_app::native_model_source_stats();
        if(source.chunks!=source.completed_windows)throw std::runtime_error("Original source windows remain incomplete");
        qwen_app::stop_native_model_sources();const auto ledger=qwen_app::native_model_device_stats();
        if(ledger.live||qwen_app_resident_cache_reuse_live_owners())throw std::runtime_error("Additional model owners remain live");
        for(unsigned i=0;i<request_count;++i){auto report=completed_route_report(routes[i]);
            report.update({{"pid",getpid()},{"run_id",run},{"ordinal",i},{"cache_reset_before_request",true},
                {"sidecar_written_after_model_and_source_retirement",true},{"JSON_created_after_model_and_source_retirement",true}});
            write_fresh_report(startup.admission_report+".arm"+std::to_string(i)+".routes",report);}
        struct ps5_heap_stats heap{};ps5_heap_stats(&heap);
        write_fresh_report(startup.admission_report,{{"schema","ps5-qwen-routing-sharing-result-v1"},{"completed",true},
            {"requests",completed},{"model_loads",1},{"pid",getpid()},{"run_id",run},
            {"candidate_SELF_sha256",policy.at("native_first_generation_validation").at("candidate_SELF_sha256")},
            {"model_receipt_sha256",policy.at("native_first_generation_validation").at("model_receipt_sha256")},
            {"all_model_source_device_owners_positively_retired",true},{"device_ledger_live_bytes",0},
            {"CPU_heap_peak_bytes",heap.peak_bytes},{"device_ledger_peak_bytes",ledger.peak},
            {"source_windows",source.chunks},{"source_completed_windows",source.completed_windows},
            {"graph_reuse_disabled_uniformly",true},{"routing_quality_is_measured_not_an_equality_gate",true},
            {"HTTP_requests",0},{"VideoOut_starts",0},{"production_adopted",false}});
        qwen_native_stage("resident_additional_completed_waiting_for_ordinary_close");
