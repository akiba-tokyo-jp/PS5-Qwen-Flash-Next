// SPDX-License-Identifier: MIT
// Real admission control with synthetic API readbacks; no GPU or learned model.
#include "moe_admission.h"
#include "model_integrity.h"
#include "ggml.h"
#include <algorithm>
#include <cstring>
#include <fstream>
#include <iostream>
#include <limits>
#include <stdexcept>

namespace {
struct ContractError : std::logic_error { using std::logic_error::logic_error; };
void check(bool value) { if (!value) throw ContractError("MoE ownership or shape contract failed"); }
int mode, tensors, computes, frees, reads, backends, supports, inputs;
std::size_t uploaded;
bool reference_done, synchronized, release_admitted, ids_uploaded, vector_uploaded;
ggml_context context; ggml_cgraph graph;
ggml_tensor weights, vector, ids, output;
constexpr std::int32_t expected_ids[] = {511, 0, 256, 17, 383, 1, 510, 127, 255, 42};
std::uint16_t synthetic_word(unsigned expert, unsigned row) { return 0x3d00 + (expert * 17 + row * 13) % 512; }
float decode(std::uint16_t word) { std::uint32_t bits = std::uint32_t(word) << 16; float value; std::memcpy(&value, &bits, 4); return value; }
void reset(int value) {
    mode = value; tensors = computes = frees = reads = backends = supports = inputs = 0; uploaded = 0;
    reference_done = synchronized = release_admitted = ids_uploaded = vector_uploaded = false;
}
void stage(const char * text) {
    if (!std::strcmp(text, "MoE_CPU_double_references_completed_before_compute_backend")) { check(backends == 0); reference_done = true; }
    if (!std::strcmp(text, "MoE_indexed_operation_supported_before_device_allocation")) check(supports == 1 && uploaded == 0);
    if (!std::strcmp(text, "MoE_synchronized_before_readback")) check(synchronized && reads == 0 && frees == 0);
    if (!std::strcmp(text, "MoE_all_numerical_gates_passed_before_release")) {
        check(mode == 0 && computes == 1 && reads == 1 && synchronized && frees == 0); release_admitted = true;
    }
    if (!std::strcmp(text, "MoE_numerical_failure_backing_retained")) check(frees == 0 && !release_admitted);
}
}
namespace qwen_app {
void verify_model_file(const std::string &, std::uint64_t bytes, const std::string & sha,
                       const std::function<void(std::uint64_t)> &, unsigned timeout) {
    check(bytes == 41943040 && sha == moe_fixture_sha256 && timeout == 30 && backends == 0);
    if (mode == 14) throw std::runtime_error("synthetic full-fixture SHA mismatch");
}
}
extern "C" {
std::size_t ggml_tensor_overhead() { return 64; }
std::size_t ggml_graph_overhead_custom(std::size_t n, bool grads) { check(n == 16 && !grads); return 256; }
ggml_context * ggml_init(ggml_init_params p) { check(p.mem_size == 768 && !p.mem_buffer && p.no_alloc); return mode == 10 ? nullptr : &context; }
ggml_tensor * ggml_new_tensor_3d(ggml_context * c, ggml_type type, std::int64_t width, std::int64_t height, std::int64_t depth) {
    check(c == &context && width == 2560); ++tensors;
    if (tensors == 1) { check(type == GGML_TYPE_BF16 && height == 16 && depth == 512); weights = {type, width, height, 1, depth}; return &weights; }
    check(tensors == 2 && type == GGML_TYPE_F32 && height == 1 && depth == 1); vector = {type, width, height, 2, depth}; return &vector;
}
ggml_tensor * ggml_new_tensor_2d(ggml_context * c, ggml_type type, std::int64_t width, std::int64_t height) {
    check(c == &context && ++tensors == 3 && type == GGML_TYPE_I32 && width == 10 && height == 1);
    ids = {type, width, height, 3}; return &ids;
}
ggml_tensor * ggml_mul_mat_id(ggml_context * c, ggml_tensor * a, ggml_tensor * b, ggml_tensor * i) {
    check(c == &context && a == &weights && b == &vector && i == &ids);
    output = {GGML_TYPE_F32, 16, 10, 4}; return &output;
}
void ggml_set_input(ggml_tensor * t) { check(t == &weights || t == &vector || t == &ids); ++inputs; }
void ggml_set_output(ggml_tensor * t) { check(t == &output && inputs == 3); }
ggml_cgraph * ggml_new_graph_custom(ggml_context * c, std::size_t n, bool grads) { check(c == &context && n == 16 && !grads); return &graph; }
void ggml_build_forward_expand(ggml_cgraph * g, ggml_tensor * t) { check(g == &graph && t == &output); }
float ggml_bf16_to_fp32(ggml_bf16_t value) { return decode(value.bits); }
ggml_backend_t ggml_backend_vk_init(std::size_t index) { check(index == 0 && reference_done); ++backends; return mode == 6 ? nullptr : &context; }
const char * ggml_backend_name(ggml_backend_t b) { check(b == &context); return "synthetic_MoE_API"; }
void * ggml_backend_get_device(ggml_backend_t b) { check(b == &context); return b; }
bool ggml_backend_dev_supports_op(void * b, const ggml_tensor * t) { check(b == &context && t == &output && uploaded == 0); ++supports; return mode != 1; }
ggml_backend_buffer_t ggml_backend_alloc_ctx_tensors(ggml_context * c, ggml_backend_t b) { check(c == &context && b == &context && supports == 1); return mode == 2 ? nullptr : &graph; }
void ggml_backend_tensor_set(ggml_tensor * t, const void * data, std::size_t offset, std::size_t bytes) {
    check(data && frees == 0 && computes == 0);
    if (t == &weights) {
        check(offset == uploaded && bytes == (8u << 20) && uploaded + bytes <= 41943040);
        const auto * words = static_cast<const std::uint16_t *>(data);
        for (std::size_t index : {std::size_t(0), bytes / 2 - 1}) {
            const auto element = (offset / 2 + index) / 2560;
            check(words[index] == synthetic_word(element / 16, element % 16));
        }
        if (mode == 11) throw std::runtime_error("synthetic upload refusal");
        uploaded += bytes;
    } else if (t == &vector) {
        check(uploaded == 41943040 && offset == 0 && bytes == 10240);
        const auto * values = static_cast<const float *>(data);
        for (unsigned k = 0; k < 2560; ++k) check(values[k] == float(int(k % 7) - 3) * .5f);
        vector_uploaded = true;
    } else {
        check(t == &ids && vector_uploaded && offset == 0 && bytes == 40 && !std::memcmp(data, expected_ids, 40));
        if (mode == 12) throw std::runtime_error("synthetic IDs upload refusal");
        ids_uploaded = true;
    }
}
ggml_status ggml_backend_graph_compute(ggml_backend_t b, ggml_cgraph * g) {
    check(b == &context && g == &graph && ids_uploaded && uploaded == 41943040 && computes == 0); ++computes;
    return mode == 3 ? GGML_STATUS_FAILED : GGML_STATUS_SUCCESS;
}
void ggml_backend_synchronize(ggml_backend_t b) { check(b == &context && computes == 1 && reads == 0); synchronized = true; }
void ggml_backend_tensor_get(const ggml_tensor * t, void * data, std::size_t offset, std::size_t bytes) {
    check(t == &output && synchronized && frees == 0 && offset == 0 && bytes == 640); ++reads;
    if (mode == 7) throw std::runtime_error("synthetic readback refusal");
    auto * values = static_cast<float *>(data);
    for (unsigned slot = 0; slot < 10; ++slot) for (unsigned row = 0; row < 16; ++row)
        values[slot * 16 + row] = -2.5f * decode(synthetic_word(expected_ids[slot], row));
    if (mode == 4) values[0] += .01f;
    if (mode == 5) values[159] = std::numeric_limits<float>::quiet_NaN();
    if (mode == 13) std::swap(values[0], values[16]);
}
void ggml_backend_buffer_free(ggml_backend_buffer_t b) { check(b == &graph && release_admitted); ++frees; }
void ggml_free(ggml_context * c) { check(c == &context && release_admitted); ++frees; }
void ggml_backend_free(ggml_backend_t b) { check(b == &context && release_admitted); ++frees; }
}
int main(int argc, char ** argv) {
    try {
        check(argc == 2);
        std::vector<std::uint16_t> bits(41943040 / 2);
        for (unsigned expert = 0; expert < 512; ++expert) for (unsigned row = 0; row < 16; ++row)
            std::fill_n(bits.begin() + (expert * 16 + row) * 2560, 2560, synthetic_word(expert, row));
        for (int scenario = 0; scenario <= 13; ++scenario) {
            reset(scenario); bool threw = false;
            if (mode == 8) bits.pop_back();
            if (mode == 9) bits.back() = 0x7fc0;
            try {
                auto result = qwen_app::admit_original_moe(bits, stage);
                check(mode == 0 || mode == 4 || mode == 5 || mode == 13);
                check(result.passed == (mode == 0) && result.metric.values == 160 && computes == 1 && reads == 1);
                check(frees == (mode == 0 ? 3 : 0));
            } catch (const ContractError &) { throw; } catch (const std::exception &) { threw = true; }
            check(threw == !(mode == 0 || mode == 4 || mode == 5 || mode == 13));
            if (mode != 0) check(frees == 0);
            if (mode == 1 || mode == 2 || mode == 6 || mode == 8 || mode == 9 || mode == 10 || mode == 11 || mode == 12) check(computes == 0);
            if (mode == 8) bits.push_back(synthetic_word(511, 15));
            if (mode == 9) bits.back() = synthetic_word(511, 15);
        }
        reset(0);
        { std::ofstream f(argv[1], std::ios::binary); f.write(reinterpret_cast<const char *>(bits.data()), bits.size() * 2); }
        check(qwen_app::load_original_moe_fixture(argv[1]) == bits);
        for (int scenario : {0, 9, 14}) {
            reset(scenario);
            { std::ofstream f(argv[1], std::ios::binary); if (mode == 9) { bits.back() = 0x7f80; f.write(reinterpret_cast<const char *>(bits.data()), bits.size() * 2); } else f.write("short", 5); }
            bool refused = false;
            try { qwen_app::load_original_moe_fixture(argv[1]); } catch (const ContractError &) { throw; } catch (const std::exception &) { refused = true; }
            check(refused && backends == 0);
        }
        std::cout << "MoE all512/top10 shapes, ordered IDs, broadcast, five bounded uploads, single graph, 160 readbacks and failure retention passed; synthetic API only\n";
    } catch (const std::exception & e) { std::cerr << e.what() << '\n'; return 1; }
}
