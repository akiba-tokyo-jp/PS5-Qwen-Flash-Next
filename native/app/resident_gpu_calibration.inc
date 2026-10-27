// SPDX-License-Identifier: MIT
// A separate model-free frontier; no inference, graph or tensor payload.
        if(policy.contains("native_resident_GPU_initialization_calibration")) {
            qwen_app::require_resident_gpu_calibration_policy(policy);
            if(policy.contains("native_resident_GPU_buffer_capacity"))qwen_app::require_resident_gpu_buffers(policy);
            const auto &prior=policy.at("native_resident_GPU_fixture_qualification");
            if(prior.at("report_sha256")!="d596ba7c1c149b9b8819f095826063bf972f6ef2f612cad2a019641b05861411")
                throw std::runtime_error("Exact earlier complete GPU fixture evidence required");
            const auto prior_report=read_completed_native_report(prior);
            qwen_app::require_large_cache_layout_report(prior_report,prior);
            const auto phase_component=qwen_app::resident_gpu_phase_component(prior_report);
            const auto entry=qwen_app::admit_native_system_memory();
            const auto ordinary_extra=std::max<std::uint64_t>(entry.kernel_reserved,256);
            if(entry.kernel_minimum!=898||entry.kernel_reserved!=206||ordinary_extra+phase_component>512)
                throw std::runtime_error("Fixture and ordinary-reserve component prices exceed the scoped total");
            const auto required=std::max<std::uint64_t>(entry.kernel_minimum+ordinary_extra,entry.kernel_minimum+512);
            if(entry.kernel_free<required)throw qwen_app::KernelMemoryPressure();
            // The total initializer allowance is prepaid once. Later completed
            // boundaries retain the ordinary floor; do not recharge already
            // resident initializer objects as new future work.
            const auto phase_boundary=[&]{const auto m=qwen_app::admit_native_system_memory();
                if(m.kernel_minimum!=entry.kernel_minimum||m.kernel_reserved!=entry.kernel_reserved)
                    throw qwen_app::KernelMemoryPressure();};
            resident_sample("GPU_initializer_before");
            if(!qwen_native_gpu_frontend_linked()||setenv("GGML_VK_SUBALLOCATION_BLOCK_SIZE","2147483648",1))
                throw std::runtime_error("The original native frontend and batching target are required");
            qwen_native_stage("resident_GPU_initializer_calibration_before_native_GPU_call");
            native_resources_started=true;
            qwen_native_gpu_initialize((startup.admission_report+".driver.log").c_str());
            qwen_native_driver_begin();
            resident_sample("GPU_initializer_frontend_returned");
            phase_boundary();
#if defined(QWEN_RESIDENT_COMPACT_GPU)
            // CPU clock/context admission already initialized ggml. This raw
            // buffer fixture needs neither a model factory nor CPU registry.
            (void)ggml_backend_vk_reg();
#else
            llama_backend_init();
#endif
            resident_sample("GPU_initializer_registry_returned");
#if defined(QWEN_RESIDENT_COMPACT_GPU)
            auto calibration_device=ggml_backend_reg_dev_get(ggml_backend_vk_reg(),0);
#else
            auto calibration_device=ggml_backend_dev_by_type(GGML_BACKEND_DEVICE_TYPE_GPU);
            if(!calibration_device)calibration_device=ggml_backend_dev_by_type(GGML_BACKEND_DEVICE_TYPE_IGPU);
#endif
            if(!calibration_device)throw std::runtime_error("GPU initializer device is unavailable");
            std::size_t calibration_free=0,calibration_total=0;
            ggml_backend_dev_memory(calibration_device,&calibration_free,&calibration_total);
            resident_sample("GPU_initializer_device_returned");
            phase_boundary();
            // The post-load ledger requires a completed SourceReader window.
            // This empty-backend fixture has no source reader or tensor API.
            // Keep that model-only guard disabled instead of fabricating a
            // completed source window or weakening the production guard.
            auto *calibration_backend=ggml_backend_vk_init(0);
            if(!calibration_backend)throw std::runtime_error("GPU initializer backend is unavailable");
            resident_sample("GPU_initializer_backend_returned");
#include "resident_gpu_buffers.inc"
            ggml_backend_synchronize(calibration_backend);qwen_native_driver_checkpoint();
            resident_sample("GPU_initializer_empty_queue_completed");
            ggml_backend_free(calibration_backend);qwen_native_driver_complete();
            resident_sample("GPU_initializer_backend_retired_no_model_sources_started");
            write_fresh_report(startup.admission_report+".resident.startup-memory",resident_startup_report());
            write_fresh_report(startup.admission_report,{{"schema","ps5-qwen-resident-GPU-initialization-calibration-result-v1"},
                {"pid",getpid()},{"run_id",policy.at("native_first_generation_validation").at("run_id")},
                {"completed",true},{"model_loaded",false},{"model_loads",0},{"model_requests",0},
                {"graph_computes",0},{"tensor_payload_allocations",0},{"backend_instances",1},
                {"entry_free_pages",entry.kernel_free},{"selected_total_above_kernel_minimum_pages",512},
                {"ordinary_operational_floor_pages",entry.kernel_minimum+ordinary_extra},
                {"sampled_phase_component_pages",phase_component},{"selected_required_pages",required},
                {"earlier_complete_GPU_fixture_global_decline_pages",103},{"initializer_scope_is_subset_of_earlier_fixture",true},
                {"device_free_bytes",calibration_free},{"device_total_bytes",calibration_total},
                {"backend_instance_positively_synchronized_and_retired",true},{"source_workers_stopped",true},
                {"source_chunks",0},{"source_completed_windows",0},{"source_workers_started",0},
                {"whole_model_metadata_files",0},{"whole_model_CPU_preflight_repeated",false},
                {"postload_model_device_ledger_enabled",false},{"model_tensor_API_calls",0},
                {"buffer_capacity_measurement",buffer_measurement},
                {"global_device_lifetime_retained_until_ordinary_OS_close",true},
                {"unknown_completion",false},{"ordinary_OS_close_required",true}});
            qwen_native_stage("resident_GPU_initializer_calibration_completed_waiting_for_ordinary_close");
            for(;;)(void)usleep(1000000);
        }
