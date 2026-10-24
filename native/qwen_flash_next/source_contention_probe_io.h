/* SPDX-License-Identifier: MIT */
#pragma once
#include <stdint.h>
#include <sys/types.h>
struct read_sample {uint64_t begin,end,cpu_ns;long voluntary,involuntary;ssize_t got;int error;};
struct job {int fd;unsigned char *target;size_t bytes;off_t offset;struct read_sample sample;};
#ifdef __cplusplus
extern "C" {
#endif
void probe_execute_read(struct job *,unsigned,int);
int probe_cpp_start(void);
int probe_cpp_read(struct job *,int);
int probe_cpp_parallel_allowed(const struct job *,const uint64_t *,const uint64_t *);
int probe_cpp_stop(void);
#ifdef __cplusplus
}
#endif
