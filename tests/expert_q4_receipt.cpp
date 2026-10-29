// SPDX-License-Identifier: MIT
#include "expert_q4_receipt.h"
#include <fstream>
#include <iostream>

int main(int argc,char **argv) {
    if(argc!=2)return 2;
    nlohmann::json receipt;std::ifstream input(argv[1]);input>>receipt;
    qwen_app::ExpertQ4Receipt valid(receipt);
    unsigned refusals=0;
    auto refuse=[&](nlohmann::json candidate) {
        try{qwen_app::ExpertQ4Receipt rejected(candidate);return false;}
        catch(const std::exception&){++refusals;return true;}
    };
    auto changed=receipt;changed["KV_quantization"]=true;if(!refuse(changed))return 3;
    changed=receipt;changed["tensors"].erase(changed["tensors"].begin());if(!refuse(changed))return 4;
    changed=receipt;changed["files"][0]["original_sha256"]=std::string(64,'0');if(!refuse(changed))return 5;
    bool quantized=false,dense=false;
    for(std::size_t i=0;i<receipt["tensors"].size();++i) {
        const auto &tensor=receipt["tensors"][i];
        if(!quantized && tensor["type"]=="Q4_0") {
            changed=receipt;changed["tensors"][i]["shape"][2]=511;if(!refuse(changed))return 6;
            valid.tensor(tensor["name"],"Q4_0",tensor["shape"].get<std::vector<std::uint64_t>>(),tensor["bytes"]);
            try{valid.tensor(tensor["name"],"BF16",tensor["shape"].get<std::vector<std::uint64_t>>(),tensor["bytes"]);return 7;}
            catch(const std::exception&){++refusals;}
            quantized=true;
        } else if(!dense && tensor["type"]!="Q4_0") {
            changed=receipt;changed["tensors"][i]["type"]="Q4_0";if(!refuse(changed))return 8;dense=true;
        }
    }
    qwen_app::ModelFootprint footprint;
    footprint.trunk_layers=48;footprint.mapped_files=valid.mapped_bytes;
    for(const auto &t:receipt["tensors"])footprint.tensor(t["name"],t["bytes"]);
    qwen_app::validate_expert_q4_footprint(footprint,valid.mapped_bytes);
    if(!dense || !quantized || refusals!=6)return 9;
    std::cout<<"{\"Expert_Q4_metadata_and_footprint_passed\":true,\"invalid_candidates_refused\":6,\"console_operations\":0}\n";
}
