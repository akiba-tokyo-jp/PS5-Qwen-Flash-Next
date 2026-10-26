// SPDX-License-Identifier: MIT
#pragma once
#include <nlohmann/json.hpp>
#include <cstdint>
#include <stdexcept>
#include <string>
#include <utility>
namespace qwen_app {
inline void require_PLE_slice_policy(const nlohmann::json &policy,bool display) {
    using Json=nlohmann::json;const auto check=[](bool ok){if(!ok)throw std::runtime_error("Exact headless bounded PLE fixture policy required");};
    const auto &p=policy.at("native_PLE_slice_validation");
    check(!display&&p.is_object()&&p.size()==14&&p.at("schema")=="ps5-qwen-PLE-slice-policy-v1"&&p.at("enabled")==true&&
        p.at("driver_revision")=="872cc1264ad8ba5d6b888b092968fa5858a38c58"&&p.at("profile")=="cumulative-idle"&&
        p.at("native_archive_sha256")=="b57fe26e969940d147be05c1ffae830503d4865877281dffe03af32328f49925"&&
        p.at("model_loading_enabled")==false&&p.at("persistent_caches_enabled")==false&&
        p.at("deterministic_data")=="original_shapes_not_model_weights");
    for(const auto &item:{std::pair<const char*,std::uint64_t>{"maximum_GPU_payload_bytes",16u<<20},{"rounds",8},
            {"maximum_graphs",208},{"maximum_source_scratch_bytes",8u<<20}})
        check(p.at(item.first).is_number_unsigned()&&p.at(item.first)==item.second);
    for(const auto *name:{"widths","modes"}) {
        const auto &a=p.at(name);check(a.is_array()&&a.size()==4);
        for(unsigned i=0;i<4;++i)check(a[i].is_number_unsigned()&&a[i]==i+unsigned(std::string(name)=="widths"));
    }
    const auto &s=policy.at("native_shader_storage");
    check(s.is_object()&&s.size()==11&&s.at("schema")=="ps5-qwen-shader-storage-policy-v1"&&s.at("enabled")==true&&
        s.at("verify_all_original_assets_before_Vulkan")==true&&s.at("model_and_shader_precision_unchanged")==true&&
        s.at("persistent_caches_enabled")==false&&!s.contains("prior_native_CPU"));
    const auto hash=[&](const Json &value){check(value.is_string());const auto h=value.get<std::string>();check(h.size()==64&&h.find_first_not_of("0123456789abcdef")==std::string::npos);return h;};
    (void)hash(s.at("registry_sha256"));
    for(const auto *name:{"shader_count","original_bytes","stored_bytes","lookup_entries"})check(s.at(name).is_number_unsigned()&&s.at(name)>0);
    check(s.at("shader_count")<=8192u&&s.at("lookup_entries")<=65536u&&s.at("original_bytes")<=(512u<<20)&&s.at("stored_bytes")<=(128u<<20));
    const auto &f=s.at("external_file");check(f.is_object()&&f.size()==7);
    const auto digest=hash(f.at("sha256"));
    check(f.at("schema")=="ps5-qwen-external-shader-file-policy-v1"&&f.at("single_read_only_descriptor")==true&&
        f.at("new_model_source_window")==false&&f.at("bytes").is_number_unsigned()&&f.at("bytes")==s.at("stored_bytes")&&
        f.at("path")=="/app0/qwen-runtime/shader-storage-"+digest+".bin"&&f.at("input_window_bytes").is_number_unsigned());
    const auto window=f.at("input_window_bytes").get<std::uint64_t>();check(window&&window<=(1u<<20)&&window%16384==0);
}
// The caller must first qualify CPU shader storage and startup memory,
// and must positively complete the driver epoch after this function returns.
nlohmann::json admit_PLE_slice_fixture(const nlohmann::json &policy,const std::string &journal);
}
