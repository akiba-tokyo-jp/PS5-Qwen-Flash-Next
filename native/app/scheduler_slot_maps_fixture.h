// SPDX-License-Identifier: MIT
#pragma once
#include "scheduler_slot_maps.h"
#include "ggml-vulkan.h"
#include "ggml-cpu.h"
#include <nlohmann/json.hpp>
#include <chrono>

namespace qwen_app { namespace scheduler_slot_maps_fixture {
inline bool copy(ggml_backend_t backend, const ggml_tensor * source,
                 ggml_tensor * destination, ggml_cgraph *, void * opaque) {
    const auto * sources = static_cast<const std::array<ggml_tensor *, 2> *>(opaque);
    for (unsigned layer = 0; layer < sources->size(); ++layer) {
        if ((*sources)[layer] != source) continue;
        auto * const data = destination->data;
        auto * const buffer = destination->buffer;
        const bool accepted = scheduler_slot_map_owner->publish(backend, layer, source, destination);
        if (destination->data != data || destination->buffer != buffer)
            throw std::runtime_error("Publication changed a live scheduler address");
        return accepted;
    }
    return false;
}
inline nlohmann::json run(void (*checkpoint)(), void (*stage)(const char *), void (*admit)()) {
    using Json = nlohmann::json;
    using Clock = std::chrono::steady_clock;
    const auto need = [](bool value, const char * message) {
        if (!value) throw std::runtime_error(message);
    };
    const auto deadline = Clock::now() + std::chrono::seconds(180);
    admit();
    auto * gpu = ggml_backend_vk_init(0);
    auto * cpu = ggml_backend_cpu_init();
    need(gpu && cpu, "Actual CPU/Vulkan scheduler backends required");
    ggml_backend_cpu_set_n_threads(cpu, 1);
    ggml_init_params hp{};
    hp.no_alloc = true; hp.mem_size = 2 * ggml_tensor_overhead() + 256;
    auto * host = ggml_init(hp);
    need(host != nullptr, "CPU map metadata unavailable");
    std::array<ggml_tensor *, 2> sources{};
    for (unsigned layer = 0; layer < sources.size(); ++layer) {
        sources[layer] = ggml_new_tensor_2d(host, GGML_TYPE_I32, 1, 512);
        ggml_format_name(sources[layer], "fixture.slot_map-%u", layer);
    }
    auto * host_buffer = ggml_backend_alloc_ctx_tensors(host, cpu);
    need(host_buffer != nullptr, "CPU map buffer unavailable");
    ggml_backend_buffer_set_usage(host_buffer, GGML_BACKEND_BUFFER_USAGE_WEIGHTS);
    ggml_backend_t backends[] = {gpu, cpu};
    auto * scheduler = ggml_backend_sched_new(backends, nullptr, 2, 128, false, true);
    need(scheduler != nullptr, "Actual graph scheduler unavailable");
    ggml_backend_sched_set_copy_callback(scheduler, copy, &sources);
    Json arms = Json::array(); unsigned graphs = 0;
    {
        SchedulerSlotMaps maps(gpu, {sources[0], sources[1]}, 64);
        for (unsigned arm = 0; arm < 2; ++arm) {
            scheduler_slot_map_reuse = arm != 0;
            const auto before = scheduler_slot_map_counts;
            Json samples = Json::array();
            const unsigned shapes[] = {30, 1, 30, 1};
            for (unsigned phase = 0; phase < 4; ++phase) {
                admit(); need(Clock::now() < deadline, "Finite scheduler fixture deadline reached");
                ggml_backend_sched_reset(scheduler);
                ggml_init_params gp{}; gp.no_alloc = true;
                gp.mem_size = 32 * ggml_tensor_overhead() + ggml_graph_overhead_custom(64, false) + 256;
                auto * context = ggml_init(gp);
                need(context != nullptr, "Fixture graph metadata unavailable");
                auto * indices = ggml_new_tensor_1d(context, GGML_TYPE_I32, shapes[phase]);
                ggml_set_input(indices);
                std::array<ggml_tensor *, 2> outputs{}, views{};
                auto * graph = ggml_new_graph_custom(context, 64, false);
                for (unsigned layer = 0; layer < 2; ++layer) {
                    outputs[layer] = ggml_get_rows(context, sources[layer], indices);
                    need(ggml_backend_supports_op(gpu, outputs[layer]), "Map lookup must execute on GPU");
                    ggml_backend_sched_set_tensor_backend(scheduler, outputs[layer], gpu);
                    ggml_set_output(outputs[layer]);
                    views[layer] = ggml_view_1d(context, outputs[layer], shapes[phase], 0);
                    ggml_set_output(views[layer]);
                    ggml_build_forward_expand(graph, views[layer]);
                }
                need(ggml_backend_sched_alloc_graph(scheduler, graph), "Scheduler graph allocation failed");
                std::array<std::int32_t, 30> ids{};
                for (unsigned i = 0; i < shapes[phase]; ++i) ids[i] = (i * 17 + 31) % 512;
                for (unsigned sample = 0; sample < 6; ++sample) {
                    admit(); need(Clock::now() < deadline && graphs < 48, "Finite scheduler graph bound reached");
                    std::array<std::array<std::int32_t, 512>, 2> authoritative{};
                    for (unsigned layer = 0; layer < 2; ++layer) {
                        const unsigned revision = phase >= 2 && layer == 1 ? sample / 2 + 1 : 0;
                        for (unsigned i = 0; i < 512; ++i)
                            authoritative[layer][i] = (i * 3 + layer * 7 + revision) % 64;
                        authoritative[layer][511] = -1;
                        ggml_backend_tensor_set(sources[layer], authoritative[layer].data(), 0, 512 * sizeof(std::int32_t));
                    }
                    ggml_backend_tensor_set(indices, ids.data(), 0, shapes[phase] * sizeof(std::int32_t));
                    const auto begin = Clock::now();
                    need(ggml_backend_sched_graph_compute(scheduler, graph) == GGML_STATUS_SUCCESS,
                         "Actual CPU/Vulkan scheduler execution failed; retain owner");
                    ggml_backend_sched_synchronize(scheduler); checkpoint(); ++graphs;
                    samples.push_back(std::chrono::duration<double, std::micro>(Clock::now() - begin).count());
                    for (unsigned layer = 0; layer < 2; ++layer) {
                        need(ggml_backend_sched_get_tensor_backend(scheduler, outputs[layer]) == gpu,
                             "Map output silently fell back to CPU");
                        std::array<std::int32_t, 30> actual{}, viewed{};
                        ggml_backend_tensor_get(outputs[layer], actual.data(), 0, shapes[phase] * sizeof(std::int32_t));
                        ggml_backend_tensor_get(views[layer], viewed.data(), 0, shapes[phase] * sizeof(std::int32_t));
                        for (unsigned i = 0; i < shapes[phase]; ++i)
                            need(actual[i] == authoritative[layer][ids[i]] && viewed[i] == actual[i],
                                 "Scheduler map lookup or descendant view differs");
                    }
                    maps.verify_completed(); checkpoint();
                }
                ggml_backend_sched_reset(scheduler); ggml_free(context);
            }
            Json delta = Json::array();
            for (unsigned i = 0; i < 10; ++i) delta.push_back(scheduler_slot_map_counts[i] - before[i]);
            need(delta[0] == 48 && delta[1].get<unsigned>() + delta[2].get<unsigned>() == 48 && delta[3] == 8,
                 "Every scheduled map copy and pre-allocation binding must reconcile");
            need(arm ? delta[2].get<unsigned>() > 0 : delta[2] == 0, "Actual reuse/control execution required");
            arms.push_back({{"reuse_enabled", arm != 0}, {"samples_us", samples}, {"slot_map_delta", delta}});
        }
        ggml_backend_sched_synchronize(scheduler); checkpoint();
    }
    scheduler_slot_map_reuse = false;
    ggml_backend_sched_free(scheduler);
    ggml_backend_buffer_free(host_buffer); ggml_free(host);
    ggml_backend_free(cpu); ggml_backend_free(gpu); checkpoint();
    need(graphs == 48 && !scheduler_slot_map_owner, "Complete scheduler fixture retirement required");
    stage("scheduler_slot_map_fixture_completed");
    return {{"completed", true}, {"GPU_graphs", graphs}, {"arms", arms},
            {"all_I32_bytes_and_canaries_exact", true}, {"actual_CPU_Vulkan_scheduler", true},
            {"prefill30_decode1_and_rebuilds", true}, {"cached_graphs_and_descendant_views", true},
            {"cross_layer_updates_and_evictions", true}, {"live_address_changes", 0},
            {"synthetic_inputs_only", true}, {"model_loaded", false}};
}
}}
