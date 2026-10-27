// SPDX-License-Identifier: MIT
#pragma once
#include <nlohmann/json.hpp>
#include <cstdint>
#include <stdexcept>
#include <string>
namespace qwen_app {
// One existing original-BF16 pack, no model load or new converted corpus.
inline constexpr const char *split_bank_pack_path="/app0/qwen-runtime/vector-bank-0.pack";
inline constexpr std::uint64_t split_bank_pack_bytes=63488000;
inline constexpr const char *split_bank_pack_sha256="4d6247378c577a586d8cc552b14c771f63a732f8b9762ead8405612aea2d371d";
inline void require_split_bank_policy(const nlohmann::json &policy,bool mode,bool display,bool clock) {
    using Json=nlohmann::json;
    const auto check=[](bool good){if(!good)throw std::invalid_argument("Exact isolated split-bank backing scope required");};
    check(mode&&!display&&!clock&&policy.at("console_operations_enabled")==true&&
        policy.at("console_validation_enabled")==true&&policy.at("allowed_modes")==Json::array({"first-generation-validation"}));
    const auto &p=policy.at("native_split_bank_validation");
    check(p.is_object()&&p.size()==8&&p.at("schema")=="ps5-qwen-split-bank-policy-v1"&&p.at("enabled")==true&&
        p.at("driver_revision")=="872cc1264ad8ba5d6b888b092968fa5858a38c58"&&p.at("profile")=="cumulative-idle"&&
        p.at("native_archive_sha256")=="b57fe26e969940d147be05c1ffae830503d4865877281dffe03af32328f49925"&&
        p.at("model_loading_enabled")==false&&p.at("persistent_caches_enabled")==false);
    const auto &pack=p.at("source_pack");
    check(pack.is_object()&&pack.size()==3&&pack.at("path")==split_bank_pack_path&&
        pack.at("bytes").is_number_unsigned()&&pack.at("bytes")==split_bank_pack_bytes&&pack.at("sha256")==split_bank_pack_sha256);
    const bool ready=policy.contains("native_ready_expert_numerical");
    const bool original=policy.contains("native_ready_expert_original");
    if(original) {
        check(ready);const auto &o=policy.at("native_ready_expert_original");
        check(o.is_object()&&o.size()==7&&o.at("schema")=="ps5-qwen-ready-original-policy-v1"&&o.at("enabled")==true&&
            o.at("same_title_numerical_gate_required")==true&&o.at("unique_original_experts").is_number_unsigned()&&o.at("unique_original_experts")==10u&&
            o.at("source_IO_depth").is_number_unsigned()&&o.at("source_IO_depth")==2u&&o.at("cohort_runs").is_number_unsigned()&&o.at("cohort_runs")==6u);
        const auto sha=o.at("source_plan_sha256").get<std::string>();check(sha.size()==64&&sha.find_first_not_of("0123456789abcdef")==std::string::npos);
    }
    if(ready)check(policy.at("native_ready_expert_numerical")==Json{{"schema","ps5-qwen-ready-numerical-policy-v1"},{"enabled",true},
        {"unique_original_experts",2u},{"original_contributions",10u},{"cohort_runs",6u},
        {"source_IO_depth",1u},{"representative_speed_test",false}});
    if(ready)for(const auto *key:{"unique_original_experts","original_contributions","cohort_runs","source_IO_depth"})
        check(policy.at("native_ready_expert_numerical").at(key).is_number_unsigned());
    const auto &binding=policy.at("native_isolated_split_bank_title");
    check(binding.is_object()&&binding.size()==6&&binding.at("schema")=="ps5-qwen-isolated-split-bank-title-v1"&&
        binding.at("model_loading_enabled")==false&&binding.at("source_workers").is_number_unsigned()&&binding.at("source_workers")==unsigned(original?2:ready?1:0)&&
        binding.at("candidate_SELF_bytes").is_number_unsigned()&&binding.at("candidate_SELF_bytes")>0u&&binding.at("candidate_SELF_bytes")<=(32u<<20));
    const auto hash=binding.at("candidate_SELF_sha256").get<std::string>(),run=binding.at("run_id").get<std::string>();
    check(hash.size()==64&&hash.find_first_not_of("0123456789abcdef")==std::string::npos&&
        run.size()==32&&run.find_first_not_of("0123456789abcdef")==std::string::npos);
    const auto &storage=policy.at("native_shader_storage");
    check(storage.at("persistent_caches_enabled")==false&&storage.at("model_and_shader_precision_unchanged")==true&&
        storage.at("verify_all_original_assets_before_Vulkan")==false&&storage.contains("prior_native_CPU"));
}
nlohmann::json admit_split_bank_backing(const nlohmann::json &,const std::string &journal,bool &GPU_started);
}
