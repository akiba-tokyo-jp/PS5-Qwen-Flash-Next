// SPDX-License-Identifier: MIT
#include <cerrno>
#include <cstddef>
#include <cstdint>
#include <iostream>
#include <stdexcept>
static int calls = 0, result = 0, last_protection = -1;
extern "C" int qwen_native_mprotect(void *, std::size_t, int);
extern "C" std::int32_t sceKernelMprotect(const void * pointer, std::size_t bytes, int protection) {
    if (pointer != reinterpret_cast<void *>(0x10000) || bytes != 0x4000) throw std::runtime_error("Unexpected protection range");
    ++calls; last_protection = protection; return result;
}
int main() {
    auto check = [](bool ok) { if (!ok) throw std::runtime_error("Public memory-protection adapter failed"); };
    try {
        auto * address = reinterpret_cast<void *>(0x10000);
        for (int protection : {0, 1, 2, 3}) {
            check(qwen_native_mprotect(address, 0x4000, protection) == 0 && last_protection == protection);
        }
        const int before = calls;
        for (int protection : {4, 5, 7, 0x20, -1})
            check(qwen_native_mprotect(address, 0x4000, protection) == -1 && errno == EPERM && calls == before);
        result = static_cast<std::int32_t>(0x8002000c);
        check(qwen_native_mprotect(address, 0x4000, 1) == -1 && errno == 12);
        std::cout << "Public title protection, errno translation and executable/kernel-helper rejection passed; API stubs only\n";
    } catch (const std::exception & error) { std::cerr << error.what() << '\n'; return 1; }
}
