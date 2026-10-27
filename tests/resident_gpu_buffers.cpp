// SPDX-License-Identifier: MIT
#include "resident_gpu_buffers.h"
#include <iostream>
int main() {
    using J=nlohmann::json;const auto scope=qwen_app::resident_gpu_buffer_scope();
    J p={{"native_resident_GPU_buffer_capacity",scope}};qwen_app::require_resident_gpu_buffers(p);
    unsigned rejected=0;
    auto deny=[&](const J &value){bool refused=false;try{qwen_app::require_resident_gpu_buffers(value);}catch(...){refused=true;}
        if(!refused)throw std::runtime_error("Changed raw-buffer scope admitted");++rejected;};
    for(auto it=scope.begin();it!=scope.end();++it) {
        auto changed=p;changed["native_resident_GPU_buffer_capacity"].erase(it.key());deny(changed);
        changed=p;changed["native_resident_GPU_buffer_capacity"][it.key()]=nullptr;deny(changed);
        changed=p;
        if(it.value().is_boolean())changed["native_resident_GPU_buffer_capacity"][it.key()]=!it.value().get<bool>();
        else if(it.value().is_number_integer())changed["native_resident_GPU_buffer_capacity"][it.key()]=it.value().get<double>();
        else changed["native_resident_GPU_buffer_capacity"][it.key()]="altered";
        deny(changed);
    }
    auto changed=p;changed["native_resident_GPU_buffer_capacity"]["extra"]=1;deny(changed);
    std::cout<<rejected<<" altered buffer scopes rejected\n";
}
