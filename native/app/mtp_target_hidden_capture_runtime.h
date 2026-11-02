// SPDX-License-Identifier: MIT
#pragma once
#include "mtp_target_hidden_capture.h"
struct llama_context;
namespace qwen_app {
void bind_mtp_target_hidden_capture(llama_context*);
const MtpTargetHiddenCapture<>*mtp_target_hidden_capture()noexcept;
void retire_mtp_target_hidden_capture_after_all_owners();
}
