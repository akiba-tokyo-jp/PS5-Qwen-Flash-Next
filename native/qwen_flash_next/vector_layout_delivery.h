// SPDX-License-Identifier: MIT
#pragma once
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
struct vector_layout_source {int fd;uint64_t offset;};
struct vector_layout_times {uint64_t wall_ns,source_ns,physical_bytes;};
int vector_layout_start(void);
int vector_layout_batch(unsigned mode,const struct vector_layout_source sources[6],
    unsigned char *destination,struct vector_layout_times *times);
int vector_layout_stop(void);
int vector_layout_identity(int,uint64_t *,uint64_t *,uint64_t *);
int vector_layout_permit(void);
int vector_layout_record(const char *);
uint64_t vector_layout_now(void);
#ifdef __cplusplus
}
#endif
