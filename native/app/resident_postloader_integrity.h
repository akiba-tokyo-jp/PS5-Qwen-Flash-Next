// SPDX-License-Identifier: MIT
#pragma once
#include <nlohmann/json.hpp>
#include <stdexcept>
namespace qwen_app {
inline void require_resident_postloader_integrity(const nlohmann::json &policy) {
    const nlohmann::json expected={{"schema","ps5-qwen-postloader-SELF-integrity-v1"},{"enabled",true},
        {"full_current_SELF_SHA256_required",true},{"maximum_read_window_bytes",1048576},
        {"additional_VM_pages",19},{"maximum_passes",1},{"GPU_before_completion",false},
        {"automatic_retries",0},{"cache_recovery_assumed_before_measurement",false}};
    const auto &scope=policy.at("native_resident_postloader_integrity");
    if(!scope.is_object()||scope.size()!=expected.size())throw std::runtime_error("Exact postloader SELF scope required");
    for(auto i=expected.begin();i!=expected.end();++i){const auto &v=scope.at(i.key());
        if((i.value().is_number_integer()?!v.is_number_integer():v.type()!=i.value().type())||v!=i.value())
            throw std::runtime_error("Postloader SELF scope value or type differs");}
}
}
