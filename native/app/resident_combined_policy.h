// SPDX-License-Identifier: MIT
#pragma once
#include "resident_comparison_policy.h"
namespace qwen_app {
inline nlohmann::json resident_combined_scope() {
    auto result=resident_comparison_scope(false);
    result["schema"]="ps5-qwen-resident-combined-comparison-v1";
    result["maximum_requests"]=19;result["warmup_requests"]=2;
    result["prefix_matched_groups"]=4;
    return result;
}
inline void require_resident_combined_policy(const nlohmann::json &policy) {
    const auto &scope=policy.at("native_resident_comparison");const auto expected=resident_combined_scope();
    if(!scope.is_object()||scope.size()!=expected.size())throw std::runtime_error("Exact combined comparison required");
    for(auto i=expected.begin();i!=expected.end();++i){const auto &v=scope.at(i.key());
        if((i.value().is_number_integer()?!v.is_number_integer():v.type()!=i.value().type())||v!=i.value())
            throw std::runtime_error("Combined comparison type or value differs");}
    auto original=policy;original["native_resident_comparison"]=resident_comparison_scope(false);
    require_resident_comparison_policy(original);
}
}
