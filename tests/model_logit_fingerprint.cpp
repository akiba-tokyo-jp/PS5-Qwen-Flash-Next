// SPDX-License-Identifier: MIT
#include "model_integrity.h"
#include <array>
#include <cstring>
#include <iomanip>
#include <iostream>
#include <stdexcept>
int main() {
    const std::array<std::uint32_t,8> bits{{0,0x80000000u,0x3f800001u,0xbf800001u,1,0x007fffffu,0x7f7fffffu,0xff7fffffu}};
    std::array<float,8> values{};std::memcpy(values.data(),bits.data(),sizeof(bits));
    const auto digest=qwen_app::model_logit_fingerprint(values.data(),values.size());
    unsigned refused=0;
    for(unsigned i=0;i<3;++i) {
        try{qwen_app::model_logit_fingerprint(i==0?nullptr:values.data(),i==1?0:i==2?262145:8);}
        catch(const std::invalid_argument &){++refused;}
    }
    if(refused!=3)return 2;
    values[0]=1.0f;if(qwen_app::model_logit_fingerprint(values.data(),values.size())==digest)return 3;
    std::cout<<"{\"bounds_refusals\":3,\"changed_bits_detected\":true,\"sha256\":\"";
    for(const auto byte:digest)std::cout<<std::hex<<std::setfill('0')<<std::setw(2)<<unsigned(byte);
    std::cout<<"\",\"PS5_operations\":0}"<<std::endl;
}
