// SPDX-License-Identifier: MIT
#include "source_read_schedule.h"
#include "padded_bank.h"
#include <nlohmann/json.hpp>
#include <fstream>
#include <iostream>
#include <vector>
int main(int argc,char **argv) {
    if(argc!=2)return 2;
    using Json=nlohmann::ordered_json;
    std::ifstream input(argv[1]);Json data;input>>data;
    const auto files=data.at("files").get<std::vector<std::array<std::uint64_t,10>>>();
    Json results=Json::array();
    for(const auto &packet:data.at("packets")) {
        if(packet.empty()||packet.size()>2)return 3;
        bool direct=true;std::array<std::uint64_t,2> aligned{};
        std::array<std::size_t,2> bytes{},indices{};
        std::array<std::uint64_t,2> offsets{};
        for(unsigned i=0;i<packet.size();++i) {
            indices[i]=packet[i][0].get<std::size_t>();offsets[i]=packet[i][1].get<std::uint64_t>();
            if(indices[i]>=files.size())return 4;
            direct&=qwen_app::padded_source_envelope(offsets[i],files[indices[i]][5],aligned[i],bytes[i]);
        }
        const bool adjacent=packet.size()==2&&indices[0]==indices[1]&&offsets[1]>=offsets[0]&&
            offsets[1]-offsets[0]==qwen_app::bank_expert_bytes;
        direct&=!adjacent;
        const bool parallel=direct&&packet.size()==2&&qwen_app::source_schedule_parallel(
            files[indices[0]],aligned[0],bytes[0],files[indices[1]],aligned[1],bytes[1]);
        results.push_back({direct,parallel,bytes[0]+bytes[1],adjacent});
    }
    std::cout<<results.dump()<<'\n';
}
