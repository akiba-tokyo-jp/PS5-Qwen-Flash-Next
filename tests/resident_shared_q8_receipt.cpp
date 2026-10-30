// SPDX-License-Identifier: MIT
#include "resident_shared_q8_receipt.h"
#include <fstream>
#include <iostream>
extern "C" {
#include "hash/sha256/sha256.h"
}
namespace qwen_app {
std::string sha256_metadata_bytes(const std::string&raw){sha256_t h;sha256_init(&h);sha256_update(&h,reinterpret_cast<const unsigned char*>(raw.data()),raw.size());
    unsigned char bytes[32];sha256_final(&h,bytes);std::string s;for(auto b:bytes){s+="0123456789abcdef"[b>>4];s+="0123456789abcdef"[b&15];}return s;}
}
using Json=nlohmann::json;
void check(bool b){if(!b)throw std::runtime_error("Shared Q8 receipt check failed");}
std::string read(const char*p){std::ifstream f(p,std::ios::binary);check(bool(f));return{std::istreambuf_iterator<char>(f),{}};}
int main(int argc,char**argv){try{
    check(argc==4);const auto candidate=Json::parse(read(argv[1]));const auto base=read(argv[2]),original=read(argv[3]);
    qwen_app::ResidentSharedQ8Receipt admitted(candidate,base,original);unsigned checked=0;
    for(const auto&t:candidate.at("tensors")){const auto shape=t.at("shape").get<std::vector<std::uint64_t>>();
        admitted.tensor(t.at("name"),t.at("type"),shape,t.at("bytes"));std::int64_t ne[4]{1,1,1,1};for(unsigned i=0;i<shape.size();++i)ne[i]=shape[i];
        admitted.tensor_ne(t.at("name"),t.at("type"),ne,t.at("bytes"));++checked;}
    check(checked==1256&&admitted.mapped_bytes==150561081472ull);unsigned refused=0;
    for(unsigned test=0;test<12;++test){auto changed=candidate;auto raw=base;auto&o=changed["resident_Q8_overlay"];
        if(test==0)o["tensors"].erase(o["tensors"].begin());if(test==1)o["tensors"][0]["name"]="output.weight";
        if(test==2)o["tensors"][0]["pack_offset"]=1;if(test==3)o["headers"][0]["bytes"]=1;
        if(test==4)changed["files"][0]["bytes"]=1;if(test==5)changed["activation_quantization"]=true;
        if(test==6)changed["candidate_whole_GGUF_hash_claimed"]=true;if(test==7)raw+=' ';
        if(test==8)o["tensors"][0]["parent_payload_sha256"]=std::string(64,'0');if(test==9)o["overlays"][0]["bytes"]=1;
        if(test==10)o["pack"]["bytes"]=1;if(test==11)changed["base_output_Q8_receipt_ref"]["sha256"]=std::string(64,'0');
        try{qwen_app::ResidentSharedQ8Receipt invalid(changed,raw,original);}catch(const std::exception&){++refused;}
    }check(refused==12);std::cout<<"All1256 real tensors,144 active shared projections and12 invalid scope/source controls passed.\n";
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
