// SPDX-License-Identifier: MIT
#pragma once
#include <cstdint>
#include <functional>
#include <string>
namespace qwen_app {
std::string sha256_metadata_bytes(const std::string & bytes);
// Streaming integrity verification uses a fixed 1 MiB buffer and performs no
// model evaluation, mapping, backend initialization or GPU allocation.
void verify_model_file(const std::string & path, std::uint64_t bytes, const std::string & expected_sha256,
                       const std::function<void(std::uint64_t)> & progress, unsigned timeout_seconds=7200);
}
