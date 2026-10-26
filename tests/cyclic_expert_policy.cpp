// SPDX-License-Identifier: MIT
#include "cyclic_expert_policy.h"
#include <nlohmann/json.hpp>
#include <fstream>
#include <iostream>
int main(int argc,char **argv) {
    if(argc!=2)return 2;std::ifstream input(argv[1]);const auto records=nlohmann::json::parse(input);
    if(!records.is_array()||records.size()!=3)return 3;
    nlohmann::json result=nlohmann::json::array();
    for(auto mode:{qwen_app::CyclicEviction::control,qwen_app::CyclicEviction::layer_distance,qwen_app::CyclicEviction::frequency_over_distance}) {
        std::unique_ptr<qwen_app::CyclicExpertPolicy> policy;std::vector<std::int32_t> keys;nlohmann::json requests=nlohmann::json::array();
        for(std::size_t i=0;i<records.size();++i) {
            if(records[i].at("cache_reset_before_request").get<bool>()!=(i<2))return 4;
            if(i<2){policy=std::make_unique<qwen_app::CyclicExpertPolicy>(mode);keys.assign(53,-1);}
            std::uint64_t hits=0,misses=0,unique=0;
            for(const auto &row:records[i].at("records")) {
                const auto layer=row.at("layer").get<std::int32_t>();auto selected=row.at("ids").get<std::vector<std::int32_t>>();
                std::sort(selected.begin(),selected.end());selected.erase(std::unique(selected.begin(),selected.end()),selected.end());
                policy->observe(layer,selected);unique+=selected.size();
                for(auto expert:selected) {
                    const auto key=layer*512+expert;
                    if(std::find(keys.begin(),keys.end(),key)!=keys.end()){++hits;continue;}
                    const auto slot=policy->victim(keys,layer,selected);if(slot<0||slot>=53)return 5;
                    keys[slot]=key;++misses;
                }
                for(auto expert:selected)if(std::find(keys.begin(),keys.end(),layer*512+expert)==keys.end())return 6;
            }
            requests.push_back({{"hits",hits},{"misses",misses},{"unique",unique}});
        }
        result.push_back({{"mode",int(mode)},{"requests",requests}});
    }
    std::cout<<result<<std::endl;
}
