/* SPDX-License-Identifier: MIT
 * ABI facts cross-checked against SharpProspero 5dfdb4b0 KernelAio.cs.
 * Only read, bounded wait and completed single-ID retirement are used.
 */
#pragma once
#include <stddef.h>
#include <stdint.h>
struct qwen_aio_result { int64_t value; volatile uint32_t state; uint32_t pad; };
struct qwen_aio_schedule { int32_t window,delayed; uint32_t split,size,chunk; };
struct qwen_aio_param { struct qwen_aio_schedule priorities[3]; };
struct qwen_aio_read { int64_t offset; uint64_t bytes; void *buffer; struct qwen_aio_result *result; int32_t fd,pad; };
_Static_assert(sizeof(struct qwen_aio_result)==16,"Native AIO result ABI");
_Static_assert(sizeof(struct qwen_aio_schedule)==20,"Native AIO scheduling ABI");
_Static_assert(sizeof(struct qwen_aio_param)==60,"Native three-priority AIO ABI");
_Static_assert(sizeof(struct qwen_aio_read)==40,"Native AIO request ABI");
_Static_assert(offsetof(struct qwen_aio_read,result)==24,"Native AIO result address offset");
_Static_assert(offsetof(struct qwen_aio_read,fd)==32,"Native AIO descriptor offset");
void sceKernelAioInitializeParam(struct qwen_aio_param *);
int sceKernelAioInitializeImpl(void *,int);
int sceKernelAioSubmitReadCommands(struct qwen_aio_read *,int,int,int *);
int sceKernelAioPollRequest(int,int *);
int sceKernelAioWaitRequest(int,int *,uint32_t *);
int sceKernelAioDeleteRequest(int,int *);
