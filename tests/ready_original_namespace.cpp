// SPDX-License-Identifier: MIT
#include "ready_original_namespace.h"
#include <iostream>
using namespace qwen_app;
int main(){
    const SourceIdentity directory{{1,2,0040755,0,0,64,7,0,7,0}},receipt{{1,3,0100644,0,0,90,7,0,7,0}};
    auto app_directory=directory,app_receipt=receipt;app_directory[0]=app_receipt[0]=9;
    nlohmann::json policy={{"schema","ps5-qwen-ready-original-app-namespace-v1"},{"canonical_root","/data/source/model"},
        {"directory_identity",directory},{"receipt_identity",receipt},{"allow_app0_device_translation",true}};
    ReadyOriginalPlan plan;plan.sha256=std::string(64,'a');plan.original_receipt_sha256=std::string(64,'b');
    plan.files.push_back({"/data/source/model/part",90,receipt});
    auto bound=bind_ready_original_app_namespace(plan,policy,app_directory,app_receipt);
    if(bound.sha256!=plan.sha256||bound.original_receipt_sha256!=plan.original_receipt_sha256||
        bound.files[0].path!="/app0/qwen-runtime/model/part"||bound.files[0].identity[0]!=9||plan.files[0].identity[0]!=1)return 2;
    unsigned refusals=0;
    const auto reject=[&](const auto &p,const auto &pol,const auto &d,const auto &r){
        try{(void)bind_ready_original_app_namespace(p,pol,d,r);}catch(const std::exception &){++refusals;return;}
        throw std::runtime_error("Altered original namespace admitted");};
    for(unsigned i=0;i<10;++i){auto d=app_directory,r=app_receipt;++d[i];reject(plan,policy,d,app_receipt);++r[i];reject(plan,policy,app_directory,r);}
    for(const char *path:{"/data/source/model-other/part","/data/source/model/../part","/data/source/model/"}){
        auto p=plan;p.files[0].path=path;reject(p,policy,app_directory,app_receipt);}
    {auto p=plan;p.files[0].identity[0]=3;reject(p,policy,app_directory,app_receipt);}
    for(const auto *key:{"schema","canonical_root","directory_identity","receipt_identity","allow_app0_device_translation"}){
        auto p=policy;p.erase(key);reject(plan,p,app_directory,app_receipt);}
    {auto p=policy;p["allow_app0_device_translation"]=false;reject(plan,p,app_directory,app_receipt);}
    auto same=bind_ready_original_app_namespace(plan,policy,directory,receipt);
    if(same.files[0].identity!=receipt)return 3;
    std::cout<<"{\"passed\":true,\"namespace_refusals\":"<<refusals<<"}\n";
}
