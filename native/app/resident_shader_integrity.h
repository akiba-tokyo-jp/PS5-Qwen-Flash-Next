// SPDX-License-Identifier: MIT
#pragma once
#include <nlohmann/json.hpp>
#include <array>
#include <cstdint>
#include <stdexcept>
extern "C" void qwen_app_bind_same_launch_shader_integrity(const std::uint64_t*,std::uint64_t,const unsigned char*);
namespace qwen_app {
inline std::array<std::uint64_t,10> validate_resident_shader_receipt(const nlohmann::json &s,const nlohmann::json &expected) {
    const auto bytes=expected.at("bytes").get<std::uint64_t>();const auto sha=expected.at("sha256").get<std::string>();
    if(!bytes||bytes>(512ull<<20)||sha.size()!=64||sha.find_first_not_of("0123456789abcdef")!=std::string::npos||
       expected.at("path")!="/app0/qwen-runtime/shader-storage-"+sha+".bin"||
       s.at("schema")!="ps5-qwen-same-launch-shader-integrity-v1"||s.at("bytes")!=bytes||
       s.at("sha256")!=sha||s.at("path")!=expected.at("path")||s.size()!=5||
       !s.at("bytes").is_number_integer()||!s.at("identity").is_array()||s.at("identity").size()!=10)
        throw std::runtime_error("Exact current shader resource integrity required");
    std::array<std::uint64_t,10> identity{};
    for(unsigned i=0;i<10;++i) {
        if(!s.at("identity")[i].is_number_integer())throw std::runtime_error("Typed shader identity required");
        identity[i]=s.at("identity")[i].get<std::uint64_t>();
    }
    if(!identity[0]||!identity[1]||identity[5]!=bytes)throw std::runtime_error("Complete shader inode identity required");
    return identity;
}
inline void bind_resident_shader_integrity(const nlohmann::json &receipt,const nlohmann::json &expected) {
    const auto identity=validate_resident_shader_receipt(receipt.at("external_shader"),expected);
    const auto bytes=expected.at("bytes").get<std::uint64_t>();const auto sha=expected.at("sha256").get<std::string>();
    std::array<unsigned char,32> digest{};
    const auto digit=[](char c){return unsigned(c<='9'?c-'0':c-'a'+10);};
    for(unsigned i=0;i<32;++i)digest[i]=static_cast<unsigned char>((digit(sha[2*i])<<4)|digit(sha[2*i+1]));
    qwen_app_bind_same_launch_shader_integrity(identity.data(),bytes,digest.data());
}
}
