// SPDX-License-Identifier: MIT
#pragma once
#include <cstdint>
#include <array>
#include <functional>
#include <string>
namespace qwen_app {
std::string sha256_metadata_bytes(const std::string & bytes);
// Hash an already completed CPU-visible F32 logit array without copying it.
// This adds no tensor transfer or model operation.
std::array<std::uint8_t,32> model_logit_fingerprint(const float *,std::size_t count);
// Streaming integrity verification uses a fixed 1 MiB buffer and performs no
// model evaluation, mapping, backend initialization or GPU allocation.
void verify_model_file(const std::string & path, std::uint64_t bytes, const std::string & expected_sha256,
                       const std::function<void(std::uint64_t)> & progress, unsigned timeout_seconds=7200);
}
