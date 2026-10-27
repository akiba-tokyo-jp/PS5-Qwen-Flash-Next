// SPDX-License-Identifier: MIT
#pragma once
#include <nlohmann/json.hpp>
#include <cstdint>
#include <stdexcept>
namespace qwen_app {
struct ResidentWorkerPrice {std::uint64_t worker_pages=0,idle_pages=0;unsigned completed=0;};
inline ResidentWorkerPrice resident_worker_price(const nlohmann::json &proof,const nlohmann::json &report) {
    if(proof.at("case")!=3538||proof.at("report_bytes")!=223||
       proof.at("report_sha256")!="17e3f65b643209240bbcd83435e48bf91a45bfec9ba8eec641546cb94e5bbf6b")
        throw std::runtime_error("The exact completed four-worker qualification is required");
    const nlohmann::json expected={{"GPU_calls",0},{"IO_payload_reads",0},{"completed",true},{"lifetimes",4},
        {"maximum_matched_idle_decline_pages",0},{"maximum_sampled_worker_VM_decline_pages",2},
        {"sampled_maxima_not_universal_minima",true}};
    if(!report.is_object()||report.size()!=expected.size())throw std::runtime_error("Complete worker measurement required");
    for(auto it=expected.begin();it!=expected.end();++it) {
        const auto &actual=report.at(it.key());
        if((it.value().is_number_integer()?!actual.is_number_integer():actual.type()!=it.value().type())||actual!=it.value())
            throw std::runtime_error("Completed worker measurement differs");
    }
    return {2,0,4};
}
}
