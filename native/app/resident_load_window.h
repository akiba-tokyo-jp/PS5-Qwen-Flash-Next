// SPDX-License-Identifier: MIT
#pragma once
#include <nlohmann/json.hpp>
#include <stdexcept>
namespace qwen_app {
inline void require_resident_load_window(const nlohmann::json &policy) {
    const nlohmann::json expected={{"schema","ps5-qwen-resident-model-load-window-v1"},{"enabled",true},
        {"model_load_maximum_read_bytes",1048576},{"postload_maximum_read_bytes",8388608},
        {"owned_CPU_scratch_bytes",8388608},{"original_bytes_and_precision_preserved",true},
        {"physical_calls_counted_per_actual_window",true},{"automatic_retries",0}};
    const auto &scope=policy.at("native_resident_model_load_window");
    if(!scope.is_object()||scope.size()!=expected.size())throw std::runtime_error("Exact model-load I/O scope required");
    for(auto i=expected.begin();i!=expected.end();++i){const auto &v=scope.at(i.key());
        if((i.value().is_number_integer()?!v.is_number_integer():v.type()!=i.value().type())||v!=i.value())
            throw std::runtime_error("Model-load I/O scope value or type differs");}
}
}
