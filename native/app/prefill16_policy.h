// SPDX-License-Identifier: MIT
#pragma once
namespace qwen_app {
constexpr bool supported_sharing_prefill_width(unsigned width) {
    return width==4||width==16;
}
}
