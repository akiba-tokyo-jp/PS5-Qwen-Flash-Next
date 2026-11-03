/* SPDX-License-Identifier: MIT */
#pragma once
#include <stdint.h>
struct qwen_cold_probe_result {
    int status, source_closed, readonly, constructor_checked, allocation_retained;
    uint32_t free_before, free_after, minimum_free;
    uint64_t mapped_bytes, checksum;
    int failure_step, source_flags, source_errno;
    uint64_t source_mode, source_uid, source_gid, source_links, source_bytes;
    int64_t last_read;
    uint64_t completed_reads;
    unsigned char observed_digest[32];
};
extern struct qwen_cold_probe_result qwen_cold_probe;
