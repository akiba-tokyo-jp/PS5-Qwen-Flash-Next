// SPDX-License-Identifier: MIT
#include "session.h"

#include <chrono>
#include <utility>

namespace qwen_app {

static double monotonic_ms() {
    return std::chrono::duration<double, std::milli>(
        std::chrono::steady_clock::now().time_since_epoch()).count();
}

Session::Session(Engine & engine, Clock clock)
    : engine_(engine), clock_(clock ? std::move(clock) : Clock(monotonic_ms)) {}

bool Session::begin(Request request) {
    if (state_ == State::preparing || state_ == State::generating || quarantined_) {
        return false;
    }
    request_ = std::move(request);
    metrics_ = {};
    error_ = Error::none;
    cancel_requested_ = false;
    engine_started_ = false;
    accepted_at_ = clock_();
    first_token_at_ = 0;
    if (request_.id.empty() || request_.rendered_prompt.empty() || !request_.context_tokens ||
        !request_.max_output_tokens || request_.max_output_tokens >= request_.context_tokens) {
        error_ = Error::invalid_request;
        state_ = State::failed;
        stamp_total();
        return false;
    }
    state_ = State::preparing;
    return true;
}

void Session::cancel() {
    if (state_ == State::preparing || state_ == State::generating) {
        cancel_requested_ = true;
    }
}

void Session::stamp_total() {
    metrics_.total_ms = clock_() - accepted_at_;
}

Event Session::event(EventKind kind, std::optional<Token> token) const {
    return {kind, std::move(token), state_, error_};
}

Event Session::fail_backend() {
    // Completion is uncertain after a backend exception. Keep its resource graph
    // intact and refuse future requests; no finish, retry or reset is attempted.
    quarantined_ = true;
    state_ = State::failed;
    error_ = Error::backend_failure;
    stamp_total();
    return event(EventKind::finished);
}

Event Session::complete(State state) {
    if (engine_started_) {
        try {
            engine_.finish();
        } catch (...) {
            return fail_backend();
        }
        engine_started_ = false;
    }
    state_ = state;
    stamp_total();
    return event(EventKind::finished);
}

Event Session::advance() {
    if (state_ != State::preparing && state_ != State::generating) {
        return event(EventKind::finished);
    }
    if (cancel_requested_) {
        return complete(State::cancelled);
    }
    if (state_ == State::preparing) {
        const auto tokenize_start = clock_();
        try {
            metrics_.prompt_tokens = engine_.tokenize(request_.rendered_prompt);
        } catch (...) {
            return fail_backend();
        }
        metrics_.tokenize_ms = clock_() - tokenize_start;
        if (!metrics_.prompt_tokens ||
            std::uint64_t(metrics_.prompt_tokens) + request_.max_output_tokens > request_.context_tokens) {
            error_ = Error::context_limit;
            state_ = State::failed;
            stamp_total();
            return event(EventKind::finished);
        }
        const auto prefill_start = clock_();
        engine_started_ = true;
        try {
            engine_.prefill(request_.context_tokens);
        } catch (...) {
            return fail_backend();
        }
        metrics_.prefill_ms = clock_() - prefill_start;
        state_ = State::generating;
        stamp_total();
        return event(EventKind::prefilled);
    }
    Token token;
    try {
        token = engine_.next();
    } catch (...) {
        return fail_backend();
    }
    if (token.end_of_generation) {
        return complete(State::completed);
    }
    const auto now = clock_();
    ++metrics_.generated_tokens;
    if (metrics_.generated_tokens == 1) {
        first_token_at_ = now;
        metrics_.ttft_ms = now - accepted_at_;
    } else {
        metrics_.decode_ms = now - first_token_at_;
        if (metrics_.decode_ms > 0) {
            metrics_.decode_tokens_per_second =
                1000.0 * (metrics_.generated_tokens - 1) / metrics_.decode_ms;
        }
    }
    if (metrics_.generated_tokens == request_.max_output_tokens) {
        const auto terminal = complete(State::completed);
        if (terminal.error != Error::none) {
            return terminal;
        }
    }
    stamp_total();
    return event(EventKind::token, std::move(token));
}

} // namespace qwen_app
