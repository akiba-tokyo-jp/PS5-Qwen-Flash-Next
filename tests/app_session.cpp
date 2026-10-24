// SPDX-License-Identifier: MIT
// This executable uses a deterministic fake backend. It never loads a model.
#include "session.h"

#include <cmath>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <type_traits>
#include <vector>

using namespace qwen_app;

static void check(bool condition, const char * message) {
    if (!condition) throw std::runtime_error(message);
}

struct FakeEngine : Engine {
    double now = 0;
    std::uint32_t prompt_tokens = 4;
    int tokenize_calls = 0, prefill_calls = 0, next_calls = 0, finish_calls = 0;
    std::string throw_in;
    std::vector<Token> tokens{{1, "Hello", false}, {2, " world", false}, {3, "!", false}};

    void maybe_throw(const char * operation) {
        if (throw_in == operation) throw std::runtime_error("Simulated backend failure");
    }
    std::uint32_t tokenize(const std::string &) override {
        ++tokenize_calls; now += 5; maybe_throw("tokenize"); return prompt_tokens;
    }
    void prefill(std::uint32_t) override {
        ++prefill_calls; now += 100; next_calls = 0; maybe_throw("prefill");
    }
    Token next() override {
        const int index = next_calls++;
        now += 20; maybe_throw("next");
        return index < int(tokens.size()) ? tokens[index] : Token{0, "", true};
    }
    void finish() override { ++finish_calls; maybe_throw("finish"); }
};

static Request request(std::uint32_t limit = 3) {
    return {"request-1", "An already rendered prompt", 16, limit};
}

static void streaming_and_metrics() {
    FakeEngine engine;
    Session session(engine, [&] { return engine.now; });
    check(session.begin(request()), "Request rejected");
    check(session.advance().kind == EventKind::prefilled, "Missing prefill event");
    check(!session.begin(request()), "A concurrent request was admitted");
    std::string text;
    for (int i = 0; i < 3; ++i) {
        auto event = session.advance();
        check(event.kind == EventKind::token && event.token.has_value(), "Missing token event");
        text += event.token->piece;
    }
    check(text == "Hello world!", "Token pieces were changed");
    check(session.state() == State::completed && engine.finish_calls == 1, "Output cap not enforced");
    check(engine.next_calls == 3, "An extra decode was performed");
    check(session.advance().kind == EventKind::finished && engine.finish_calls == 1, "Terminal event retried finish");
    const auto & metrics = session.metrics();
    check(metrics.prompt_tokens == 4 && metrics.generated_tokens == 3, "Token counts are incorrect");
    check(metrics.tokenize_ms == 5 && metrics.prefill_ms == 100, "Prefill includes unrelated work");
    check(metrics.ttft_ms && *metrics.ttft_ms == 125, "TTFT excludes prompt preparation");
    check(metrics.decode_ms == 40 && metrics.decode_tokens_per_second &&
        std::abs(*metrics.decode_tokens_per_second - 50) < 1e-9, "Decode rate includes TTFT or counts the first token twice");
    check(metrics.total_ms == 165, "Total duration is incorrect");
    check(session.begin(request(1)), "A completed backend cannot accept its next request");
    session.advance(); session.advance();
    check(session.metrics().generated_tokens == 1 && !session.metrics().decode_tokens_per_second,
          "One-token output invented a decode speed");
    check(*session.metrics().ttft_ms == 125, "Metrics leaked across requests");
}

static void cancellation_boundaries() {
    FakeEngine engine;
    Session session(engine, [&] { return engine.now; });
    session.begin(request()); session.cancel();
    check(session.advance().state == State::cancelled, "Early cancellation was ignored");
    check(!engine.tokenize_calls && !engine.prefill_calls && !engine.finish_calls,
          "An early cancellation touched the backend");
    session.begin(request()); session.advance(); session.advance(); session.cancel();
    check(session.advance().state == State::cancelled, "Token-boundary cancellation failed");
    check(engine.next_calls == 1 && engine.finish_calls == 1, "Cancellation decoded more output or skipped finish");
    session.advance(); session.cancel();
    check(engine.finish_calls == 1, "Cancellation repeated backend cleanup");
}

static void context_admission() {
    FakeEngine engine;
    Session session(engine);
    auto bad = request(); bad.rendered_prompt.clear();
    check(!session.begin(bad) && !engine.tokenize_calls, "Empty prompt reached the backend");
    engine.prompt_tokens = 15;
    check(session.begin(request()), "Basic admission failed");
    check(session.advance().error == Error::context_limit && !engine.prefill_calls, "Context overflow reached inference");
    engine.prompt_tokens = std::numeric_limits<std::uint32_t>::max();
    session.begin(request());
    check(session.advance().error == Error::context_limit && !engine.prefill_calls, "Context accounting overflowed");
    engine.prompt_tokens = 13;
    session.begin(request());
    check(session.advance().kind == EventKind::prefilled, "An exact context fit was rejected");
    session.cancel(); session.advance();
}

static void empty_and_fragmented_output() {
    FakeEngine engine;
    Session session(engine, [&] { return engine.now; });
    engine.tokens.clear(); session.begin(request()); session.advance();
    check(session.advance().state == State::completed, "End token did not complete");
    check(!session.metrics().ttft_ms && !session.metrics().decode_tokens_per_second &&
        !session.metrics().generated_tokens, "Empty output invented timing or token results");
    engine.tokens = {{1, std::string("\xe6", 1), false}, {2, std::string("\x97\xa5", 2), false}};
    session.begin(request()); session.advance();
    std::string bytes;
    while (session.state() == State::generating) {
        auto event = session.advance();
        if (event.token) bytes += event.token->piece;
    }
    check(bytes == std::string("\xe6\x97\xa5", 3), "UTF-8 token fragments were modified");
}

static void backend_failures_are_quarantined() {
    for (const auto * operation : {"tokenize", "prefill", "next", "finish"}) {
        FakeEngine engine; engine.throw_in = operation;
        Session session(engine);
        check(session.begin(request(1)), "Request rejected before backend failure");
        for (int i = 0; i < 3 && session.state() != State::failed; ++i) session.advance();
        check(session.quarantined() && session.error() == Error::backend_failure, "Backend failure did not quarantine");
        const int calls = engine.tokenize_calls + engine.prefill_calls + engine.next_calls + engine.finish_calls;
        check(!session.begin(request()), "An uncertain backend was reused");
        session.cancel(); session.advance();
        check(calls == engine.tokenize_calls + engine.prefill_calls + engine.next_calls + engine.finish_calls,
              "A backend operation was retried after a fault");
        check(engine.finish_calls == (std::string(operation) == "finish" ? 1 : 0), "Uncertain resources were released");
    }
}

int main() {
    static_assert(!std::is_copy_constructible<Session>::value, "A session must have one owner");
    try {
        streaming_and_metrics();
        cancellation_boundaries();
        context_admission();
        empty_and_fragmented_output();
        backend_failures_are_quarantined();
        std::cout << "Passed 5 application scenarios with a fake backend; no model or console execution\n";
    } catch (const std::exception & error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
