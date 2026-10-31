// SPDX-License-Identifier: MIT
#include "precision_overlay_receipt.h"
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
static void check(bool ok){if(!ok)throw std::runtime_error("Precision receipt control failed");}
static std::string read(const char*p){std::ifstream f(p,std::ios::binary);check(bool(f));return{std::istreambuf_iterator<char>(f),{}};}
int main(int argc,char**argv)try{
    check(argc==5);const auto r=Json::parse(read(argv[1]));
    const auto parent=read(argv[2]),base=read(argv[3]),original=read(argv[4]);
    qwen_app::PrecisionOverlayReceipt admitted(r,parent,base,original);
    qwen_app::ModelFootprint f;f.trunk_layers=48;
    for(const auto&t:r.at("tensors")){
        const auto shape=t.at("shape").get<std::vector<std::uint64_t>>();
        admitted.tensor(t.at("name"),t.at("type"),shape,t.at("bytes"));
        std::int64_t ne[4]{1,1,1,1};for(unsigned i=0;i<shape.size();++i)ne[i]=shape[i];
        admitted.tensor_ne(t.at("name"),t.at("type"),ne,t.at("bytes"));f.tensor(t.at("name"),t.at("bytes"));
    }
    f.mapped_files=admitted.mapped_bytes;qwen_app::validate_precision_footprint(f,admitted.mapped_bytes);
    unsigned refused=0;
    for(unsigned i=0;i<8;++i){auto bad=r;auto raw=parent;
        if(i==0)bad["precision_overlay"]["tensors"].erase(bad["precision_overlay"]["tensors"].begin());
        if(i==1)bad["precision_overlay"]["parts"][0]["bytes"]=1;
        if(i==2)bad["tensors"][0]["bytes"]=1;
        if(i==3)bad["activation_quantization"]=true;
        if(i==4)raw+=' ';
        if(i==5)bad["precision_overlay"]["tensors"][0]["payload_sha256"]=std::string(64,'0');
        if(i==6)bad["precision_overlay"]["headers"][0]["sha256"]=std::string(64,'0');
        if(i==7)bad["precision_overlay"]["mode"]="other";
        try{qwen_app::PrecisionOverlayReceipt invalid(bad,raw,base,original);}
        catch(const std::exception&){++refused;}
    }
    check(refused==8);std::cout<<"PASS: all1256 tensor descriptors, exact footprint and8 ancestry/precision refusals\n";
    return 0;
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}
