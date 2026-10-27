// SPDX-License-Identifier: MIT
// No model tensors, payload reads, queue submissions or graphs are involved.
            Json buffer_measurement=nullptr;
            if(policy.contains("native_resident_GPU_buffer_capacity")) {
                std::array<ggml_backend_buffer_t,5> buffers{};
                const std::array<std::size_t,5> sizes{{2147483648ull,2147483648ull,2147483648ull,2147483648ull,165170688ull}};
                Json observations=Json::array();std::uint64_t requested=0;unsigned allocated=0;
                std::string terminal="completed";
                ps5_ai_arena_stats before_buffers{};ps5_ai_arena_snapshot(&before_buffers);
                for(unsigned i=0;i<sizes.size();++i) {
                    const auto memory=qwen_app::observe_native_system_memory();
                    const auto floor=std::uint64_t(memory.kernel_minimum)+std::max<std::uint64_t>(memory.kernel_reserved,256);
                    // This selected next-operation allowance is provisional,
                    // not a measured universal bound for a 2 GiB allocation.
                    if(memory.kernel_free<floor+512){terminal="selected_per_buffer_VM_allowance_refused";break;}
                    const auto budget=qwen_native_allocator_budget(calibration_total);
                    const auto rounded=(sizes[i]+(2ull<<20)-1)&~((2ull<<20)-1);
                    if(budget.available<rounded+(512ull<<20)||memory.flexible_available<(256ull<<20)) {
                        terminal="fresh_Direct_or_Flexible_capacity_refused";break;
                    }
                    qwen_native_stage("resident_GPU_capacity_before_one_buffer_allocation");
                    buffers[i]=ggml_backend_alloc_buffer(calibration_backend,sizes[i]);
                    qwen_native_stage("resident_GPU_capacity_one_buffer_allocation_returned");
                    const auto after=qwen_app::observe_native_system_memory();
                    ps5_ai_arena_stats owned{};ps5_ai_arena_snapshot(&owned);
                    observations.push_back({{"ordinal",i},{"requested_bytes",sizes[i]},
                        {"free_before",memory.kernel_free},{"free_after",after.kernel_free},
                        {"owned_Direct_bytes_after",owned.used_bytes},
                        {"allocation_returned",true},{"allocation_succeeded",buffers[i]!=nullptr}});
                    if(owned.mapping_uncertain||owned.gpu_fault_retained)
                        throw std::runtime_error("Returned GPU allocation retained uncertain native ownership; ordinary OS close required");
                    if(!buffers[i]){terminal="allocation_returned_null";break;}
                    requested+=sizes[i];++allocated;
                    resident_sample("GPU_capacity_buffer_allocation_returned");
                    if(after.kernel_free<floor){terminal="ordinary_floor_after_return_refused";break;}
                }
                ggml_backend_synchronize(calibration_backend);qwen_native_driver_checkpoint();
                resident_sample("GPU_capacity_buffers_live_before_metadata_retirement");
                ps5_ai_arena_stats live{};ps5_ai_arena_snapshot(&live);
                for(auto it=buffers.rbegin();it!=buffers.rend();++it)if(*it){ggml_backend_buffer_free(*it);*it=nullptr;}
                qwen_native_driver_checkpoint();resident_sample("GPU_capacity_buffer_metadata_retired_backing_owned_until_OS_close");
                ps5_ai_arena_stats retired{};ps5_ai_arena_snapshot(&retired);
                if(retired.mapping_uncertain||retired.gpu_fault_retained||retired.live_allocations!=before_buffers.live_allocations)
                    throw std::runtime_error("Raw buffer retirement ownership is uncertain");
                // No submission means there is no completed kick epoch. The
                // existing allocator intentionally retains physical mappings
                // until normal OS close. Never invent an epoch or force a free.
                buffer_measurement={{"completed",true},{"all_five_allocated",allocated==5},
                    {"allocated_buffers",allocated},{"requested_live_peak_bytes",requested},
                    {"selected_per_buffer_future_VM_pages",512},{"terminal",terminal},
                    {"observations",observations},{"buffer_free_callbacks_returned",allocated},
                    {"live_calibration_buffer_objects",0},{"model_tensors_created",0},
                    {"driver_owned_bytes_before",before_buffers.used_bytes},
                    {"driver_owned_bytes_at_peak",live.used_bytes},{"driver_owned_bytes_after_callbacks",retired.used_bytes},
                    {"physical_backing_retained_for_ordinary_OS_close",true},
                    {"queue_submissions",0},{"not_the_exact_model_BO_layout",true},
                    {"universal_peak_bound_established",false}};
            }
