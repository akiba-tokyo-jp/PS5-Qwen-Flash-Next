// SPDX-License-Identifier: MIT
#pragma once
#include <array>
#include <cstdint>
#include <cstring>
#include <string>
#include <vector>
namespace qwen_frontier {
struct CommandBinding {std::uint64_t buffer,offset,range;};
inline std::string command_key(std::uintptr_t context,std::uint64_t destroy_generation,
    std::uint64_t pipeline,std::uint64_t layout,std::uint32_t family,
    const std::array<std::uint32_t,3>& groups,const std::vector<CommandBinding>& bindings,
    const void *push,std::size_t push_size) {
    std::string key;
    auto add=[&](const auto &v){key.append(reinterpret_cast<const char*>(&v),sizeof(v));};
    add(context);add(destroy_generation);add(pipeline);add(layout);add(family);
    for(auto n:groups)add(n);
    const std::uint64_t count=bindings.size(),bytes=push_size;add(count);add(bytes);
    for(const auto &b:bindings){add(b.buffer);add(b.offset);add(b.range);}
    if(push_size)key.append(static_cast<const char*>(push),push_size);
    return key;
}
}
