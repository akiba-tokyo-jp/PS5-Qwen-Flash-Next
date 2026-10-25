/* SPDX-License-Identifier: MIT */
#pragma once
#include <stddef.h>
#include <stdint.h>
struct queued_probe_request {int fd;void *target;size_t bytes;uint64_t offset;};
#ifdef __cplusplus
extern "C" {
#endif
int queued_probe_start(void);
int queued_probe_read(const struct queued_probe_request *,unsigned,int64_t *);
int queued_probe_stop(void);
unsigned queued_probe_pending(void);
#ifdef __cplusplus
}
#endif
