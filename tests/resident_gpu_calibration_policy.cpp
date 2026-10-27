// SPDX-License-Identifier: MIT
#include "resident_gpu_calibration_policy.h"
#include <iostream>
int main() {
    using J=nlohmann::json;
    J p={{"native_resident_GPU_initialization_calibration",qwen_app::resident_gpu_calibration_scope()},
        {"native_resident_comparison",{{"CPU_startup_calibration",true}}}};
    qwen_app::require_resident_gpu_calibration_policy(p);unsigned rejected=0;
    auto deny=[&](const J &bad){bool refused=false;try{qwen_app::require_resident_gpu_calibration_policy(bad);}catch(...){refused=true;}
        if(!refused)throw std::runtime_error("Altered GPU initializer calibration admitted");++rejected;};
    const auto expected=qwen_app::resident_gpu_calibration_scope();
    for(auto i=expected.begin();i!=expected.end();++i) {
        auto x=p;x["native_resident_GPU_initialization_calibration"].erase(i.key());deny(x);
        x=p;x["native_resident_GPU_initialization_calibration"][i.key()]=nullptr;deny(x);
        if(i.value().is_number_integer()) {x=p;x["native_resident_GPU_initialization_calibration"][i.key()]=i.value().get<double>();deny(x);}
        else if(i.value().is_boolean()) {x=p;x["native_resident_GPU_initialization_calibration"][i.key()]=!i.value().get<bool>();deny(x);}
    }
    auto x=p;x["native_resident_comparison"]["CPU_startup_calibration"]=false;deny(x);
    x=p;x["native_resident_GPU_initialization_calibration"]["extra"]=0;deny(x);
    x=p;x["native_resident_GPU_initialization_calibration"]["additional_operational_pages"]=1024;deny(x);
    x=p;x["native_resident_GPU_initialization_calibration"]["total_above_kernel_minimum_pages"]=1024;deny(x);
    const J proof={{"VM_before_GPU",{{"wired",34719},{"active",22130}}},
        {"VM_after_GPU_and_retirement",{{"wired",34911},{"active",22164}}}};
    if(qwen_app::resident_gpu_phase_component(proof)!=245)throw std::runtime_error("Population movements or Direct/idle allowance changed");
    std::cout<<rejected<<" altered initializer scopes rejected\n";
}
