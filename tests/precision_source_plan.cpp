// SPDX-License-Identifier: MIT
#include <fstream>
#include <iostream>
#include <nlohmann/json.hpp>
namespace qwen_app {inline nlohmann::json source_inventory_backing=nlohmann::json::array();}
#include "precision_overlay_receipt.h"
extern "C" {
#include "hash/sha256/sha256.h"
}
namespace qwen_app {
std::string sha256_metadata_bytes(const std::string&raw){sha256_t h;sha256_init(&h);sha256_update(&h,reinterpret_cast<const unsigned char*>(raw.data()),raw.size());unsigned char bytes[32];sha256_final(&h,bytes);std::string s;for(auto b:bytes){s+="0123456789abcdef"[b>>4];s+="0123456789abcdef"[b&15];}return s;}
}
static std::string read(const char*p){std::ifstream f(p,std::ios::binary);if(!f)throw std::runtime_error("Fixture input unavailable");return{std::istreambuf_iterator<char>(f),{}};}
int main(int argc,char**argv)try{
    if(argc!=6)return 2;using Json=nlohmann::json;
    const auto policy=Json::parse(read(argv[1])),model=Json::parse(read(argv[2]));const auto parent=read(argv[3]),base=read(argv[4]),original=read(argv[5]);
    qwen_app::PrecisionOverlayReceipt admitted(model,parent,base,original);
    const auto&gate=policy.at("native_first_generation_validation");const auto seal=Json::parse(gate.at("precision_source_integrity").at("raw").get<std::string>());
    auto plan=qwen_app::precision_source_integrity(gate,model,Json::parse(parent),Json::parse(base),Json::parse(original),
        "/app0/expert-q2-07f574937f4a9197361a1afb90eef86c","/app0/expert-q2-17b2aba8c41844c84be0500971730e8b",seal.at("source_directory"),admitted.mapped_bytes);
    if(plan.logical.size()!=76||plan.physical.empty())throw std::runtime_error("Complete source plan required");
    std::cout<<"PASS: actual immutable source parser,76 logical files,"<<plan.physical.size()<<" physical owners\n";return 0;
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}
