// SPDX-License-Identifier: MIT
#include "http_app.h"
#include "httplib.h"
#include "nlohmann/json.hpp"
#include "jinja/lexer.h"
#include "jinja/parser.h"
#include "jinja/runtime.h"
#include "json.h"

#include <atomic>
#include <condition_variable>
#include <deque>
#include <memory>
#include <mutex>
#include <thread>
#include <ctime>

namespace qwen_app {
using Json = nlohmann::json;

static double now_ms() {
    return std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now().time_since_epoch()).count();
}

static const char * name(State state) {
    switch (state) {
        case State::idle: return "idle";
        case State::preparing: return "preparing";
        case State::generating: return "generating";
        case State::completed: return "completed";
        case State::cancelled: return "cancelled";
        case State::failed: return "failed";
    }
    return "failed";
}

static std::string base64(const std::string & value) {
    static const char alphabet[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    std::string result;
    for (std::size_t i = 0; i < value.size(); i += 3) {
        const auto remaining = value.size() - i;
        const unsigned a = static_cast<unsigned char>(value[i]);
        const unsigned b = remaining > 1 ? static_cast<unsigned char>(value[i + 1]) : 0;
        const unsigned c = remaining > 2 ? static_cast<unsigned char>(value[i + 2]) : 0;
        result += alphabet[a >> 2]; result += alphabet[((a & 3) << 4) | (b >> 4)];
        result += remaining > 1 ? alphabet[((b & 15) << 2) | (c >> 6)] : '=';
        result += remaining > 2 ? alphabet[c & 63] : '=';
    }
    return result;
}

struct Job {
    Request request;
    Json messages;
    bool thinking = true;
    std::atomic<bool> cancel{false};
    std::mutex mutex;
    std::condition_variable changed;
    std::deque<std::string> events;
    bool done = false;
};

class Service {
public:
    Service(Engine & engine, const std::string & source)
        : engine_(engine), source_(source), program_(jinja::parse_from_tokens(jinja::lexer().tokenize(source))) {
        worker_ = std::thread([this] { work(); });
    }
    ~Service() {
        {
            std::lock_guard<std::mutex> lock(mutex_);
            stop_ = true;
            if (active_) { active_->cancel = true; active_->changed.notify_all(); }
        }
        changed_.notify_all();
        worker_.join();
    }
    std::shared_ptr<Job> submit(Json data) {
        if (!data.is_object() || !data.contains("messages") || !data["messages"].is_array() ||
            data["messages"].empty() || data["messages"].size() > 64)
            throw std::invalid_argument("Provide 1 to 64 text messages");
        bool user = false;
        if (data.contains("tools") || data.contains("tool_choice"))
            throw std::invalid_argument("Tool calling is not enabled");
        for (const auto & message : data["messages"]) {
            if (!message.is_object() || !message.contains("role") || !message["role"].is_string() ||
                !message.contains("content") || !message["content"].is_string())
                throw std::invalid_argument("Messages require a role and text content");
            if (message.contains("tool_calls") || message.contains("function_call"))
                throw std::invalid_argument("Tool calling is not enabled");
            const auto role = message["role"].get<std::string>();
            if (role != "system" && role != "user" && role != "assistant")
                throw std::invalid_argument("Only system, user, and assistant text are supported");
            if (role == "user") user = true;
        }
        if (!user) throw std::invalid_argument("At least one user message is required");
        auto job = std::make_shared<Job>();
        job->request.id = data.at("id").get<std::string>();
        if (job->request.id.empty() || job->request.id.size() > 128)
            throw std::invalid_argument("Request ID must contain 1 to 128 bytes");
        for (const auto * key : {"max_output_tokens", "context_tokens"}) {
            if (data.contains(key) && (!data[key].is_number_integer() || data[key].get<std::int64_t>() < 1 ||
                data[key].get<std::int64_t>() > 32768)) throw std::invalid_argument("Invalid token budget");
        }
        job->request.max_output_tokens = data.value("max_output_tokens", 128u);
        job->request.context_tokens = data.value("context_tokens", 2048u);
        if (job->request.context_tokens > 4096) throw std::invalid_argument("Context exceeds the current application budget");
        if (job->request.max_output_tokens >= job->request.context_tokens)
            throw std::invalid_argument("Output budget must be smaller than the context");
        job->messages = data["messages"];
        job->thinking = data.value("enable_thinking", true);
        std::lock_guard<std::mutex> lock(mutex_);
        if (active_ || quarantined_) return {};
        active_ = job;
        last_started_ = now_ms();
        first_token_ = 0;
        token_times_.clear();
        last_request_ = {{"id", job->request.id}, {"state", "preparing"}, {"metrics", Json::object()}};
        changed_.notify_one();
        return job;
    }
    bool cancel(const std::string & id) {
        std::lock_guard<std::mutex> lock(mutex_);
        if (!active_ || active_->request.id != id) return false;
        active_->cancel = true;
        active_->changed.notify_all();
        return true;
    }
    Json status() {
        std::lock_guard<std::mutex> lock(mutex_);
        auto request = last_request_;
        if (active_) request["elapsed_ms"] = now_ms() - last_started_;
        else request["elapsed_ms"] = request.value("metrics", Json::object()).value("total_ms", 0.0);
        const auto now = now_ms();
        const auto start = std::max(first_token_, now - 5000.0);
        std::size_t intervals = 0;
        for (double stamp : token_times_) if (stamp > start) ++intervals;
        request["live_tokens_per_second"] = active_ && first_token_ > 0 && now > start
            ? Json(1000.0 * intervals / (now - start)) : Json(nullptr);
        return {{"busy", bool(active_)}, {"quarantined", quarantined_}, {"request", request}, {"expert_cache", expert_cache_}};
    }
private:
    void publish(const std::shared_ptr<Job> & job, const Json & data, bool terminal = false) {
        const auto encoded = "data: " + data.dump() + "\n\n";
        std::unique_lock<std::mutex> lock(job->mutex);
        job->changed.wait(lock, [&] { return job->events.size() < 16 || job->cancel.load(); });
        if (job->cancel) {
            if (!terminal) return;
            job->events.clear();
        }
        job->events.push_back(encoded);
        job->done = terminal;
        lock.unlock(); job->changed.notify_all();
    }
    void work() {
        Session session(engine_);
        for (;;) {
            std::shared_ptr<Job> job;
            {
                std::unique_lock<std::mutex> lock(mutex_);
                changed_.wait(lock, [&] { return stop_ || active_; });
                if (stop_ && !active_) return;
                job = active_;
            }
            bool backend_entered = false;
            try {
                jinja::context context(source_);
                const auto variables = Json{{"messages", job->messages}, {"tools", Json::array()},
                    {"add_generation_prompt", true}, {"enable_thinking", job->thinking}};
                jinja::global_from_json(context, common_json::parse(variables.dump()), true);
                jinja::runtime runtime(context);
                job->request.rendered_prompt = runtime.gather_string_parts(runtime.execute(program_))->as_string().str();
                if (job->request.rendered_prompt.size() > (1u << 20)) throw std::runtime_error("Rendered prompt is too large");
                backend_entered = true;
                session.begin(job->request);
                for (;;) {
                    if (job->cancel) session.cancel();
                    const auto event = session.advance();
                    Json data{{"id", job->request.id}, {"state", name(event.state)}};
                    if (event.token) {
                        data["type"] = "token";
                        data["piece_b64"] = base64(event.token->piece);
                        data["token_id"] = event.token->id;
                    } else data["type"] = event.kind == EventKind::prefilled ? "prefilled" : "finished";
                    const auto & metrics = session.metrics();
                    data["metrics"] = {{"prompt_tokens", metrics.prompt_tokens}, {"generated_tokens", metrics.generated_tokens},
                        {"prefill_ms", metrics.prefill_ms}, {"total_ms", metrics.total_ms},
                        {"ttft_ms", metrics.ttft_ms ? Json(*metrics.ttft_ms) : Json(nullptr)},
                        {"decode_tokens_per_second", metrics.decode_tokens_per_second ? Json(*metrics.decode_tokens_per_second) : Json(nullptr)}};
                    data["error"] = int(event.error);
                    const auto cache = engine_.expert_cache_metrics();
                    {
                        std::lock_guard<std::mutex> lock(mutex_);
                        if (cache) expert_cache_ = {{"hits", cache->hits}, {"misses", cache->misses},
                            {"uploaded_bytes", cache->uploaded_bytes}, {"prefetch_advice_bytes", cache->prefetch_advice_bytes},
                            {"scope", "process lifetime; completed owner operations"}, {"policy", "maya-aged-lfu"}};
                        last_request_ = {{"id", job->request.id}, {"state", name(event.state)},
                            {"metrics", data["metrics"]}, {"error", data["error"]}};
                        if (event.token) {
                            const auto stamp = now_ms();
                            if (first_token_ == 0) first_token_ = stamp;
                            token_times_.push_back(stamp);
                            while (token_times_.size() > 1 && token_times_.front() < stamp - 5000.0)
                                token_times_.pop_front();
                        }
                    }
                    const bool terminal = event.kind == EventKind::finished;
                    publish(job, data, terminal);
                    if (terminal) break;
                }
            } catch (const std::exception &) {
                // No backend call follows an unexpected application exception.
                if (backend_entered) { std::lock_guard<std::mutex> lock(mutex_); quarantined_ = true; }
                { std::lock_guard<std::mutex> lock(mutex_); last_request_["state"] = "failed"; }
                publish(job, {{"id", job->request.id}, {"type", "finished"}, {"state", "failed"},
                    {"error", backend_entered ? "application_failure" : "invalid_chat"}}, true);
            }
            {
                std::lock_guard<std::mutex> lock(mutex_);
                quarantined_ = quarantined_ || session.quarantined();
                active_.reset();
                if (stop_) return;
            }
        }
    }
    Engine & engine_;
    std::string source_;
    jinja::program program_;
    std::mutex mutex_;
    std::condition_variable changed_;
    std::shared_ptr<Job> active_;
    bool stop_ = false, quarantined_ = false;
    Json last_request_ = {{"state", "idle"}, {"metrics", Json::object()}};
    Json expert_cache_ = nullptr;
    double last_started_ = 0, first_token_ = 0;
    std::deque<double> token_times_;
    std::thread worker_;
};

int serve_http(Engine & engine, const std::string & assets,
               const std::string & chat_template, int port, bool demo, HardwareInfo hardware) {
    Service service(engine, chat_template);
    httplib::Server server;
    server.set_payload_max_length(1 << 20);
    server.set_read_timeout(10);
    server.set_write_timeout(10);
    std::mutex cpu_mutex;
    double last_cpu_wall = now_ms();
    std::clock_t last_cpu = std::clock();
    server.Get("/api/status", [&](const auto &, auto & response) {
        auto data = service.status();
        data["backend"] = demo ? "demo" : "model";
        data["model_loaded"] = !demo;
        data["server_epoch_ms"] = std::chrono::duration_cast<std::chrono::milliseconds>(
            std::chrono::system_clock::now().time_since_epoch()).count();
        Json process_cpu = nullptr;
        if (hardware.sample_process_cpu && hardware.logical_cpu_threads) {
            std::lock_guard<std::mutex> lock(cpu_mutex);
            const auto wall = now_ms();
            const auto cpu = std::clock();
            if (cpu != std::clock_t(-1) && last_cpu != std::clock_t(-1) && cpu >= last_cpu && wall > last_cpu_wall)
                process_cpu = std::min(100.0, 100000.0 * double(cpu - last_cpu) / CLOCKS_PER_SEC /
                    (wall - last_cpu_wall) / hardware.logical_cpu_threads);
            last_cpu = cpu; last_cpu_wall = wall;
        }
        data["hardware"] = {
            {"cpu", {{"name", hardware.cpu_name.empty() ? Json(nullptr) : Json(hardware.cpu_name)},
                {"logical_threads", hardware.logical_cpu_threads ? Json(hardware.logical_cpu_threads) : Json(nullptr)},
                {"app_usage_percent", process_cpu}}},
            {"gpu", {{"name", hardware.gpu_name.empty() ? Json(nullptr) : Json(hardware.gpu_name)},
                {"usage_percent", nullptr}, {"memory_sample", "driver report at startup"},
                {"total_bytes", hardware.gpu_total_bytes ? Json(*hardware.gpu_total_bytes) : Json(nullptr)},
                {"free_bytes", hardware.gpu_free_bytes ? Json(*hardware.gpu_free_bytes) : Json(nullptr)}}}};
        response.set_header("Cache-Control", "no-store");
        response.set_content(data.dump(), "application/json");
    });
    server.Post("/api/generate", [&](const auto & request, auto & response) {
        try {
            auto job = service.submit(Json::parse(request.body));
            if (!job) { response.status = 409; response.set_content("{\"error\":\"busy_or_quarantined\"}", "application/json"); return; }
            response.set_header("Cache-Control", "no-store");
            response.set_chunked_content_provider("text/event-stream", [job](std::size_t, httplib::DataSink & sink) {
                std::unique_lock<std::mutex> lock(job->mutex);
                job->changed.wait_for(lock, std::chrono::seconds(1), [&] { return job->done || !job->events.empty(); });
                if (job->events.empty()) {
                    if (job->done) { sink.done(); return true; }
                    lock.unlock(); return sink.write(": heartbeat\n\n", 13);
                }
                const auto event = std::move(job->events.front()); job->events.pop_front();
                const bool done = job->done && job->events.empty();
                lock.unlock(); job->changed.notify_all();
                if (!sink.write(event.data(), event.size())) return false;
                if (done) sink.done();
                return true;
            }, [job](bool) { job->cancel = true; job->changed.notify_all(); });
        } catch (const std::exception &) {
            response.status = 400;
            response.set_content("{\"error\":\"invalid_request\"}", "application/json");
        }
    });
    server.Post("/api/cancel", [&](const auto & request, auto & response) {
        try {
            const auto id = Json::parse(request.body).at("id").template get<std::string>();
            response.status = service.cancel(id) ? 202 : 404;
            response.set_content("{}", "application/json");
        } catch (...) { response.status = 400; }
    });
    if (!server.set_mount_point("/", assets)) throw std::runtime_error("Application assets not found");
    // During development, the preview is reachable only from this computer.
    return server.listen("127.0.0.1", port) ? 0 : 1;
}
} // namespace qwen_app
