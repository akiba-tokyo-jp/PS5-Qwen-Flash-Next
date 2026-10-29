// SPDX-License-Identifier: MIT
#include "resident_output_q8_receipt.h"
#include <fstream>
#include <iostream>
extern "C" {
#include "hash/sha256/sha256.h"
}
namespace qwen_app {
std::string sha256_metadata_bytes(const std::string&raw){
    sha256_t h;sha256_init(&h);sha256_update(&h,reinterpret_cast<const unsigned char*>(raw.data()),raw.size());
    unsigned char bytes[32];sha256_final(&h,bytes);std::string s;
    for(auto b:bytes){s+="0123456789abcdef"[b>>4];s+="0123456789abcdef"[b&15];}return s;
}
}
using Json=nlohmann::json;
static void require(bool b){if(!b)throw std::runtime_error("Output-only Q8 receipt control failed");}
static std::string read(const char*p){std::ifstream f(p,std::ios::binary);require(bool(f));return{std::istreambuf_iterator<char>(f),{}};}
int main(int argc,char**argv){try{
    require(argc==3);auto candidate=Json::parse(read(argv[1]));const auto parent=read(argv[2]);
    const qwen_app::ResidentOutputQ8Receipt admitted(candidate,parent);
    require(admitted.mapped_bytes==150561081472ull);unsigned checked=0;
    for(const auto&t:candidate.at("tensors")){admitted.tensor(t.at("name"),t.at("type"),t.at("shape").get<std::vector<std::uint64_t>>(),t.at("bytes"));++checked;}
    require(checked==1256);unsigned refused=0;
    for(unsigned test=0;test<13;++test){auto changed=candidate;auto raw=parent;
        if(test==0)changed["non_Expert_payload_bytes_preserved"]=true;
        if(test==1)changed["all_Experts_retained"]=false;
        if(test==2)changed["tensors"].erase(changed["tensors"].begin());
        if(test==3)changed["files"][7]["sha256"]=std::string(64,'0');
        if(test==4)changed["resident_output_Q8"]["parts"][1]["offset"]=0;
        if(test==5)changed["parent_all_Q2_receipt_ref"]["sha256"]=std::string(64,'0');
        if(test==6)raw+=' ';
        if(test==7)changed["activation_quantization"]=true;
        if(test==8)changed["KV_quantization"]=true;
        if(test==9)changed["non_Expert_except_output_payload_bytes_preserved"]=false;
        if(test>=10)for(auto&t:changed["tensors"])if(t["name"]=="output.weight"){
            if(test==10)t["type"]="BF16";if(test==11)t["bytes"]=675430418ull;if(test==12)t["shape"][0]=2592;
        }
        try{qwen_app::ResidentOutputQ8Receipt invalid(changed,raw);}catch(const std::exception&){++refused;}
    }
    require(refused==13);
    try{admitted.tensor("output.weight","BF16",{2560,248320},1271398400);throw 1;}catch(const std::runtime_error&){}
    try{admitted.tensor("missing","Q8_0",{2560,248320},675430400);throw 1;}catch(const std::runtime_error&){}
    std::cout<<"All 1256 real tensors, exact parent SHA and 15 scope/type/source negative controls passed\n";
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
