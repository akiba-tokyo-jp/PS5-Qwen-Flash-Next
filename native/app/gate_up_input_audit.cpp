// SPDX-License-Identifier: MIT
#include "gate_up_input_audit.h"
namespace {qwen_app::GateUpInputAudit audit;}
extern "C" void qwen_observe_gate_up_inputs(const ggml_tensor*up,const ggml_tensor*gate,int layer) noexcept {
    audit.observe(up,gate,layer);
}
namespace qwen_app {
nlohmann::json gate_up_input_audit_report(){
    const auto s=audit.snapshot();const auto all=(std::uint64_t(1)<<48)-1;
    std::uint64_t layers=0;for(auto mask:s.layer_masks)layers|=mask;
    return {{"schema","ps5-qwen-Gate-Up-input-identity-v1"},{"completed",true},
        {"scope","Metadata identity during actual native graph construction"},{"calls",s.calls},
        {"unsupported",s.unsupported},{"geometry_failures",s.geometry_failures},
        {"input_pointer_mismatches",s.input_mismatches},{"ID_pointer_mismatches",s.ID_mismatches},
        {"width_buckets",{1,2,30,32,"other"}},{"width_calls",s.width_calls},{"layer_masks",s.layer_masks},
        {"all48_layers_observed",layers==all},{"all_observed_inputs_and_IDs_identical",s.calls&&layers==all&&
            !s.unsupported&&!s.geometry_failures&&!s.input_mismatches&&!s.ID_mismatches},
        {"tensor_values_read",0},{"retained_tensor_pointers",0},{"graph_operations_added",0},
        {"GPU_calls_added",0},{"scheduler_splits_added",0},{"new_activation_streams",0},
        {"calibration_scope","Previously captured Up moments may cover Gate only for the observed unchanged graph/input scope"}};
}
}
