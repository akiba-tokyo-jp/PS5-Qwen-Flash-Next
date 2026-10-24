// SPDX-License-Identifier: MIT
#pragma once
#include <cstdint>
#include "native_allocator_budget.h"
// Frontend implementation is separate from permission to execute on a console.
bool qwen_native_gpu_frontend_linked();
void qwen_native_gpu_initialize(const char * own_journal);
qwen_app::NativeAllocatorBudget qwen_native_allocator_budget(std::uint64_t reported_device_total);
extern "C" {
void qwen_native_driver_begin();
void qwen_native_driver_complete();
void qwen_native_driver_checkpoint();
void qwen_native_driver_retain();
void qwen_native_driver_before_submit();
void qwen_native_driver_after_submit();
void qwen_native_driver_register_device(std::uintptr_t device);
}
