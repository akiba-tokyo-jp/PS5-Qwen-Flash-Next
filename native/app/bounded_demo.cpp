// SPDX-License-Identifier: MIT
#include "bounded_demo.h"
#include "first_generation.h"
#include "monitor_clock.h"
#include "httplib.h"
#include <atomic>
#include <condition_variable>
#include <deque>
#include <exception>
#include <fstream>
#include <mutex>
#include <thread>
#include <unistd.h>
extern "C" bool qwen_native_faulted();

namespace qwen_app {
using Json = nlohmann::json;
namespace {
using Clock = std::chrono::steady_clock;
std::string asset(const std::string & path) {
    std::ifstream file(path, std::ios::binary);
    if (!file) throw std::runtime_error("A bounded monitor asset is missing");
    file.seekg(0, std::ios::end); const auto bytes = file.tellg(); file.seekg(0);
    if (bytes <= 0 || bytes > (256u << 10)) throw std::runtime_error("Invalid monitor asset size");
    std::string text(std::size_t(bytes), '\0');
    if (!file.read(text.data(), bytes) || file.peek() != std::char_traits<char>::eof())
        throw std::runtime_error("A monitor asset changed during its read");
    return text;
}
struct Job {
    unsigned ordinal = 0;
    std::atomic<bool> disconnected{false};
    std::mutex mutex;
    std::condition_variable changed;
    std::deque<std::string> events;
    bool done = false;
    bool terminal_delivered = false;
};
}

Json serve_bounded_demo(const std::string & run_id, const std::string & assets,
    const std::string & bind_address, int port, const HardwareInfo & hardware, const DemoExecute & execute,
    const std::function<void(const MonitorSnapshot &)> & monitor,
    const std::function<void(const Json &)> & ready) {
    if (run_id.size() != 32 || run_id.find_first_not_of("0123456789abcdef") != std::string::npos ||
        !execute || !monitor || !ready || !monitor_clock().calibrated() ||
        (bind_address != "127.0.0.1" && bind_address != "0.0.0.0"))
        throw std::invalid_argument("A calibrated bounded demonstration and durable readiness observer are required");
    httplib::Server server;
    server.new_task_queue = [] { return new httplib::ThreadPool(3, 3, 8); };
    server.set_payload_max_length(16384);
    server.set_read_timeout(10); server.set_write_timeout(10);
    std::mutex mutex;
    std::condition_variable changed;
    std::shared_ptr<Job> active;
    unsigned accepted = 0, completed = 0, observations = 0, asset_mask = 0;
    std::int64_t first_observation = 0, last_observation = 0;
    bool finish_delivered = false, listener_failed = false;
    Json last = {{"state", "idle"}, {"metrics", Json::object()}};
    Json cache = nullptr;
    Clock::time_point request_started;
    std::deque<double> token_times;
    const auto started = Clock::now();
    auto capture = [&] {
        std::lock_guard<std::mutex> lock(mutex);
        const auto uncertainty = monitor_clock().initial_uncertainty_ms();
        auto request = last;
        const bool quarantined = qwen_native_faulted();
        if (quarantined) request["state"] = "failed";
        request["elapsed_ms"] = active ? std::chrono::duration<double, std::milli>(Clock::now() - request_started).count() :
            request.value("metrics", Json::object()).value("total_ms", 0.0);
        request["live_tokens_per_second"] = nullptr;
        if (active && token_times.size() >= 2) {
            const auto now = std::chrono::duration<double, std::milli>(Clock::now().time_since_epoch()).count();
            const auto start = std::max(token_times.front(), now - 5000.0);
            unsigned intervals = 0;
            for (const auto time : token_times) if (time > start) ++intervals;
            if (now > start) request["live_tokens_per_second"] = intervals * 1000.0 / (now - start);
        }
        return Json{{"backend", "model"}, {"model_loaded", true}, {"process_id", getpid()},
            {"run_id", run_id}, {"busy", bool(active)}, {"quarantined", quarantined}, {"request", request},
            {"expert_cache", cache}, {"server_epoch_ms", monitor_clock().now()},
            {"clock", {{"source", monitor_clock().source()}, {"calibrated", true},
                {"initial_uncertainty_ms", uncertainty ? Json(*uncertainty) : Json(nullptr)}}},
            {"validation", {{"accepted_requests", accepted}, {"completed_requests", completed},
                {"maximum_requests", 2}, {"cache_scope", "first request: empty expert cache; second request: retained cache; file pages and pipelines may be warm"}}},
            {"hardware", {{"cpu", {{"name", hardware.cpu_name}, {"logical_threads", hardware.logical_cpu_threads},
                {"app_usage_percent", nullptr}}}, {"gpu", {{"name", hardware.gpu_name}, {"usage_percent", nullptr},
                {"memory_sample", "driver report after model/context admission"},
                {"total_bytes", hardware.gpu_total_bytes ? Json(*hardware.gpu_total_bytes) : Json(nullptr)},
                {"free_bytes", hardware.gpu_free_bytes ? Json(*hardware.gpu_free_bytes) : Json(nullptr)}}}}}};
    };
    auto show = [&] {
        const auto data = capture(); const auto & request = data.at("request");
        const auto metrics = request.value("metrics", Json::object());
        MonitorSnapshot screen;
        screen.state = request.value("state", "idle"); screen.request_id = request.value("id", "");
        screen.model_loaded = true; screen.busy = data.at("busy");
        screen.quarantined = data.at("quarantined");
        screen.cpu_name = hardware.cpu_name; screen.cpu_threads = hardware.logical_cpu_threads;
        screen.gpu_name = hardware.gpu_name; screen.gpu_total_bytes = hardware.gpu_total_bytes;
        screen.gpu_free_bytes = hardware.gpu_free_bytes;
        screen.epoch_ms = monitor_clock().now(); screen.clock_calibrated = true;
        screen.generated_tokens = metrics.value("generated_tokens", std::uint64_t(0));
        screen.elapsed_ms = metrics.value("total_ms", 0.0);
        if (metrics.contains("ttft_ms") && metrics["ttft_ms"].is_number()) screen.ttft_ms = metrics["ttft_ms"].get<double>();
        if (metrics.contains("decode_tokens_per_second") && metrics["decode_tokens_per_second"].is_number())
            screen.tokens_per_second = metrics["decode_tokens_per_second"].get<double>();
        if (data["expert_cache"].is_object()) {
            const auto & c = data["expert_cache"];
            screen.expert_cache = ExpertCacheMetrics{c.at("hits"), c.at("misses"), c.at("uploaded_bytes"), c.at("prefetch_advice_bytes")};
        }
        screen.message = "ORIGINAL BF16 / EXTERNAL REQUESTS / PASSIVE MONITOR";
        monitor(screen);
    };
    server.Get("/api/status", [&](const auto &, auto & response) {
        {
            std::lock_guard<std::mutex> lock(mutex);
            last_observation = monitor_clock().now();
            if (!observations) first_observation = last_observation;
            ++observations;
        }
        response.set_header("Cache-Control", "no-store");
        response.set_content(capture().dump(), "application/json");
    });
    for (const auto & row : {std::pair<const char *, const char *>{"/", "index.html"},
        {"/app\\.js", "app.js"}, {"/style\\.css", "style.css"}}) {
        const std::string name = row.second;
        const auto body = asset(assets + "/" + name);
        const unsigned mask = name == "index.html" ? 1 : name == "app.js" ? 2 : 4;
        const std::string type = mask == 1 ? "text/html; charset=utf-8" : mask == 2 ?
            "text/javascript; charset=utf-8" : "text/css; charset=utf-8";
        server.Get(row.first, [&, body, mask, type](const auto &, auto & response) {
            { std::lock_guard<std::mutex> lock(mutex); asset_mask |= mask; }
            response.set_content(body, type);
        });
    }
    server.Post("/api/generate", [&](const auto & request, auto & response) {
        try {
            const auto data = Json::parse(request.body);
            auto job = std::make_shared<Job>();
            {
                std::lock_guard<std::mutex> lock(mutex);
                if (active || accepted >= 2 || completed != accepted || finish_delivered || qwen_native_faulted()) {
                    response.status = 409; response.set_content("{}", "application/json"); return;
                }
                const Json expected = {{"id", run_id + "-" + std::to_string(accepted + 1)},
                    {"messages", Json::array({{{"role", "user"}, {"content", demo_prompt}}})},
                    {"context_tokens", first_context_tokens}, {"max_output_tokens", first_output_tokens}, {"enable_thinking", false}};
                if (data != expected || !data.at("context_tokens").is_number_integer() ||
                    !data.at("max_output_tokens").is_number_integer())
                    throw std::invalid_argument("Only the exact two bounded text requests are admitted");
                job->ordinal = ++accepted; active = job;
                request_started = Clock::now(); token_times.clear();
                last = {{"id", expected.at("id")}, {"state", "preparing"}, {"metrics", Json::object()}};
            }
            changed.notify_all();
            response.set_header("Cache-Control", "no-store");
            response.set_header("Connection", "close");
            response.set_chunked_content_provider("text/event-stream", [job](std::size_t, httplib::DataSink & sink) {
                std::unique_lock<std::mutex> lock(job->mutex);
                job->changed.wait_for(lock, std::chrono::seconds(1), [&] { return job->done || job->disconnected || !job->events.empty(); });
                if (job->disconnected) return false;
                if (job->events.empty()) {
                    if (job->done) {
                        job->terminal_delivered = true; job->changed.notify_all();
                        sink.done(); return true;
                    }
                    lock.unlock(); return sink.write(": heartbeat\n\n", 13);
                }
                const auto text = std::move(job->events.front()); job->events.pop_front();
                const bool done = job->done && job->events.empty(); lock.unlock();
                if (!sink.write(text.data(), text.size())) return false;
                if (done) {
                    { std::lock_guard<std::mutex> sent(job->mutex); job->terminal_delivered = true; }
                    job->changed.notify_all(); sink.done();
                }
                return true;
            }, [job](bool) { job->disconnected = true; job->changed.notify_all(); });
        } catch (...) { response.status = 400; response.set_content("{}", "application/json"); }
    });
    server.Post("/api/validation/finish", [&](const auto & request, auto & response) {
        try {
            const auto body = Json::parse(request.body);
            {
                std::lock_guard<std::mutex> lock(mutex);
                if (body != Json{{"run_id", run_id}} || active || completed != 2 || accepted != 2 ||
                    observations < 2 || last_observation - first_observation < 1000 || asset_mask != 7 || finish_delivered)
                    throw std::runtime_error("Completed requests and passive observations are required before shutdown");
            }
            response.set_chunked_content_provider("application/json", [](std::size_t, httplib::DataSink & sink) {
                if (!sink.write("{\"state\":\"accepted\"}", 20)) return false;
                sink.done(); return true;
            }, [&](bool success) {
                if (success) { std::lock_guard<std::mutex> lock(mutex); finish_delivered = true; changed.notify_all(); }
            });
        } catch (...) { response.status = 409; response.set_content("{}", "application/json"); }
    });
    if (!server.bind_to_port(bind_address, port)) throw std::runtime_error("The bounded native listener could not bind");
    std::thread listener([&] {
        const bool success = server.listen_after_bind();
        std::lock_guard<std::mutex> lock(mutex);
        if (!success || !finish_delivered) listener_failed = true;
        changed.notify_all();
    });
    auto stop = [&] {
        std::shared_ptr<Job> pending;
        { std::lock_guard<std::mutex> lock(mutex); pending = active; }
        if (pending) {
            { std::lock_guard<std::mutex> lock(pending->mutex); pending->disconnected = true; pending->done = true; }
            pending->changed.notify_all();
        }
        server.stop(); if (listener.joinable()) listener.join();
    };
    try {
        const auto ready_deadline = Clock::now() + std::chrono::seconds(5);
        while (!server.is_running()) {
            { std::lock_guard<std::mutex> lock(mutex);
              if (listener_failed) throw std::runtime_error("The native listener failed before readiness"); }
            if (Clock::now() > ready_deadline) throw std::runtime_error("Native listener readiness deadline expired");
            std::this_thread::sleep_for(std::chrono::milliseconds(10));
        }
        ready({{"schema", "ps5-qwen-bounded-demo-ready-v1"}, {"pid", getpid()}, {"run_id", run_id},
            {"maximum_requests", 2}, {"context_tokens", first_context_tokens}, {"maximum_output_tokens", first_output_tokens},
            {"prompt", demo_prompt}, {"listener_bind", bind_address}, {"model_loaded", true}, {"native_display_started", true}});
        unsigned processed = 0;
        auto last_activity = Clock::now();
        Json results = Json::array();
        for (;;) {
            std::shared_ptr<Job> job;
            {
                std::unique_lock<std::mutex> lock(mutex);
                changed.wait_for(lock, std::chrono::seconds(1), [&] {
                    return listener_failed || finish_delivered || (active && active->ordinal > processed);
                });
                if (listener_failed) throw std::runtime_error("The native demonstration listener stopped unexpectedly");
                if (finish_delivered) break;
                if (active && active->ordinal > processed) job = active;
            }
            if (Clock::now() - started > std::chrono::hours(3) ||
                Clock::now() - last_activity > std::chrono::minutes(15))
                throw std::runtime_error("The bounded native demonstration wait expired");
            show();
            if (!job) continue;
            Json report;
            try {
            report = execute(job->ordinal, [job] { return !job->disconnected.load(); }, [&](const Json & event) {
                const std::string text = "data: " + event.dump() + "\n\n";
                {
                    std::lock_guard<std::mutex> lock(job->mutex);
                    if (job->disconnected || job->events.size() >= 64 || text.size() > (128u << 10))
                        throw std::runtime_error("The bounded inference observer disconnected or exceeded its queue");
                    job->events.push_back(text);
                }
                {
                    std::lock_guard<std::mutex> lock(mutex);
                    last = event;
                    if (event.value("type", "") == "token") {
                        token_times.push_back(std::chrono::duration<double, std::milli>(Clock::now().time_since_epoch()).count());
                        while (token_times.size() > 32) token_times.pop_front();
                    }
                    if (event.contains("expert_cache")) cache = event.at("expert_cache");
                }
                job->changed.notify_all(); show();
            });
            } catch (...) {
                const auto failure = std::current_exception();
                const Json terminal{{"id", run_id + "-" + std::to_string(job->ordinal)},
                    {"type", "finished"}, {"state", "failed"}, {"error", int(Error::backend_failure)},
                    {"quarantined", true}, {"resource_graph_retained", true}, {"GPU_completion_qualified", false}};
                {
                    std::lock_guard<std::mutex> lock(job->mutex);
                    job->events.push_back("data: " + terminal.dump() + "\n\n"); job->done = true;
                }
                job->changed.notify_all();
                // Give the existing observer one bounded opportunity to receive
                // the failed terminal event. Never retry work or free resources.
                {
                    std::unique_lock<std::mutex> lock(job->mutex);
                    job->changed.wait_for(lock, std::chrono::seconds(2), [&] {
                        return job->terminal_delivered || job->disconnected.load();
                    });
                }
                std::rethrow_exception(failure);
            }
            {
                std::lock_guard<std::mutex> lock(job->mutex); job->done = true;
            }
            job->changed.notify_all();
            {
                std::lock_guard<std::mutex> lock(mutex); ++completed; active.reset();
            }
            results.push_back(report); processed = job->ordinal; last_activity = Clock::now();
        }
        stop();
        return {{"schema", "ps5-qwen-bounded-demo-result-v1"}, {"pid", getpid()}, {"run_id", run_id},
            {"external_requests_accepted", accepted}, {"external_requests_completed", completed},
            {"status_observations", observations}, {"observed_clock_advance_ms", last_observation - first_observation},
            {"all_monitor_assets_requested", asset_mask == 7}, {"finish_acknowledgement_delivered", true},
            {"listener_stopped", true}, {"model_loaded", true}, {"requests", results}};
    } catch (...) { stop(); throw; }
}
}
