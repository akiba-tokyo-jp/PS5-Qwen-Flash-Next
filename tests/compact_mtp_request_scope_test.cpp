// SPDX-License-Identifier: MIT
#include "compact_mtp_request_scope.h"
#include <iostream>
template<class F>void reject(F f){try{f();}catch(const std::runtime_error&){return;}throw std::runtime_error("Invalid compact scope accepted");}
int main(){try{
    for(unsigned i=0;i<3;++i){std::uint64_t before[]={6u*i,i},after[]={6u*(i+1),i+1};qwen_app::require_compact_mtp_request(before,after,6,1);}
    std::uint64_t before[]={6,1},after[]={12,2};
    reject([&]{qwen_app::require_compact_mtp_request(nullptr,after,6,1);});
    reject([&]{qwen_app::require_compact_mtp_request(before,nullptr,6,1);});
    reject([&]{qwen_app::require_compact_mtp_request(before,after,0,0);});
    reject([&]{qwen_app::require_compact_mtp_request(before,after,7,1);});
    reject([&]{qwen_app::require_compact_mtp_request(before,after,6,7);});
    reject([&]{qwen_app::require_compact_mtp_request(before,after,5,1);});
    reject([&]{qwen_app::require_compact_mtp_request(before,after,6,0);});
    std::uint64_t backwards_attempt[]={5,2},backwards_reject[]={12,0};
    reject([&]{qwen_app::require_compact_mtp_request(before,backwards_attempt,6,1);});
    reject([&]{qwen_app::require_compact_mtp_request(before,backwards_reject,6,1);});
    std::cout<<"Three observed-shape transitions and nine refusal controls passed\n";return 0;
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
