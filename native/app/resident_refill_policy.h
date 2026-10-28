// SPDX-License-Identifier: MIT
#pragma once
#include "resident_additional_policy.h"
namespace qwen_app {
inline void require_resident_refill_policy(const nlohmann::json &policy) {
    auto expected=resident_additional_scope("cache",53);
    expected["schema"]="ps5-qwen-resident-six-demand-comparison-v1";
    expected["maximum_requests"]=5;expected["matched_groups"]=2;
    const auto &scope=policy.at("native_resident_comparison");
    if(!scope.is_object()||scope.size()!=expected.size())throw std::runtime_error("Exact six-demand model cohort required");
    for(auto it=expected.begin();it!=expected.end();++it){const auto &actual=scope.at(it.key());
        if((it.value().is_number_integer()?!actual.is_number_integer():actual.type()!=it.value().type())||actual!=it.value())
            throw std::runtime_error("Six-demand model cohort value or type differs");}
    auto original=policy;original["native_resident_comparison"]=resident_additional_scope("cache",53);
    require_resident_additional_policy(original,"cache");
}
}
