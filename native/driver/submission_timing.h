/* SPDX-License-Identifier: MIT */
#pragma once
/* Observation only: no allocation, visibility, timeout or completion policy changes. */
#include <stdint.h>
extern uint64_t qwen_submit_timing[48];
extern unsigned qwen_submit_timing_enabled;
void qwen_ps5_timing_select(unsigned enabled);
void qwen_ps5_timing_snapshot(uint64_t *out);
static inline void qwen_timing_add(unsigned slot, uint64_t value) {
    if (p_atomic_read(&qwen_submit_timing_enabled)) p_atomic_add(&qwen_submit_timing[slot], value);
}
struct qwen_timing_scope { unsigned slot; uint64_t start; };
static inline struct qwen_timing_scope qwen_timing_start(unsigned slot) {
    struct qwen_timing_scope s = {slot, 0};
    if (p_atomic_read(&qwen_submit_timing_enabled)) {
        p_atomic_inc(&qwen_submit_timing[slot]); s.start = os_time_get_nano();
    }
    return s;
}
static inline void qwen_timing_finish(struct qwen_timing_scope *s) {
    if (s->start) p_atomic_add(&qwen_submit_timing[s->slot+1], os_time_get_nano()-s->start);
}
#define QWEN_TIMING_SCOPE(slot) struct qwen_timing_scope qwen_measured_##slot __attribute__((cleanup(qwen_timing_finish))) = qwen_timing_start(slot)
