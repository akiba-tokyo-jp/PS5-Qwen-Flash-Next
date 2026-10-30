// SPDX-License-Identifier: MIT
#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <mutex>
#include <stdexcept>

namespace qwen_app {
// Cache only the numeric name. Every value is read again through the original
// observation order; free pages, limits and Flexible availability are not cached.
class NumericMemoryCounter {
    std::array<int,24>name_{};std::size_t length_=0;std::once_flag resolved_;
public:
    template<class Resolve,class Read>std::uint32_t value(const char*text,Resolve resolve,Read read){
        std::call_once(resolved_,[&]{auto length=name_.size();if(resolve(text,name_.data(),&length)||!length||length>name_.size())throw std::runtime_error("Native numeric memory name resolution failed");length_=length;});
        std::uint32_t result=0;auto bytes=sizeof(result);
        if(read(name_.data(),unsigned(length_),&result,&bytes)||bytes!=sizeof(result))throw std::runtime_error("Fresh numeric memory observation failed");
        return result;
    }
};
}
