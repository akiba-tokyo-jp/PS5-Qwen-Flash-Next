// SPDX-License-Identifier: MIT
#pragma once
#include <nlohmann/json.hpp>
#include <array>
#include <cstdint>
#include <stdexcept>
#include <string>
#include <utility>
namespace qwen_app {
inline bool PLE_slice_smoke(const nlohmann::json &policy) {
    const auto &schema=policy.at("native_PLE_slice_validation").at("schema");
    return schema=="ps5-qwen-PLE-slice-smoke-policy-v1"||schema=="ps5-qwen-PLE-slice-smoke-policy-v2";
}
inline bool PLE_slice_explicit_source(const nlohmann::json &policy) {
    const auto &schema=policy.at("native_PLE_slice_validation").at("schema");
    return schema=="ps5-qwen-PLE-slice-smoke-policy-v2"||schema=="ps5-qwen-PLE-slice-paired-policy-v2";
}
inline bool PLE_slice_prior_proof(const nlohmann::json &policy) {
    return PLE_slice_smoke(policy)||PLE_slice_explicit_source(policy);
}
inline void require_PLE_source_identity(const std::array<std::uint64_t,10> &identity,std::uint64_t bytes) {
    const auto mode=identity[2];
    if(!identity[1]||(mode&0170000u)!=0100000u||!bytes||identity[5]!=bytes||(mode&0022u))
        throw std::runtime_error("PLE source owner requires stable read-only regular-file identity: inode_present="+
            std::to_string(bool(identity[1]))+" mode_bits="+std::to_string(mode&07777u)+
            " bytes_match="+std::to_string(identity[5]==bytes));
}
inline void require_PLE_slice_policy(const nlohmann::json &policy,bool display) {
    using Json=nlohmann::json;const auto check=[](bool ok){if(!ok)throw std::runtime_error("Exact headless bounded PLE fixture policy required");};
    const auto &p=policy.at("native_PLE_slice_validation");
    const bool smoke=PLE_slice_smoke(policy),explicit_source=PLE_slice_explicit_source(policy),prior=PLE_slice_prior_proof(policy);
    check(!display&&p.is_object()&&p.size()==(explicit_source?15u:14u)&&(smoke||explicit_source||p.at("schema")=="ps5-qwen-PLE-slice-policy-v1")&&p.at("enabled")==true&&
        p.at("driver_revision")=="872cc1264ad8ba5d6b888b092968fa5858a38c58"&&p.at("profile")=="cumulative-idle"&&
        p.at("native_archive_sha256")=="b57fe26e969940d147be05c1ffae830503d4865877281dffe03af32328f49925"&&
        p.at("model_loading_enabled")==false&&p.at("persistent_caches_enabled")==false&&
        p.at("deterministic_data")=="original_shapes_not_model_weights");
    for(const auto &item:{std::pair<const char*,std::uint64_t>{"maximum_GPU_payload_bytes",16u<<20},{"rounds",smoke?0u:8u},
            {"maximum_graphs",smoke?4u:208u},{"maximum_source_scratch_bytes",8u<<20}})
        check(p.at(item.first).is_number_unsigned()&&p.at(item.first)==item.second);
    for(const auto *name:{"widths","modes"}) {
        const auto &a=p.at(name);const unsigned count=smoke&&std::string(name)=="widths"?1:4;
        check(a.is_array()&&a.size()==count);
        for(unsigned i=0;i<count;++i)check(a[i].is_number_unsigned()&&a[i]==i+unsigned(std::string(name)=="widths"));
    }
    const auto &s=policy.at("native_shader_storage");
    check(s.is_object()&&s.size()==(prior?12u:11u)&&s.at("schema")=="ps5-qwen-shader-storage-policy-v1"&&s.at("enabled")==true&&
        s.at("verify_all_original_assets_before_Vulkan")==!prior&&s.at("model_and_shader_precision_unchanged")==true&&
        s.at("persistent_caches_enabled")==false&&s.contains("prior_native_CPU")==prior);
    const auto hash=[&](const Json &value){check(value.is_string());const auto h=value.get<std::string>();check(h.size()==64&&h.find_first_not_of("0123456789abcdef")==std::string::npos);return h;};
    (void)hash(s.at("registry_sha256"));
    if(prior) {
        const auto &prior=s.at("prior_native_CPU");check(prior.is_object()&&prior.size()==10);
        for(const auto *name:{"all_original_assets_completed_on_this_boot","same_encoded_resources_and_per_use_decoder_in_current_SELF",
                "current_module_input_full_SHA256_required"})check(prior.at(name)==true);
        for(const auto *name:{"report_sha256","prior_SELF_sha256","resource_manifest_sha256"})(void)hash(prior.at(name));
        const auto run=prior.at("run_id").get<std::string>();
        check(run.size()==32&&run.find_first_not_of("0123456789abcdef")==std::string::npos&&
            prior.at("report_path")=="/app0/qwen-runtime/plan-"+run+".json.shader-assets.CPU"&&
            prior.at("report_bytes").is_number_unsigned()&&prior.at("report_bytes")>0&&prior.at("report_bytes")<=4096u&&
            prior.at("pid").is_number_unsigned()&&prior.at("pid")>0);
    }
    for(const auto *name:{"shader_count","original_bytes","stored_bytes","lookup_entries"})check(s.at(name).is_number_unsigned()&&s.at(name)>0);
    check(s.at("shader_count")<=8192u&&s.at("lookup_entries")<=65536u&&s.at("original_bytes")<=(512u<<20)&&s.at("stored_bytes")<=(128u<<20));
    const auto &f=s.at("external_file");check(f.is_object()&&f.size()==7);
    const auto digest=hash(f.at("sha256"));
    check(f.at("schema")=="ps5-qwen-external-shader-file-policy-v1"&&f.at("single_read_only_descriptor")==true&&
        f.at("new_model_source_window")==false&&f.at("bytes").is_number_unsigned()&&f.at("bytes")==s.at("stored_bytes")&&
        f.at("path")=="/app0/qwen-runtime/shader-storage-"+digest+".bin"&&f.at("input_window_bytes").is_number_unsigned());
    const auto window=f.at("input_window_bytes").get<std::uint64_t>();check(window&&window<=(1u<<20)&&window%16384==0);
    if(explicit_source) {
        const auto &source=p.at("source_guard");check(source.is_object()&&source.size()==6&&
            source.at("schema")=="ps5-qwen-PLE-qualified-source-owner-v1"&&
            source.at("path")=="/app0/qwen-runtime/vector-bank-0.pack"&&
            source.at("bytes").is_number_unsigned()&&source.at("bytes")>=16384u&&source.at("bytes")<=(128u<<20)&&
            source.at("numerical_input")==false&&source.at("current_whole_native_integrity_required")==true);
        (void)hash(source.at("sha256"));
    }
}
// CPU-only prerequisite, including complete current source integrity for v2.
// A completed owner may be consumed once by the same thread and exact policy.
void prepare_PLE_source_owner(const nlohmann::json &policy);
// The caller must first qualify CPU shader storage and startup memory,
// and must positively complete the driver epoch after this function returns.
nlohmann::json admit_PLE_slice_fixture(const nlohmann::json &policy,const std::string &journal);
}
