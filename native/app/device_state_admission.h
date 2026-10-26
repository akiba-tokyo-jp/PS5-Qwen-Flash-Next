// SPDX-License-Identifier: MIT
#pragma once
#include <nlohmann/json.hpp>
#include <stdexcept>
#include <string>
namespace qwen_app {
inline constexpr std::uint64_t device_state_fixture_bytes=136ull<<20;
inline void require_device_state_policy(const nlohmann::json &policy,bool display) {
    const auto &p=policy.at("native_device_state_validation");
    if(display||!p.is_object()||p.size()!=11||p.at("schema")!="ps5-qwen-device-state-fixture-v1"||p.at("enabled")!=true||
       p.at("driver_revision")!="872cc1264ad8ba5d6b888b092968fa5858a38c58"||p.at("profile")!="cumulative-idle"||
       p.at("native_archive_sha256")!="b57fe26e969940d147be05c1ffae830503d4865877281dffe03af32328f49925"||
       p.at("model_loading_enabled")!=false||p.at("persistent_caches_enabled")!=false||
       !p.at("state_bytes").is_number_unsigned()||p.at("state_bytes")!=device_state_fixture_bytes||
       !p.at("maximum_GPU_memory_bytes").is_number_unsigned()||p.at("maximum_GPU_memory_bytes")!=536870912u||
       !p.at("cases").is_number_unsigned()||p.at("cases")!=8u)
        throw std::runtime_error("Exact original-F32 device-state fixture policy required");
    const auto &source=p.at("source");
    if(!source.is_object()||source.size()!=3||source.at("path")!="/app0/qwen-runtime/vector-bank-0.pack"||
       !source.at("bytes").is_number_unsigned()||source.at("bytes")!=63488000u||
       source.at("sha256")!="4d6247378c577a586d8cc552b14c771f63a732f8b9762ead8405612aea2d371d")
        throw std::runtime_error("The unchanged bounded source-owner prerequisite is required");
    const auto &storage=policy.at("native_shader_storage");
    if(storage.at("enabled")!=true||storage.at("verify_all_original_assets_before_Vulkan")!=true||
       storage.at("model_and_shader_precision_unchanged")!=true||storage.at("persistent_caches_enabled")!=false||storage.contains("prior_native_CPU"))
        throw std::runtime_error("All current CPU shader inputs must precede the device-state fixture");
}
bool device_state_fixture_linked();
nlohmann::json admit_device_state_fixture(const nlohmann::json &,const std::string &);
}
