// SPDX-License-Identifier: MIT
#include "expert_q2_composite_source.h"
#include <fstream>
#include <iostream>
using Json=nlohmann::json;
static std::string raw_file(const char*path){std::ifstream f(path,std::ios::binary);return {std::istreambuf_iterator<char>(f),{}};}
int main(int argc,char**argv){
    if(argc!=6)return 2;
    const auto model=Json::parse(raw_file(argv[1])),gate=Json::parse(raw_file(argv[2]));
    const std::string old_receipt=raw_file(argv[3]),old_proof=raw_file(argv[4]),old_layout=raw_file(argv[5]);
    const auto metadata=[&](const std::string&path,const Json&record,const qwen_app::SourceIdentity&,std::string*out){
        const auto&raw=path.find("retained-Q4-proof.json")!=std::string::npos?old_proof:
            path.find("retained-Q4-layout.json")!=std::string::npos?old_layout:old_receipt;
        if(raw.size()!=record.at("bytes")||qwen_app::sha256_metadata_bytes(raw)!=record.at("sha256"))
            throw std::runtime_error("Metadata fixture hash differs");
        if(out)*out=raw;return Json::parse(raw);
    };
    const std::string root=Json::parse(gate.at("Expert_Q2_source_integrity").at("raw").get<std::string>()).at("source_directory");
    qwen_app::ExpertQ2Receipt admitted(model);
    auto source=qwen_app::expert_q2_composite_source_integrity(gate,model,root,admitted.mapped_bytes,metadata);
    if(source.logical.size()!=76||qwen_app::expert_q2_pending_segments.size()!=74||source.physical.size()>1024)return 3;
    std::uint64_t covered=0;for(const auto&file:source.logical)covered+=file.bytes;
    if(covered!=admitted.mapped_bytes)return 4;
    unsigned refused=0;
    auto reject=[&](Json candidate,Json proof){
        qwen_app::expert_q2_pending_segments.clear();Json changed_gate=gate;
        const auto raw=proof.dump();changed_gate["Expert_Q2_source_integrity"]["raw"]=raw;
        changed_gate["Expert_Q2_source_integrity"]["sha256"]=qwen_app::sha256_metadata_bytes(raw);
        try{qwen_app::ExpertQ2Receipt shape(candidate);(void)qwen_app::expert_q2_composite_source_integrity(changed_gate,candidate,root,shape.mapped_bytes,metadata);}
        catch(const std::exception&){++refused;return;}
        throw std::runtime_error("Malformed composite plan was accepted");
    };
    const auto proof=Json::parse(gate.at("Expert_Q2_source_integrity").at("raw").get<std::string>());
    unsigned file=0;while(model["files"][file]["reused_original"]==true)++file;
    auto candidate=model;candidate["files"][file]["regions"].erase(candidate["files"][file]["regions"].begin());reject(candidate,proof);
    candidate=model;candidate["files"][file]["packed_bytes"]=1;reject(candidate,proof);
    candidate=model;candidate["files"][file]["header_bytes"]=1;reject(candidate,proof);
    candidate=model;
    for(auto&region:candidate["files"][file]["regions"])if(region["storage"]=="retained_Q4"){region["storage_offset"]=region["storage_offset"].get<std::uint64_t>()+32;break;}
    reject(candidate,proof);
    candidate=model;candidate["retained_Q4_conversion"]["sha256"]=std::string(64,'0');reject(candidate,proof);
    auto changed=proof;changed["logical_files"][file]["parts"][0]["identity"][5]=1;reject(model,changed);
    changed=proof;changed["same_existing_title_nullfs_namespace"]=false;reject(model,changed);
    changed=proof;changed["original_BF16_directories_and_parts_unchanged"]=false;reject(model,changed);
    candidate=model;candidate["KV_quantization"]=true;reject(candidate,proof);
    if(refused!=9)return 5;
    std::cout<<"{\"complete_mixed_source_metadata_passed\":true,\"logical_files\":76,\"composite_files\":74,\"physical_sources\":"<<source.physical.size()<<",\"invalid_candidates_refused\":9,\"metadata_fixture_only\":true,\"PS5_operations\":0}\n";
}
