// SPDX-License-Identifier: MIT
// These are API stubs for adapter control-flow checks, never model inference.
#include "llama_engine.h"
#include "expert_policy.h"
#include <cstring>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <vector>

struct llama_model {};
struct llama_context {};
struct llama_vocab {};
struct llama_batch_ext {};

static llama_vocab vocabulary;
static int decodes = 0, synchronizes = 0, clears = 0, freed = 0, samples = 0;
static bool decode_failure = false;
static float logits[] = {1, 2, 3, 4};
static std::vector<int> decoded;
static std::vector<std::string> stages;
static void observe(const char * value) { stages.emplace_back(value); }
static void check(bool value, const char * message) { if (!value) throw std::runtime_error(message); }

extern "C" {
void llama_app_expert_counters(llama_app_expert_stats * result) { *result = {7, 3, 4096, 8192}; }
llama_model_params llama_model_default_params() { return {}; }
llama_context_params llama_context_default_params() { return {}; }
const llama_vocab * llama_model_get_vocab(const llama_model *) { return &vocabulary; }
llama_batch_ext * llama_batch_ext_init(llama_context *) { return new llama_batch_ext; }
void llama_batch_ext_free(llama_batch_ext * batch) { ++freed; delete batch; }
llama_sampler * llama_sampler_init_greedy() { return reinterpret_cast<llama_sampler *>(1); }
void llama_sampler_free(llama_sampler *) { ++freed; }
void llama_sampler_reset(llama_sampler *) { samples = 0; }
int32_t llama_tokenize(const llama_vocab *, const char *, int32_t, llama_token * tokens, int32_t size, bool, bool) {
    if (!tokens || size < 3) return -3;
    tokens[0] = 11; tokens[1] = 12; tokens[2] = 13; return 3;
}
void llama_batch_ext_clear(llama_batch_ext *) {}
int32_t llama_batch_ext_add_token(llama_batch_ext *, llama_seq_id, llama_token token) { decoded.push_back(token); return 0; }
bool llama_batch_ext_set_pos(llama_batch_ext *, int32_t, const llama_pos *) { return true; }
bool llama_batch_ext_set_output_logits(llama_batch_ext *, int32_t, bool) { return true; }
int32_t llama_process(llama_context *, llama_process_type, llama_batch_ext *) { ++decodes; return decode_failure ? -1 : 0; }
void llama_synchronize(llama_context *) { ++synchronizes; }
uint32_t llama_n_ctx(const llama_context *) { return 64; }
llama_memory_t llama_get_memory(const llama_context *) { return nullptr; }
void llama_memory_clear(llama_memory_t, bool) { ++clears; }
int32_t llama_vocab_n_tokens(const llama_vocab *) { return 4; }
float * llama_get_logits_ith(llama_context *, int32_t) { return logits; }
llama_token llama_sampler_sample(llama_sampler *, llama_context *, int32_t) { return ++samples; }
bool llama_vocab_is_eog(const llama_vocab *, llama_token token) { return token == 3; }
int32_t llama_token_to_piece(const llama_vocab *, llama_token, char * buffer, int32_t size, int32_t, bool) {
    if (size < 300) return -300;
    std::memset(buffer, 'x', 300); return 300;
}
}

int main() {
    try {
        const auto buffer = reinterpret_cast<ggml_backend_buffer_type_t>(1);
        const auto model_params = qwen_app::streaming_model_params(buffer);
        check(model_params.load_mode == LLAMA_LOAD_MODE_MMAP && model_params.lazy_mode == LLAMA_LAZY_MODE_ON,
              "Required mapped and lazy PLE modes were not selected");
        check(model_params.tensor_buft_overrides[0].buft == buffer && !model_params.tensor_buft_overrides[1].pattern,
              "Expert override is not bounded and terminated");
        const auto context_params = qwen_app::streaming_context_params(64, 512 << 20);
        check(context_params.n_ubatch == 1 && context_params.n_batch == 1 && context_params.moe_cache_size == (512u << 20),
              "Streaming budgets were changed");
        llama_model model; llama_context context;
        {
            qwen_app::LlamaEngine engine(&model, &context);
            engine.set_stage_observer(observe);
            check(engine.expert_cache_metrics()->hits == 7 && engine.expert_cache_metrics()->uploaded_bytes == 4096,
                  "Cache counters did not come from the engine patch");
            check(engine.tokenize("test") == 3, "Adapter tokenization failed");
            engine.prefill(64);
            check(stages.back()=="inference_prefill_completed", "Completed prefill stage is missing");
            check(decodes == 3 && synchronizes == 3, "Prefill did not use synchronous single-token batches");
            check(engine.next().piece.size() == 300 && decodes == 3, "First sample unnecessarily decoded or truncated a piece");
            engine.next(); check(decodes == 4 && decoded.back() == 1, "Previous sampled token was not decoded");
            check(engine.next().end_of_generation, "End-of-generation was not detected");
            engine.finish();
        }
        check(freed == 2 && clears == 2, "Healthy adapter did not clear and release its owned objects");
        const int healthy_freed = freed;
        {
            qwen_app::LlamaEngine engine(&model, &context);
            engine.tokenize("test"); engine.prefill(64);
            logits[0] = std::numeric_limits<float>::quiet_NaN();
            try { engine.next(); throw std::logic_error("Non-finite logits accepted"); }
            catch (const std::runtime_error &) {}
        }
        check(freed == healthy_freed, "Uncertain adapter resources were freed");
        logits[0] = 1; decode_failure = true;
        stages.clear();
        {
            qwen_app::LlamaEngine engine(&model, &context);
            engine.set_stage_observer(observe);
            engine.tokenize("test");
            try { engine.prefill(64); throw std::logic_error("Decode failure accepted"); }
            catch (const std::runtime_error &) {}
        }
        check(stages.back()=="inference_before_decode_call", "Failed decode incorrectly reported completion");
        check(freed == healthy_freed, "Failed prefill released uncertain resources");
        std::cout << "Adapter API-stub scenarios passed; no model was loaded\n";
    } catch (const std::exception & error) { std::cerr << error.what() << '\n'; return 1; }
}
