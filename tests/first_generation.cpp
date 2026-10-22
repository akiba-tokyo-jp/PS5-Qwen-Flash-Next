// SPDX-License-Identifier: MIT
// Control-flow tests use a fake engine, never model inference.
#include "first_generation_policy.h"
#include "validation_policy.h"
#include "startup.h"
#include <fstream>
#include <iostream>
#include <limits>

using namespace qwen_app;
using Json = nlohmann::json;
static void check(bool value, const char * message) { if (!value) throw std::runtime_error(message); }
template<class F> static void reject(F action) {
    bool refused = false; try { action(); } catch (const std::exception &) { refused = true; }
    check(refused, "An invalid first-generation operation was admitted");
}
struct FakeEngine final : Engine {
    double now = 100;
    unsigned prompt_count = 3, tokenizations = 0, prefills = 0, nexts = 0, finishes = 0;
    unsigned eog_at = 3;
    double prefill_time = 20, token_time = 5;
    bool fail_prefill = false, fail_next = false, fail_finish = false, oversize_piece = false;
    std::uint32_t tokenize(const std::string &) override { ++tokenizations; now += 10; return prompt_count; }
    void prefill(std::uint32_t context) override {
        check(context == first_context_tokens, "Context bound changed"); ++prefills; now += prefill_time;
        if (fail_prefill) throw std::runtime_error("Synthetic prefill failure");
    }
    Token next() override {
        ++nexts; now += token_time;
        if (fail_next) throw std::runtime_error("Synthetic decode failure");
        return {static_cast<std::int32_t>(nexts), oversize_piece ? std::string(65537, 'x') :
            (nexts == 1 ? std::string("\xe3\x81", 2) : std::string("\x82", 1)), nexts == eog_at};
    }
    void finish() override { ++finishes; now += 2; if (fail_finish) throw std::runtime_error("Synthetic reset failure"); }
};
static Request request() { return {"0123456789abcdef0123456789abcdef", "rendered original template", 256, 32}; }
static const auto intent = [](const Request &) {};
static const auto token = [](const Token &, const Metrics &) {};
static const auto stage = [](const char *) {};

static Json valid_policy() {
    return {{"native_first_generation_validation", {
        {"schema", "ps5-qwen-first-generation-v1"},
        {"preceding_moe_SELF_sha256", "0b187cac25c3e322bd4244474a935d191ce85b7bcbb3d2559ead26f05198d057"},
        {"driver_revision", "872cc1264ad8ba5d6b888b092968fa5858a38c58"}, {"profile", "cumulative-idle"},
        {"native_archive_sha256", "b57fe26e969940d147be05c1ffae830503d4865877281dffe03af32328f49925"},
        {"original_revision", "de4b8e4d43b917e7706784d8bb445c9af86a3540"},
        {"preceding_moe_passed", true}, {"original_restoration_and_numerical_readmission_passed", true},
        {"fresh_idle_session_bound_by_launcher", true}, {"complete_transfer_and_data_lease_bound_by_launcher", true},
        {"complete_v2_model_receipt_required", true}, {"native_integrity_and_mapping_before_backend_required", true},
        {"persistent_caches_enabled", false}, {"external_requests_enabled", false}, {"maximum_requests", 1},
        {"maximum_context_tokens", 256}, {"maximum_prompt_tokens", 64}, {"maximum_output_tokens", 32},
        {"maximum_generation_seconds", 3600}, {"maximum_verification_seconds", 7200},
        {"maximum_model_load_seconds", 1200}, {"maximum_context_creation_seconds", 600},
        {"maximum_mapped_bytes", 512ull << 30}, {"prompt", first_generation_prompt}, {"enable_thinking", false},
        {"candidate_SELF_sha256", std::string(64, 'a')}, {"model_receipt_sha256", std::string(64, 'b')},
        {"candidate_SELF_bytes", 58000000}, {"model_receipt_bytes", 200000},
        {"run_id", "0123456789abcdef0123456789abcdef"}}}};
}

int main(int argc, char ** argv) {
    try {
        check(argc == 2, "Supply an owned temporary startup path");
        {
            FakeEngine engine; FirstGeneration run(engine, [&] { return engine.now; });
            unsigned persisted = 0; bool intent_before_engine = false;
            const auto & result = run.run(request(), [&](const auto &) { intent_before_engine = !engine.tokenizations; },
                [&](const auto &, const auto &) { ++persisted; }, stage);
            check(intent_before_engine && persisted == 2 && engine.nexts == 3 && engine.finishes == 1,
                "Durable intent/token ordering or EOG completion failed");
            check(result.stop_reason == "end_of_generation" && result.request_reset_completed &&
                result.output_bytes == std::vector<unsigned char>({0xe3, 0x81, 0x82}) && result.token_ids.size() == 2,
                "Split UTF-8 bytes or exact tokens were lost");
            check(*result.metrics.ttft_ms == 35 && *result.metrics.decode_tokens_per_second == 200 &&
                result.metrics.total_ms == 47, "Actual request timing was misreported");
            reject([&] { run.run(request(), intent, token, stage); });
            check(engine.nexts == 3, "A second attempt submitted work");
        }
        {
            FakeEngine engine; engine.eog_at = 100; FirstGeneration run(engine, [&] { return engine.now; });
            const auto & result = run.run(request(), intent, token, stage);
            check(engine.nexts == 32 && engine.finishes == 1 && result.stop_reason == "output_token_limit",
                "Output cap did not terminate before a 33rd token");
        }
        {
            FakeEngine engine; engine.eog_at = 1; FirstGeneration run(engine, [&] { return engine.now; });
            const auto & result = run.run(request(), intent, token, stage);
            check(result.output_bytes.empty() && !result.metrics.ttft_ms && !result.metrics.decode_tokens_per_second,
                "An empty EOG result fabricated text or speed");
        }
        for (const unsigned count : {0u, 65u, 100000u}) {
            FakeEngine engine; engine.prompt_count = count; FirstGeneration run(engine, [&] { return engine.now; });
            reject([&] { run.run(request(), intent, token, stage); });
            check(!engine.prefills && !engine.nexts && !engine.finishes, "Oversized prompt reached learned work");
        }
        for (int failure = 0; failure < 8; ++failure) {
            FakeEngine engine; FirstGeneration run(engine, [&] { return engine.now; });
            engine.fail_prefill = failure == 0; engine.fail_next = failure == 1; engine.fail_finish = failure == 2;
            engine.oversize_piece = failure == 3;
            if (failure == 4) engine.token_time = 3600001;
            if (failure == 5) engine.prefill_time = -5;
            reject([&] { run.run(request(), [&](const auto &) {
                    if (failure == 6) throw std::runtime_error("Intent persistence failed");
                }, [&](const auto &, const auto &) {
                    if (failure == 7) throw std::runtime_error("Token persistence failed");
                }, stage); });
            if (failure != 2) check(!engine.finishes, "Failure attempted engine reset");
            if (failure == 6) check(!engine.tokenizations && !engine.prefills, "Failed intent reached the engine");
            if (failure == 7) check(engine.nexts == 1, "Failed token persistence submitted another token");
            const auto before = engine.nexts;
            reject([&] { run.run(request(), intent, token, stage); });
            check(engine.nexts == before, "A failed attempt was retried");
        }
        {
            FakeEngine engine; FirstGeneration run(engine, [&] { return engine.now; });
            auto invalid = request(); invalid.context_tokens = 4096;
            reject([&] { run.run(invalid, intent, token, stage); });
            check(!engine.tokenizations, "Unadmitted context reached the engine");
        }
        {
            FakeEngine engine; FirstGeneration run(engine, [] { return std::numeric_limits<double>::quiet_NaN(); });
            reject([&] { run.run(request(), intent, token, stage); });
            check(!engine.tokenizations, "Invalid clock reached the engine");
        }
        auto valid = valid_policy();
        require_native_validation_policy(valid, "first-generation-validation", false);
        reject([&] { require_native_validation_policy(valid, "first-generation-validation", true); });
        reject([&] { require_native_validation_policy(valid, "inference", false); });
        unsigned rejected_fields = 0;
        for (auto item = valid.at("native_first_generation_validation").begin();
             item != valid.at("native_first_generation_validation").end(); ++item) {
            for (int variant = 0; variant < 3; ++variant) {
                auto bad = valid; auto & gate = bad["native_first_generation_validation"];
                if (variant == 0) gate.erase(item.key());
                else if (variant == 1) gate[item.key()] = nullptr;
                else if (item.value().is_boolean()) gate[item.key()] = item.value().get<bool>() ? 1 : 0;
                else if (item.value().is_number_integer()) gate[item.key()] = item.value().get<double>();
                else gate[item.key()] = "incorrect";
                reject([&] { require_native_validation_policy(bad, "first-generation-validation", false); });
                ++rejected_fields;
            }
        }
        const std::string path = argv[1];
        char executable[] = "app-native"; std::vector<char> owned(path.begin(), path.end()); owned.push_back(0);
        char * arguments[] = {executable, owned.data()};
        Json config{{"schema", "ps5-qwen-app-v1"}, {"development_policy", "policy"},
            {"model_receipt", "receipt"}, {"web_assets", "web"},
            {"mode", "first-generation-validation"}, {"native_display", false}};
        auto save = [&] { std::ofstream output(path); output << config; check(bool(output), "Startup fixture write failed"); };
        save(); const auto startup = read_startup(2, arguments);
        check(startup.first_generation_validation && !startup.model_validation && !startup.moe_validation &&
            !startup.monitor_validation && !startup.native_display, "First-generation startup is not isolated");
        config["native_display"] = true; save(); reject([&] { read_startup(2, arguments); });
        config["native_display"] = false; config["weight_fixture"] = "/app0/qwen-runtime/original-moe-fixture.bf16";
        save(); reject([&] { read_startup(2, arguments); });
        std::cout << "First-generation limits, persistence failures, single-attempt semantics, timing, startup and "
                  << rejected_fields << " malformed policy fields passed; no model/console access\n";
    } catch (const std::exception & error) { std::cerr << error.what() << '\n'; return 1; }
}
