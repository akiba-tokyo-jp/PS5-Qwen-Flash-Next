// SPDX-License-Identifier: MIT
// Replay completed routing metadata through the actual policy, without inference.
#include "expert_policy.h"
#include <nlohmann/json.hpp>
#include <fstream>
#include <iostream>
using Json=nlohmann::json;
int main(int argc,char **argv) {
    const bool sweep=argc==3&&std::string(argv[2])=="--research-capacity-sweep";
    if(argc!=2&&!sweep)return 2;std::ifstream input(argv[1]);const auto records=Json::parse(input);
    if(!records.is_array()||records.size()!=3)return 3;
    Json output=Json::array();
    const std::vector<unsigned> capacities=sweep?std::vector<unsigned>{53,54,64,80,96,112,128,144,160}:std::vector<unsigned>{53,54};
    for(unsigned slots:capacities) {
        qwen_app::ExpertPolicy policy;std::vector<std::int32_t> keys;Json requests=Json::array();std::uint64_t external=0;
        for(std::size_t request=0;request<3;++request) {
            if(records.at(request).at("cache_reset_before_request").get<bool>()!=(request<2))return 4;
            if(request<2){policy.reset(49,512,slots,48);keys.assign(slots,-1);}
            std::uint64_t hits=0,misses=0,unique=0;
            for(const auto &row:records.at(request).at("records")) {
                const auto layer=row.at("layer").get<std::int32_t>();auto selected=row.at("ids").get<std::vector<std::int32_t>>();
                std::sort(selected.begin(),selected.end());selected.erase(std::unique(selected.begin(),selected.end()),selected.end());
                if(layer<0||layer>=48||selected.size()<10||selected.size()>40||(!sweep&&(slots-selected.size())/48!=0))return 5;
                for(auto expert:selected)if(expert<0||expert>=512)return 6;
                policy.observe(layer,selected);unique+=selected.size();
                for(auto expert:selected) {
                    const auto key=layer*512+expert;
                    if(std::find(keys.begin(),keys.end(),key)!=keys.end()){++hits;continue;}
                    const auto slot=policy.victim(keys,layer,selected);if(slot<0||unsigned(slot)>=slots)return 7;
                    keys.at(slot)=key;++misses;
                }
                for(auto expert:selected)if(std::find(keys.begin(),keys.end(),layer*512+expert)==keys.end())return 8;
            }
            if(request)external+=misses*9830400;
            requests.push_back({{"hits",hits},{"misses",misses},{"unique",unique}});
        }
        output.push_back({{"slots",slots},{"requests",requests},{"external_uploaded_bytes",external}});
    }
    std::cout<<output<<std::endl;
}
