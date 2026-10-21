// SPDX-License-Identifier: MIT
// Host preview assertion support. Native builds use the real GGML definition.
#include "ggml.h"
#include <cstdarg>
#include <cstdio>
#include <cstdlib>

extern "C" void ggml_abort(const char * file, int line, const char * format, ...) {
    std::fprintf(stderr, "%s:%d: ", file, line);
    va_list arguments;
    va_start(arguments, format);
    std::vfprintf(stderr, format, arguments);
    va_end(arguments);
    std::abort();
}
