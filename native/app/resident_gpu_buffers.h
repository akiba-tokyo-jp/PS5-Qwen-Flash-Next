// SPDX-License-Identifier: MIT
#pragma once
#include <nlohmann/json.hpp>
#include <stdexcept>
namespace qwen_app {
inline nlohmann::json resident_gpu_buffer_scope() {
    return {{"schema","ps5-qwen-resident-GPU-buffer-capacity-v1"},{"enabled",true},
        {"owner_explicitly_accepted_freeze_risk",true},{"reboot_available",false},
        {"original_model_weight_bytes",8755105280ull},{"maximum_buffer_bytes",2147483648ull},
        {"maximum_buffers",5},{"Direct_reserve_bytes",536870912ull},
        {"Flexible_reserve_bytes",268435456ull},{"selected_per_buffer_future_VM_pages",512},
        {"model_loads",0},{"graphs",0},{"queue_submissions",0},
        {"ordinary_OS_close_releases_physical_backing",true},{"automatic_retries",0}};
}
inline void require_resident_gpu_buffers(const nlohmann::json &p) {
    const auto &value=p.at("native_resident_GPU_buffer_capacity");const auto expected=resident_gpu_buffer_scope();
    if(!value.is_object()||value.size()!=expected.size())throw std::runtime_error("Exact GPU buffer measurement scope required");
    for(auto it=expected.begin();it!=expected.end();++it) {
        const auto &actual=value.at(it.key());
        if((it.value().is_number_integer()?!actual.is_number_integer():actual.type()!=it.value().type())||actual!=it.value())
            throw std::runtime_error("GPU buffer scope type or value differs");
    }
}
}
