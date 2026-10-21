// SPDX-License-Identifier: MIT
#pragma once
#include "session.h"
#include <string>
#include <optional>

namespace qwen_app {
struct HardwareInfo {
    std::string cpu_name;
    std::string gpu_name;
    unsigned logical_cpu_threads = 0;
    bool sample_process_cpu = false;
    std::optional<std::uint64_t> gpu_total_bytes;
    std::optional<std::uint64_t> gpu_free_bytes;
};
// Uses one worker for model operations. HTTP threads only submit, stream, and
// request cancellation. The caller supplies an already admitted engine.
int serve_http(Engine & engine, const std::string & assets,
               const std::string & chat_template, int port, bool demo, HardwareInfo hardware = {});
}
