// SPDX-License-Identifier: MIT
// Transport/control fixture: no Engine, weights, Vulkan or learned inference.
#include "bounded_demo.h"
#include "monitor_clock.h"
#include <iostream>
#include <thread>
extern "C" bool qwen_native_faulted() { return false; }

int main(int argc, char ** argv) {
    if (argc != 3 && argc != 4) return 2;
    const bool inject_failure = argc == 4 && std::string(argv[3]) == "--fail-request";
    using Json = nlohmann::json;
    const auto owner = std::this_thread::get_id();
    unsigned calls = 0, screens = 0;
    const auto now = qwen_app::MonitorClock::system_epoch_ms();
    qwen_app::monitor_clock().initialize(qwen_app::ClockCalibration{now, now, 0});
    try {
        const std::string correct = "1, 2, 3, 4, 5, 6, 7, 8\n";
        qwen_app::require_demo_sequence({correct.begin(), correct.end()});
        for (const std::string invalid : {"1, 2, 3", "1,2,3,4,5,6,7,9", "1,2,3,4,5,6,7,8,9"}) {
            bool rejected = false;
            try { qwen_app::require_demo_sequence({invalid.begin(), invalid.end()}); }
            catch (const std::runtime_error &) { rejected = true; }
            if (!rejected) throw std::runtime_error("An incomplete or incorrect benchmark answer was accepted");
        }
        const auto result = qwen_app::serve_bounded_demo(std::string(32, 'a'), argv[2], "127.0.0.1", std::stoi(argv[1]), {},
            [&](unsigned ordinal, const auto & alive, const auto & publish) {
                if (std::this_thread::get_id() != owner || ++calls != ordinal || !alive())
                    throw std::runtime_error("The transport changed the admitted producer or request order");
                for (unsigned i = 1; i <= 2; ++i) {
                    publish(Json{{"id", std::string(32, 'a') + "-" + std::to_string(ordinal)},
                        {"type", "token"}, {"state", "generating"}, {"ordinal", i}, {"token_id", i},
                        {"piece_bytes", {48 + i}}, {"metrics", {{"generated_tokens", i},
                            {"total_ms", i * 20}, {"ttft_ms", 20}, {"decode_tokens_per_second", 50}}}});
                    if (inject_failure) throw std::runtime_error("Synthetic owner failure after a published event");
                }
                publish(Json{{"id", std::string(32, 'a') + "-" + std::to_string(ordinal)},
                    {"type", "finished"}, {"state", "completed"}, {"metrics", {{"generated_tokens", 2},
                        {"total_ms", 50}, {"ttft_ms", 20}, {"decode_tokens_per_second", 50}}}});
                return Json{{"synthetic_transport_request", ordinal}};
            }, [&](const auto &) { ++screens; }, [&](const auto &) { std::cout << "ready\n" << std::flush; });
        if (calls != 2 || !screens || result.at("external_requests_completed") != 2 ||
            result.at("listener_stopped") != true || result.at("finish_acknowledgement_delivered") != true)
            throw std::runtime_error("The bounded transport did not finish positively");
        std::cout << Json{{"synthetic_requests", calls}, {"passive_snapshots", screens},
            {"caller_thread_preserved", true}, {"learned_inference", false}, {"result", result}}.dump() << '\n';
        return 0;
    } catch (const std::exception & error) { std::cerr << error.what() << '\n'; return 1; }
}
