/* SPDX-License-Identifier: GPL-3.0-or-later
 * CPU-only native/supervisor handshake. Every access holds an advisory lock.
 */
#ifndef QWEN_APR_DIRECT_CONTROL_H
#define QWEN_APR_DIRECT_CONTROL_H
#include <stdint.h>
#define APR_DIRECT_MAGIC UINT64_C(0x4150524449523031)
enum apr_direct_stage { APR_DIRECT_READY=1, APR_DIRECT_BUSY=2, APR_DIRECT_MOUNTED=3,
    APR_DIRECT_NATIVE_CLOSED=4, APR_DIRECT_ABORT=5, APR_DIRECT_DETACHED=6 };
struct apr_direct_control {uint64_t magic;char nonce[32];uint64_t pid;uint32_t stage,error;uint64_t reserved;};
#if defined(__cplusplus)
static_assert(sizeof(apr_direct_control)==64,"Shared control ABI");
#else
_Static_assert(sizeof(struct apr_direct_control)==64,"Shared control ABI");
#endif
#endif
