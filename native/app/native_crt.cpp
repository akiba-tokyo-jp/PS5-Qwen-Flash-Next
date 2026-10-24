/*
 * ps5-native-app-boilerplate - Native application startup.
 * Copyright (C) 2026 BlackBearReloaded
 * SPDX-License-Identifier: GPL-3.0-or-later
 *
 * Derived from the pinned PS5-Vulkan-Inference tooling/native/app_crt.cpp.
 * Preserve IEEE/platform startup, constructor order and the main-return hook.
 * The application adds fixed durable records around each C++ initializer.
 */
#include <cstddef>
#include <cstdint>
using Destructor = void (*)();
using Initializer = void (*)();
extern "C" {
void _init_env(void *);
void ps5_fp_ieee(void);
int atexit(Destructor);
[[noreturn]] void exit(int);
int application_main(int, char **, char **) __asm__("main");
void qwen_native_stage(const char *);
void qwen_native_trace_initializer(std::size_t, std::uintptr_t, bool);
extern Initializer __preinit_array_start[] __attribute__((weak));
extern Initializer __preinit_array_end[] __attribute__((weak));
extern Initializer __init_array_start[] __attribute__((weak));
extern Initializer __init_array_end[] __attribute__((weak));
extern Initializer __fini_array_start[] __attribute__((weak));
extern Initializer __fini_array_end[] __attribute__((weak));
}
extern "C" __attribute__((weak)) void catchReturnFromMain(int) {}
extern "C" void _init() {
    if (__preinit_array_start && __preinit_array_end)
        for (auto * entry = __preinit_array_start; entry != __preinit_array_end; ++entry) (*entry)();
    qwen_native_stage("CXX_initializers_begin");
    if (__init_array_start && __init_array_end) {
        std::size_t index = 0;
        for (auto * entry = __init_array_start; entry != __init_array_end; ++entry, ++index) {
            const auto address = reinterpret_cast<std::uintptr_t>(*entry);
            qwen_native_trace_initializer(index, address, false);
            (*entry)();
            qwen_native_trace_initializer(index, address, true);
        }
    }
    qwen_native_stage("CXX_initializers_completed");
}
extern "C" void _fini() {
    if (__fini_array_start && __fini_array_end)
        for (auto * entry = __fini_array_end; entry != __fini_array_start;) (*--entry)();
}
extern "C" [[noreturn]] __attribute__((visibility("default"))) void
_start(void * process_parameters, Destructor loader_teardown) {
    const int argc = *static_cast<const int *>(process_parameters);
    auto ** argv = reinterpret_cast<char **>(static_cast<std::uint8_t *>(process_parameters) + sizeof(std::uint64_t));
    ps5_fp_ieee();
    _init_env(process_parameters);
    if (loader_teardown) (void) atexit(loader_teardown);
    (void) atexit(_fini);
    _init();
    const int result = application_main(argc, argv, nullptr);
    catchReturnFromMain(result);
    exit(result);
}
