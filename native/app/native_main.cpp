// SPDX-License-Identifier: MIT
// Compile during development; packaging and console execution remain deferred.
#include "http_app.h"
#include "llama_engine.h"
#include "ggml-cpu.h"
#include "gguf.h"
#include "nlohmann/json.hpp"

#include <cstdlib>
#include <chrono>
#include <fstream>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <string>
#include <thread>

using Json = nlohmann::json;
// A required link symbol prevents accidental use of an unpatched eager loader.
extern "C" bool llama_app_mmap_prefetch_disabled();

static std::string model_file(const std::string & receipt, const std::string & name) {
    if (name.empty() || name.find_first_of("/\\:") != std::string::npos || name == "." || name == "..")
        throw std::runtime_error("Receipt model files must use relative basenames");
    const auto separator = receipt.find_last_of("/\\");
    return separator == std::string::npos ? name : receipt.substr(0, separator + 1) + name;
}

static void inspect_container(const std::string & path, bool first) {
    std::unique_ptr<gguf_context, decltype(&gguf_free)> metadata(
        gguf_init_from_file(path.c_str(), {true, nullptr}), gguf_free);
    if (!metadata) throw std::runtime_error("GGUF metadata could not be read");
    for (std::int64_t i = 0; i < gguf_get_n_tensors(metadata.get()); ++i) {
        const auto type = gguf_get_tensor_type(metadata.get(), i);
        if (type != GGML_TYPE_BF16 && type != GGML_TYPE_F32)
            throw std::runtime_error("Only original BF16 or lossless F32 widening is accepted");
    }
    if (!first) return;
    const auto architecture = gguf_find_key(metadata.get(), "general.architecture");
    if (architecture < 0 || gguf_get_kv_type(metadata.get(), architecture) != GGUF_TYPE_STRING ||
        std::string(gguf_get_val_str(metadata.get(), architecture)) != "qwen4exp")
        throw std::runtime_error("Qwen4Exp model architecture is required");
    for (const auto * key : {"qwen4exp.ple.layers", "qwen4exp.ple.layer_multipliers",
                            "qwen4exp.ple.head_offsets", "qwen4exp.ple.head_vocab_sizes"}) {
        const auto index = gguf_find_key(metadata.get(), key);
        if (index < 0 || gguf_get_kv_type(metadata.get(), index) != GGUF_TYPE_ARRAY || !gguf_get_arr_n(metadata.get(), index))
            throw std::runtime_error("Required PLE metadata is missing");
        const auto type = gguf_get_arr_type(metadata.get(), index);
        if (std::string(key) != "qwen4exp.ple.layers" && type != GGUF_TYPE_INT64 && type != GGUF_TYPE_UINT64)
            throw std::runtime_error("PLE hash constants must remain exact 64-bit integers");
    }
}

int main(int argc, char ** argv) {
    if (argc != 5) {
        std::cerr << "Usage: app-native DEVELOPMENT_POLICY MODEL_RECEIPT WEB_ASSETS PORT\n";
        return 2;
    }
    llama_model * model = nullptr;
    llama_context * context = nullptr;
    std::unique_ptr<qwen_app::LlamaEngine> engine;
    try {
        std::ifstream policy_file(argv[1]);
        const auto policy = Json::parse(policy_file);
        if (policy.at("driver_qualification") != "complete" || !policy.at("console_operations_enabled").get<bool>())
            throw std::runtime_error("Console work is disabled while driver qualification is pending");
        std::ifstream receipt_file(argv[2]);
        const auto receipt = Json::parse(receipt_file);
        if (receipt.at("schema") != "ps5-qwen-bf16-conversion-v1" ||
            receipt.at("original_revision") != "de4b8e4d43b917e7706784d8bb445c9af86a3540" ||
            receipt.at("outtype") != "bf16" || !receipt.at("original_shards_verified").get<bool>() ||
            !receipt.at("files").is_array() || receipt.at("files").empty())
            throw std::runtime_error("Verified original BF16 conversion receipt required");
        // A receipt records host conversion provenance, not a fresh console hash
        // check. Deployment must independently verify every transferred file.
        bool first = true;
        for (const auto & file : receipt.at("files")) {
            inspect_container(model_file(argv[2], file.at("path").get<std::string>()), first); first = false;
        }
        const auto first_path = model_file(argv[2], receipt.at("files").at(0).at("path").get<std::string>());
        const int port = std::stoi(argv[4]);
        if (port < 1024 || port > 65535) throw std::invalid_argument("Invalid HTTP port");
        if (setenv("MESA_SHADER_CACHE_DISABLE", "true", 1) || setenv("LLAMA_APP_NO_MMAP_PREFETCH", "1", 1))
            throw std::runtime_error("Required cache policy could not be set");
        if (!llama_app_mmap_prefetch_disabled()) throw std::runtime_error("The streaming loader patch is required");
        llama_backend_init();
        model = llama_model_load_from_file(first_path.c_str(), qwen_app::streaming_model_params(ggml_backend_cpu_buffer_type()));
        if (!model) throw std::runtime_error("Model load failed; restart through the ordinary OS path");
        context = llama_init_from_model(model, qwen_app::streaming_context_params(4096, 512u << 20));
        if (!context) throw std::runtime_error("Context admission failed; restart through the ordinary OS path");
        engine = std::make_unique<qwen_app::LlamaEngine>(model, context);
        const auto * chat_template = llama_model_chat_template(model, nullptr);
        if (!chat_template || !*chat_template) throw std::runtime_error("The original chat template is required");
        const int result = qwen_app::serve_http(*engine, argv[3], chat_template, port, false);
        if (engine->failed()) throw std::runtime_error("Model resources retained after an uncertain backend result");
        engine.reset(); llama_free(context); context = nullptr; llama_model_free(model); model = nullptr;
        return result;
    } catch (const std::exception & error) {
        // No manual release or automatic retry after a failed native admission.
        // The owning process must remain available for ordinary OS shutdown.
        std::cerr << error.what() << '\n';
        if (model || context) {
            engine.release();
            // Keep the resource graph alive, without issuing more GPU operations.
            for (;;) std::this_thread::sleep_for(std::chrono::seconds(60));
        }
        return 1;
    }
}
