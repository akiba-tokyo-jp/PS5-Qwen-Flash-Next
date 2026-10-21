// SPDX-License-Identifier: MIT
// Use the public title API for CPU protection. Executable mappings are not
// required by this static inference client; never invoke payload kernel helpers.
#include <ps5platform/kernel.h>
#include <sys/mman.h>
#include <cerrno>
#include <cstddef>
#include <cstdint>
extern "C" int qwen_native_mprotect(void * address, std::size_t bytes, int protection) {
    static_assert(PROT_READ == 1 && PROT_WRITE == 2 && PROT_EXEC == 4, "Unexpected CPU protection bits");
    if (protection & ~(PROT_READ | PROT_WRITE)) { errno = EPERM; return -1; }
    const auto result = sceKernelMprotect(address, bytes, protection);
    if (result < 0) { errno = std::uint32_t(result) & 0xffff; return -1; }
    return 0;
}
