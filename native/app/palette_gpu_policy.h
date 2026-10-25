// SPDX-License-Identifier: MIT
#pragma once
#include <nlohmann/json.hpp>
#include <array>
#include <cstdint>
#include <stdexcept>
#include <string>
namespace qwen_app {
inline void require_palette_gpu_policy(const nlohmann::json &policy,bool display) {
    using Json=nlohmann::json;
    const auto check=[](bool ok){if(!ok)throw std::runtime_error("Exact bounded no-display palette GPU policy is required");};
    const auto digest=[&](const Json &e){
        check(e.at("sha256").is_string());const auto h=e.at("sha256").get<std::string>();
        check(h.size()==64&&h.find_first_not_of("0123456789abcdef")==std::string::npos);
    };
    const auto integer=[&](const Json &e,const char *key,std::uint64_t limit){
        check(e.at(key).is_number_unsigned()&&e.at(key).get<std::uint64_t>()<=limit);
    };
    const auto &p=policy.at("native_palette_validation");
    check(!display&&p.is_object()&&p.size()==12&&p.at("schema")=="ps5-qwen-exact-palette-GPU-v1"&&
        p.at("enabled").is_boolean()&&p.at("enabled")==true&&
        p.at("driver_revision")=="872cc1264ad8ba5d6b888b092968fa5858a38c58"&&p.at("profile")=="cumulative-idle"&&
        p.at("native_archive_sha256")=="b57fe26e969940d147be05c1ffae830503d4865877281dffe03af32328f49925"&&
        p.at("model_loading_enabled").is_boolean()&&p.at("model_loading_enabled")==false&&
        p.at("persistent_caches_enabled").is_boolean()&&p.at("persistent_caches_enabled")==false);
    integer(p,"maximum_GPU_memory_bytes",16u<<20);integer(p,"rounds",6);
    check(p.at("maximum_GPU_memory_bytes")==16u<<20&&p.at("rounds")==6);
    const auto &pack=p.at("pack");check(pack.is_object()&&pack.size()==3);digest(pack);integer(pack,"bytes",128u<<20);
    const auto path=pack.at("path").get<std::string>();
    check(pack.at("bytes").get<std::uint64_t>()>0&&path=="/app0/qwen-runtime/palette-samples.pack");
    const auto &samples=p.at("samples");check(samples.is_array()&&samples.size()==9);
    std::array<std::array<std::uint64_t,2>,18> ranges{};unsigned range_count=0;
    for(const auto &sample:samples) {
        check(sample.is_object()&&sample.size()==2);
        for(const auto *role:{"raw","encoded"}) {
            const auto &e=sample.at(role);check(e.is_object()&&e.size()==4);digest(e);
            integer(e,"offset",128u<<20);integer(e,"bytes",4u<<20);integer(e,"requested",4u<<20);
            const auto offset=e.at("offset").get<std::uint64_t>(),bytes=e.at("bytes").get<std::uint64_t>(),requested=e.at("requested").get<std::uint64_t>();
            check(bytes>0&&offset%16384==0&&requested%16384==0&&requested==(bytes+16383)/16384*16384&&offset+requested<=pack.at("bytes").get<std::uint64_t>());
            for(unsigned i=0;i<range_count;++i)check(offset>=ranges[i][1]||ranges[i][0]>=offset+requested);
            ranges[range_count++]={offset,offset+requested};
            if(std::string(role)=="raw")check(bytes==3276800);
        }
    }
    const auto &shaders=p.at("shaders");check(shaders.is_object()&&shaders.size()==2);
    for(const auto *name:{"copy","palette"}) {
        const auto &s=shaders.at(name);check(s.is_object()&&s.size()==3);digest(s);integer(s,"bytes",65536);
        check(s.at("bytes").get<unsigned>()>=20&&s.at("bytes").get<unsigned>()%4==0&&s.at("path")==std::string("/app0/qwen-runtime/palette-")+name+".spv");
    }
}
}
