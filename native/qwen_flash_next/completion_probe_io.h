// SPDX-License-Identifier: MIT
#pragma once
#include <stddef.h>
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
struct completion_extent {uint64_t offset;uint32_t bytes,requested;};
struct completion_times {uint64_t wall_ns,restore_ns,read_ns,physical_bytes,copy_ns;};
int completion_probe_start(void);
int completion_probe_batch(int fd,unsigned mode,const struct completion_extent *extents,unsigned count,
    unsigned char *io,unsigned char *destination,struct completion_times *times);
int completion_probe_stop(void);
int completion_probe_permit(void);
int completion_probe_event(unsigned returned,unsigned slot,uint64_t id,uint64_t offset,uint64_t bytes,
    int64_t result,uint64_t started,uint64_t finished);
uint64_t completion_probe_now(void);
#ifdef __cplusplus
}
#endif
