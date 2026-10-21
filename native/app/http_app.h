// SPDX-License-Identifier: MIT
#pragma once
#include "session.h"
#include <string>

namespace qwen_app {
// Uses one worker for model operations. HTTP threads only submit, stream, and
// request cancellation. The caller supplies an already admitted engine.
int serve_http(Engine & engine, const std::string & assets,
               const std::string & chat_template, int port, bool demo);
}
