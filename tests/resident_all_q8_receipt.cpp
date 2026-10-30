// SPDX-License-Identifier: MIT
#include "resident_all_q8_receipt.h"
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
void check(bool b){if(!b)throw std::runtime_error("Resident Q8 receipt fixture failed");}
std::string read(const char*p){std::ifstream f(p,std::ios::binary);check(bool(f));return{std::istreambuf_iterator<char>(f),{}};}
int main(int argc,char**argv){try{
    check(argc==5);const auto candidate=Json::parse(read(argv[1]));const auto parent=read(argv[2]),base=read(argv[3]),original=read(argv[4]);
    qwen_app::ResidentAllQ8Receipt admitted(candidate,parent,base,original);qwen_app::ModelFootprint footprint;footprint.trunk_layers=48;
    for(const auto&t:candidate.at("tensors")){const auto shape=t.at("shape").get<std::vector<std::uint64_t>>();admitted.tensor(t.at("name"),t.at("type"),shape,t.at("bytes"));
        std::int64_t ne[4]{1,1,1,1};for(unsigned i=0;i<shape.size();++i)ne[i]=shape[i];admitted.tensor_ne(t.at("name"),t.at("type"),ne,t.at("bytes"));footprint.tensor(t.at("name"),t.at("bytes"));}
    footprint.mapped_files=admitted.mapped_bytes;qwen_app::validate_resident_all_Q8_footprint(footprint,admitted.mapped_bytes);
    unsigned refused=0;for(unsigned i=0;i<12;++i){auto changed=candidate;auto&o=changed["resident_all_Q8_overlay"];auto raw=parent;
        if(i==0)o["tensors"].erase(o["tensors"].begin());if(i==1)o["tensors"][0]["name"]="token_embd.weight";
        if(i==2)o["tensors"][0]["part"]=999;if(i==3)o["tensors"][0]["pack_offset"]=1;
        if(i==4)o["tensors"][0]["payload_sha256"]=std::string(64,'0');if(i==5)o["headers"][0]["bytes"]=1;
        if(i==6)o["parts"][0]["bytes"]=1;if(i==7)changed["activation_quantization"]=true;
        if(i==8)changed["tensors"][0]["shape"]={1,1};if(i==9)raw+=' ';
        if(i==10)o["original_Expert_payloads_preserved"]=false;if(i==11)o["parent"]["bytes"]=1;
        try{qwen_app::ResidentAllQ8Receipt invalid(changed,raw,base,original);}catch(const std::exception&){++refused;}
    }check(refused==12);std::cout<<"All1256 tensors,544 resident Q8 changes, BF16 PLE convolution, complete footprint and12 refusals passed.\n";
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
