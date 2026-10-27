// SPDX-License-Identifier: MIT
#pragma once
#include <cstddef>
struct qwen_driver_table {
    unsigned char *target;std::size_t bytes,offset,packed_bytes;unsigned char sha256[32];
};
struct qwen_driver_table_plan {
    const qwen_driver_table *tables;std::size_t count;const unsigned char *packed;std::size_t packed_bytes;
    unsigned char *begin,*end;
};
extern "C" const qwen_driver_table_plan qwen_driver_table_storage __attribute__((weak));
namespace qwen_app { void restore_native_driver_tables(); }
