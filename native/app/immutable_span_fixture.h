// SPDX-License-Identifier: MIT
#pragma once
#include <nlohmann/json.hpp>
#include <cstdint>
namespace qwen_app {
nlohmann::json run_immutable_span_fixture(void(*stage)(const char*),std::uint64_t admitted_SELF_bytes);
}
