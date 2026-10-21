// SPDX-License-Identifier: MIT
#pragma once

#include <cstdint>
#include <functional>
#include <optional>
#include <string>

namespace qwen_app {

enum class State { idle, preparing, generating, completed, cancelled, failed };
enum class Error { none, invalid_request, context_limit, backend_failure };
enum class EventKind { prefilled, token, finished };

struct Request {
    std::string id;
    // The frontend must apply the model's exact chat template before submission.
    std::string rendered_prompt;
    std::uint32_t context_tokens = 2048;
    std::uint32_t max_output_tokens = 128;
};

struct Token {
    std::int32_t id = 0;
    std::string piece;
    bool end_of_generation = false;
};

struct Metrics {
    std::uint32_t prompt_tokens = 0;
    std::uint32_t generated_tokens = 0;
    double tokenize_ms = 0;
    double prefill_ms = 0;
    std::optional<double> ttft_ms;
    double decode_ms = 0;
    std::optional<double> decode_tokens_per_second;
    double total_ms = 0;
};

struct Event {
    EventKind kind = EventKind::finished;
    std::optional<Token> token;
    State state = State::idle;
    Error error = Error::none;
};

struct ExpertCacheMetrics {
    std::uint64_t hits = 0, misses = 0, uploaded_bytes = 0, prefetch_advice_bytes = 0;
};

// Calls run on one owner thread. A backend may return only after its work has
// completed; cancellation must never free or interrupt uncertain GPU work.
class Engine {
public:
    virtual ~Engine() = default;
    // Tokenization must not allocate inference state or perform learned work.
    virtual std::uint32_t tokenize(const std::string & rendered_prompt) = 0;
    virtual void prefill(std::uint32_t context_tokens) = 0;
    virtual Token next() = 0;
    // Called only after successful, synchronous work at a request boundary.
    virtual void finish() = 0;
    // Read on the engine owner after a completed operation; demos report absent.
    virtual std::optional<ExpertCacheMetrics> expert_cache_metrics() const { return {}; }
};

// One session owns one backend's request state. Its frontend serializes these
// methods; cancel requests from another thread must be queued to that owner.
class Session {
public:
    using Clock = std::function<double()>; // monotonic milliseconds
    explicit Session(Engine & engine, Clock clock = {});
    Session(const Session &) = delete;
    Session & operator=(const Session &) = delete;
    bool begin(Request request);
    Event advance();
    void cancel();
    State state() const { return state_; }
    Error error() const { return error_; }
    bool quarantined() const { return quarantined_; }
    const Metrics & metrics() const { return metrics_; }
    const std::string & request_id() const { return request_.id; }

private:
    Event event(EventKind kind, std::optional<Token> token = {}) const;
    Event fail_backend();
    Event complete(State state);
    void stamp_total();
    Engine & engine_;
    Clock clock_;
    Request request_;
    Metrics metrics_;
    State state_ = State::idle;
    Error error_ = Error::none;
    bool cancel_requested_ = false;
    bool engine_started_ = false;
    bool quarantined_ = false;
    double accepted_at_ = 0;
    double first_token_at_ = 0;
};

} // namespace qwen_app
