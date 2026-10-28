// SPDX-License-Identifier: MIT
#pragma once
#include "system_memory.h"
#include <nlohmann/json.hpp>
namespace qwen_app {
inline void require_resident_phase_VM(const nlohmann::json &policy,const nlohmann::json &buffer_report,bool existing_window=false) {
    nlohmann::json expected={{"schema","ps5-qwen-resident-phase-VM-v1"},{"enabled",true},
        {"source_window_extra_pages",19},{"GPU_initializer_extra_pages",10},{"context_extra_pages",245},
        {"startup_settle_samples",51},{"startup_settle_interval_us",100000},
        {"historical_whole_interval_is_per_operation_cost",false},
        {"completed_indexed_fixture_uses_operational_and_next_window_reserves",true},
        {"original_Direct_Flexible_heap_and_completion_guards",true},{"automatic_retries",0}};
    if(existing_window)expected.update({{"schema","ps5-qwen-resident-phase-VM-v2"},
        {"source_window_extra_pages",0},{"new_Direct_allocation_extra_pages",19},
        {"source_buffer_owned_before_GPU",true},{"per_read_Direct_allocation_and_mapping_calls",0},
        {"context_extra_pages",43},{"context_observed_maximum_decline_pages",41},
        {"context_selected_margin_pages",2},{"universal_context_peak_bound_established",false}});
    const auto &scope=policy.at("native_resident_phase_VM");
    if(!scope.is_object()||scope.size()!=expected.size())throw std::runtime_error("Exact phase-local VM scope required");
    for(auto it=expected.begin();it!=expected.end();++it){const auto &actual=scope.at(it.key());
        if((it.value().is_number_integer()?!actual.is_number_integer():actual.type()!=it.value().type())||actual!=it.value())
            throw std::runtime_error("Phase-local VM scope differs");}
    const auto &proof=policy.at("native_resident_buffer_qualification");
    if(proof.at("case")!=3643||proof.at("report_bytes")!=3178||
       proof.at("report_sha256")!="66ad9bbcb2e4fa45ecffee0e4f29a9367d934049759932970f49d85bcc30c94d"||
       buffer_report.at("pid")!=proof.at("pid")||buffer_report.at("run_id")!=proof.at("run_id")||
       buffer_report.at("completed")!=true||buffer_report.at("unknown_completion")!=false||
       buffer_report.at("model_loads")!=0||buffer_report.at("graph_computes")!=0||
       buffer_report.at("backend_instance_positively_synchronized_and_retired")!=true)
        throw std::runtime_error("Actual original-size buffer qualification required");
    const auto &b=buffer_report.at("buffer_capacity_measurement");
    if(b.at("all_five_allocated")!=true||b.at("allocated_buffers")!=5||b.at("requested_live_peak_bytes")!=8755105280ull||
       b.at("buffer_free_callbacks_returned")!=5||b.at("live_calibration_buffer_objects")!=0||b.at("queue_submissions")!=0||
       b.at("driver_owned_bytes_at_peak").get<std::uint64_t>()<b.at("driver_owned_bytes_before").get<std::uint64_t>()+8755105280ull)
        throw std::runtime_error("Complete original-size allocation prefix required");
}
inline void require_resident_source_VM(const SystemMemoryObservation &m) {
    (void)qualified_system_headroom(m);
    const auto floor=std::uint64_t(m.kernel_minimum)+std::max<std::uint64_t>(m.kernel_reserved,256);
    if(m.kernel_free<floor+19)throw KernelMemoryPressure();
}
inline void require_resident_existing_source_VM(const SystemMemoryObservation &m) {
    // This operation reuses the already allocated/mapped 8 MiB CPU window.
    // Keep the original operational reserve; do not reprice a new allocation.
    (void)qualified_system_headroom(m);
}
// Defined only in the explicit app-source overlay; production stays unchanged.
void enable_resident_source_VM();
}
