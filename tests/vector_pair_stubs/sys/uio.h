// SPDX-License-Identifier: MIT
#pragma once
#include <stddef.h>
#include <sys/types.h>
struct iovec {void *iov_base;size_t iov_len;};
extern "C" ssize_t qwen_vector_test_preadv(int,const struct iovec *,int,off_t);
