// SPDX-License-Identifier: MIT
#pragma once
#include "session.h"
#include <chrono>
#include <cmath>
#include <stdexcept>
#include <utility>
#include <vector>

namespace qwen_app {
inline constexpr std::uint32_t first_context_tokens = 256;
inline constexpr std::uint32_t first_prompt_tokens = 64;
inline constexpr std::uint32_t first_output_tokens = 32;
inline constexpr unsigned first_generation_seconds = 3600;
inline constexpr const char * first_generation_prompt =
    "What is 2 + 2? Reply with only the answer.";

struct FirstGenerationResult {
    std::string stop_reason;
    Metrics metrics;
    std::vector<std::int32_t> token_ids;
    // Token pieces may split UTF-8 characters. Persist these bytes losslessly.
    std::vector<unsigned char> output_bytes;
    bool request_reset_completed = false;
};

// Owns one attempt, not the engine. Native admission must precede construction.
// Every callback is synchronous: failed persistence prevents further submission.
// No failure invokes finish(), frees backing or retries an uncertain operation.
class FirstGeneration {
public:
    using Clock = std::function<double()>;
    using PersistIntent = std::function<void(const Request &)>;
    using PersistToken = std::function<void(const Token &, const Metrics &)>;
    using Stage = std::function<void(const char *)>;
    explicit FirstGeneration(Engine & engine, Clock clock = {})
        : engine_(engine), clock_(clock ? std::move(clock) : Clock([] {
            return std::chrono::duration<double, std::milli>(
                std::chrono::steady_clock::now().time_since_epoch()).count();
          })) {}
    FirstGeneration(const FirstGeneration &) = delete;
    FirstGeneration & operator=(const FirstGeneration &) = delete;

    void require_time() {
        if (!active_) throw std::logic_error("First-generation work is outside its active attempt");
        const auto now = clock_();
        if (!std::isfinite(now) || now < last_clock_ || now - started_ > first_generation_seconds * 1000.0)
            throw std::runtime_error("First-generation deadline or monotonic clock admission failed");
        last_clock_ = now;
    }

    const FirstGenerationResult & run(Request request, const PersistIntent & intent,
                                      const PersistToken & token, const Stage & stage) {
        if (attempted_) throw std::logic_error("First generation permits only one attempt");
        attempted_ = true;
        if (!intent || !token || !stage || request.id.empty() || request.id.size() > 128 ||
            request.id.find_first_not_of("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_") != std::string::npos ||
            request.rendered_prompt.empty() || request.rendered_prompt.size() > 16384 ||
            request.rendered_prompt.find('\0') != std::string::npos ||
            request.context_tokens != first_context_tokens || request.max_output_tokens != first_output_tokens)
            throw std::invalid_argument("The bounded first-generation request and durable observers are required");
        started_ = last_clock_ = clock_();
        if (!std::isfinite(started_)) throw std::runtime_error("A finite monotonic clock is required");
        active_ = true;
        try {
            intent(request);
            require_time(); stage("first_generation_intent_persisted");
            const auto tokenize_started = last_clock_;
            result_.metrics.prompt_tokens = engine_.tokenize(request.rendered_prompt);
            require_time();
            result_.metrics.tokenize_ms = last_clock_ - tokenize_started;
            if (!result_.metrics.prompt_tokens || result_.metrics.prompt_tokens > first_prompt_tokens ||
                result_.metrics.prompt_tokens + first_output_tokens > first_context_tokens)
                throw std::runtime_error("Rendered first-generation prompt exceeds its token bound");
            stage("first_generation_before_bounded_prefill"); require_time();
            const auto prefill_started = last_clock_;
            engine_.prefill(first_context_tokens);
            require_time();
            result_.metrics.prefill_ms = last_clock_ - prefill_started;
            stage("first_generation_prefill_completed");
            double first_token_at = 0;
            for (std::uint32_t i = 0; i < first_output_tokens; ++i) {
                require_time();
                const auto value = engine_.next();
                require_time();
                if (value.id < 0) throw std::runtime_error("First-generation token ID is invalid");
                if (value.end_of_generation) { result_.stop_reason = "end_of_generation"; break; }
                if (value.piece.size() > 65536 - result_.output_bytes.size())
                    throw std::runtime_error("First-generation output exceeds its byte bound");
                result_.token_ids.push_back(value.id);
                result_.output_bytes.insert(result_.output_bytes.end(), value.piece.begin(), value.piece.end());
                auto & metrics = result_.metrics;
                metrics.generated_tokens = static_cast<std::uint32_t>(result_.token_ids.size());
                if (metrics.generated_tokens == 1) {
                    first_token_at = last_clock_;
                    metrics.ttft_ms = last_clock_ - started_;
                } else {
                    metrics.decode_ms = last_clock_ - first_token_at;
                    if (metrics.decode_ms > 0)
                        metrics.decode_tokens_per_second = 1000.0 * (metrics.generated_tokens - 1) / metrics.decode_ms;
                }
                metrics.total_ms = last_clock_ - started_;
                token(value, metrics);
                stage("first_generation_token_persisted");
            }
            if (result_.stop_reason.empty()) result_.stop_reason = "output_token_limit";
            require_time(); stage("first_generation_before_completed_request_reset"); require_time();
            engine_.finish();
            result_.request_reset_completed = true;
            require_time(); result_.metrics.total_ms = last_clock_ - started_;
            stage("first_generation_request_reset_completed");
            active_ = false;
            return result_;
        } catch (...) { active_ = false; throw; }
    }
private:
    Engine & engine_;
    Clock clock_;
    bool attempted_ = false, active_ = false;
    double started_ = 0, last_clock_ = 0;
    FirstGenerationResult result_;
};
}
