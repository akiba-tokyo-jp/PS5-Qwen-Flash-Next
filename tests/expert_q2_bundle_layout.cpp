// SPDX-License-Identifier: MIT
#include "expert_q2_bundle_layout.h"
#include <algorithm>
#include <cstring>
#include <iostream>
#include <vector>
static void check(bool value,const char*message){if(!value)throw std::runtime_error(message);}
int main(){try{
    using L=qwen_app::ExpertQ2BundleLayout;
    std::uint64_t total=0;
    for(unsigned part=0;part<L::layers*L::parts_per_layer;++part){
        const auto n=L::part_bytes(part);check(n&&n<=L::part_limit&&n%L::alignment==0,"Part alignment or cap");total+=n;
    }
    for(unsigned layer=0;layer<L::layers;++layer)for(unsigned expert=0;expert<L::experts;++expert){
        const auto p=L::locate(layer,expert);check(p.offset%L::alignment==0&&p.bytes%L::alignment==0&&
            p.offset+p.bytes<=L::part_bytes(p.part),"Bundle crosses a part");
        for(unsigned role=0;role<3;++role)check(L::role_offset(role)+L::role_bytes[role]<=L::payload_bytes,"Role escaped original payload");
        if(expert){const auto prior=L::locate(layer,expert-1);check(prior.part!=p.part||prior.offset+prior.bytes==p.offset,"Bundle gap or alias");}
    }
    check(total==38637928448ull&&L::bundles_per_part==348,"Complete payload geometry changed");
    std::vector<unsigned char> bundle(L::stride,0);std::array<std::vector<unsigned char>,3> banks;
    for(unsigned role=0;role<3;++role){
        for(std::size_t i=0;i<L::role_bytes[role];++i)bundle[L::role_offsets[role]+i]=static_cast<unsigned char>((i*129+role*71)&255);
        banks[role].assign(L::role_bytes[role]+32,0xa5);
        std::memcpy(banks[role].data()+16,bundle.data()+L::role_offsets[role],L::role_bytes[role]);
        check(std::all_of(banks[role].begin(),banks[role].begin()+16,[](auto x){return x==0xa5;})&&
              std::all_of(banks[role].end()-16,banks[role].end(),[](auto x){return x==0xa5;}),"Role scatter canary changed");
        check(!std::memcmp(banks[role].data()+16,bundle.data()+L::role_offsets[role],L::role_bytes[role]),"Quantized role bits changed");
    }
    check(std::all_of(bundle.begin()+L::payload_bytes,bundle.end(),[](auto x){return x==0;}),"Padding contains payload");
    unsigned refused=0;for(auto pair:std::array<std::array<unsigned,2>,3>{{{{49,0}},{{0,512}},{{UINT32_MAX,UINT32_MAX}}}})
        try{(void)L::locate(pair[0],pair[1]);}catch(const std::out_of_range&){++refused;}
    try{(void)L::part_bytes(98);}catch(const std::out_of_range&){++refused;}
    try{(void)L::role_offset(3);}catch(const std::out_of_range&){++refused;}
    check(refused==5,"Invalid geometry admitted");
    std::cout<<"25,088 Expert bundles, 98 bounded parts, exact role bits, canaries and invalid geometry passed\n";
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
