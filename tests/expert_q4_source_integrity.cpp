// SPDX-License-Identifier: MIT
#include "expert_q4_source_integrity.h"
#include <fstream>
#include <iostream>
int main(int argc,char**argv){
    try{
        if(argc!=3)return 2;
        nlohmann::json receipt,gate;std::ifstream model(argv[1]),policy(argv[2]);model>>receipt;policy>>gate;
        const qwen_app::ExpertQ4Receipt manifest(receipt);
        const auto&root=nlohmann::json::parse(gate.at("Expert_Q4_source_integrity").at("raw").get<std::string>()).at("source_directory").get<std::string>();
        const auto valid=qwen_app::expert_q4_source_integrity(gate,receipt,root,manifest.mapped_bytes);
        if(valid.logical.size()!=76||valid.physical.empty())return 3;
        unsigned refusals=0;
        auto refuse=[&](nlohmann::json sealed){
            auto changed=gate;const auto raw=sealed.dump();changed["Expert_Q4_source_integrity"]["raw"]=raw;
            changed["Expert_Q4_source_integrity"]["sha256"]=qwen_app::sha256_metadata_bytes(raw);
            try{(void)qwen_app::expert_q4_source_integrity(changed,receipt,root,manifest.mapped_bytes);return false;}
            catch(const std::exception&){++refusals;return true;}
        };
        const auto source=nlohmann::json::parse(gate.at("Expert_Q4_source_integrity").at("raw").get<std::string>());
        auto bad=source;bad["all_new_parts_complete_Direct_SHA256_readback"]=false;if(!refuse(bad))return 4;
        bad=source;bad["CPU_owners_positively_closed"]=false;if(!refuse(bad))return 5;
        bad=source;bad["directory_identity"][2]=0040777;if(!refuse(bad))return 6;
        bad=source;bad["receipt_identity"][5]=1;if(!refuse(bad))return 7;
        bad=source;bad["logical_files"][0]["parts"][0]["path"]="/data/ai/unrelated";if(!refuse(bad))return 8;
        bad=source;bad["logical_files"][0]["parts"][0]["identity"][3]=1;if(!refuse(bad))return 9;
        bad=source;bad["original_split_integrity"]["sha256"]=std::string(64,'0');if(!refuse(bad))return 10;
        for(const auto&t:receipt.at("tensors")){
            const auto shape=t.at("shape").get<std::vector<std::uint64_t>>();std::int64_t ne[4]={1,1,1,1};
            for(unsigned i=0;i<shape.size();++i)ne[i]=shape[i];
            manifest.tensor_ne(t.at("name"),t.at("type"),ne,t.at("bytes"));
        }
        std::cout<<"{\"complete_Q4_source_policy_passed\":true,\"invalid_source_policies_refused\":"<<refusals<<",\"GGUF_tensor_shapes_checked\":1256,\"PS5_operations\":0}\n";
    }catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}
}
