// SPDX-License-Identifier: MIT
// Replay the complete host metadata plan through the actual native admission policy.
#include "memory_admission.h"
#include "nlohmann/json.hpp"
#include <fstream>
#include <iostream>
#include <stdexcept>
using namespace qwen_app;
using Json = nlohmann::json;
static void check(bool value) { if (!value) throw std::runtime_error("Full model footprint mismatch"); }
template<class Function> void reject(Function function) {
    bool failed=false;try {function();} catch(const std::exception &) {failed=true;}check(failed);
}
int main(int argc,char ** argv) {
    try {
        if(argc!=2) throw std::invalid_argument("A host metadata plan is required");
        std::ifstream input(argv[1]);Json plan;input>>plan;
        ModelFootprint model;model.trunk_layers=plan.at("trunk_layers").get<unsigned>();
        for(const auto & item:plan.at("tensors").items()) model.tensor(item.key(),item.value().at("bytes").get<std::uint64_t>());
        const auto & expected=plan.at("footprint_bytes");
        check(model.device_weights==expected.at("device_weights").get<std::uint64_t>());
        check(model.mapped_experts==expected.at("mapped_experts").get<std::uint64_t>());
        check(model.lazy_ple==expected.at("lazy_ple").get<std::uint64_t>());
        check(model.mapped_embeddings==expected.at("mapped_embeddings").get<std::uint64_t>());
        check(model.skipped_mtp==expected.at("skipped_mtp").get<std::uint64_t>());
        check(model.tensors==plan.at("tensor_count").get<std::uint64_t>());
        check(model.largest_device_tensor==plan.at("largest_device_tensor_bytes").get<std::uint64_t>());
        model.mapped_files=model.device_weights+model.mapped_experts+model.lazy_ple+model.mapped_embeddings+model.skipped_mtp;
        MemoryBudget budget;
        check(budget.device_requirement(model)==plan.at("planned_device_requirement_bytes").get<std::uint64_t>());
        const auto needed=budget.device_requirement(model);
        MemoryObservation synthetic{needed,needed,budget.cpu_working+budget.os_reserve,model.largest_device_tensor};
        budget.admit(model,synthetic);
        auto insufficient=synthetic;--insufficient.driver_free;reject([&]{budget.admit(model,insufficient);});
        insufficient=synthetic;--insufficient.direct_largest;reject([&]{budget.admit(model,insufficient);});
        insufficient=synthetic;--insufficient.os_free;reject([&]{budget.admit(model,insufficient);});
        insufficient=synthetic;--insufficient.device_max_buffer;reject([&]{budget.admit(model,insufficient);});
        reject([&]{budget.admit(model,{});});
        std::cout<<model.tensors<<" actual planned tensors match native placement and budget; synthetic observations only\n";
    } catch(const std::exception & error) {std::cerr<<error.what()<<'\n';return 1;}
}
