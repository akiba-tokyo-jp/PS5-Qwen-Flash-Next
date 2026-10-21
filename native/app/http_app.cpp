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

namespace qwen_app {
using Json = nlohmann::json;

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
        return {{"busy", bool(active_)}, {"quarantined", quarantined_}};
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
                    const bool terminal = event.kind == EventKind::finished;
                    publish(job, data, terminal);
                    if (terminal) break;
                }
            } catch (const std::exception &) {
                // No backend call follows an unexpected application exception.
                if (backend_entered) { std::lock_guard<std::mutex> lock(mutex_); quarantined_ = true; }
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
    std::thread worker_;
};

int serve_http(Engine & engine, const std::string & assets,
               const std::string & chat_template, int port, bool demo) {
    Service service(engine, chat_template);
    httplib::Server server;
    server.set_payload_max_length(1 << 20);
    server.set_read_timeout(10);
    server.set_write_timeout(10);
    server.Get("/api/status", [&](const auto &, auto & response) {
        auto data = service.status();
        data["backend"] = demo ? "demo" : "model";
        data["model_loaded"] = !demo;
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
