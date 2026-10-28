// SPDX-License-Identifier: MIT
#pragma once
#include <algorithm>
#include <array>
#include <atomic>
#include <cstring>
#include <string>
namespace qwen_app {
namespace {
std::atomic_flag resident_error_lock=ATOMIC_FLAG_INIT;
std::array<char,2049> resident_error_tail{};
std::size_t resident_error_size=0;
}
inline void resident_native_log(enum ggml_log_level level,const char *text,void *opaque) {
    ::native_log(level,text,opaque);
    if(level!=GGML_LOG_LEVEL_ERROR||!text)return;
    const auto length=std::strlen(text);const auto keep=std::min<std::size_t>(length,2048);
    while(resident_error_lock.test_and_set(std::memory_order_acquire)){}
    if(resident_error_size+keep>2048){const auto drop=resident_error_size+keep-2048;
        std::memmove(resident_error_tail.data(),resident_error_tail.data()+drop,resident_error_size-drop);
        resident_error_size-=drop;}
    std::memcpy(resident_error_tail.data()+resident_error_size,text+length-keep,keep);
    resident_error_size+=keep;resident_error_tail[resident_error_size]=0;
    resident_error_lock.clear(std::memory_order_release);
}
inline std::string resident_last_model_error() {
    std::array<char,2049> copy{};
    while(resident_error_lock.test_and_set(std::memory_order_acquire)){}
    std::memcpy(copy.data(),resident_error_tail.data(),resident_error_size+1);
    resident_error_lock.clear(std::memory_order_release);
    return std::string(copy.data());
}
}
