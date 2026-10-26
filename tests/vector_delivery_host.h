// SPDX-License-Identifier: MIT
#pragma once
#include <stddef.h>
#include <sys/types.h>
// Windows has no native pread declaration; this is the metadata fixture's copy stub.
extern "C" ssize_t qwen_vector_test_pread(int,void *,size_t,off_t);
