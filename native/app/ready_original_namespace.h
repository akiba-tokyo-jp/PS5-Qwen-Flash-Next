// SPDX-License-Identifier: MIT
#pragma once
#include "ready_original_source.h"
#include "model_identity_namespace.h"
namespace qwen_app {
inline void require_ready_original_namespace(const nlohmann::json &p) {
    const auto check=[](bool good){if(!good)throw std::invalid_argument("Exact original application namespace required");};
    check(p.is_object()&&p.size()==5&&p.at("schema")=="ps5-qwen-ready-original-app-namespace-v1"&&
        p.at("allow_app0_device_translation")==true);
    const auto root=p.at("canonical_root").get<std::string>();
    check(root.rfind("/data/",0)==0&&root.size()<1024&&root.back()!='/'&&root.find("..") ==std::string::npos&&
        root.find('\0')==std::string::npos&&root.find('\\')==std::string::npos);
    for(const auto *name:{"directory_identity","receipt_identity"}) {
        const auto &id=p.at(name);check(id.is_array()&&id.size()==10);
        for(const auto &v:id)check(v.is_number_unsigned());
        check(id[0]>0u&&id[1]>0u&&id[5]>0u&&(id[2].get<std::uint64_t>()&0022)==0);
    }
    check((p.at("directory_identity")[2].get<std::uint64_t>()&0170000)==0040000&&
        (p.at("receipt_identity")[2].get<std::uint64_t>()&0170000)==0100000);
}
// Reuse the production two-anchor null-mount binding. Only the device ID and
// exact path prefix change; every inode, mode, owner, size and timestamp stays
// sealed. The canonical manifest/hash continues to identify the original data.
inline ReadyOriginalPlan bind_ready_original_app_namespace(const ReadyOriginalPlan &canonical,const nlohmann::json &p,
        const SourceIdentity &directory,const SourceIdentity &receipt) {
    require_ready_original_namespace(p);
    const auto expected_directory=p.at("directory_identity").get<SourceIdentity>();
    const auto expected_receipt=p.at("receipt_identity").get<SourceIdentity>();
    const ModelIdentityNamespace names(expected_directory,directory,expected_receipt,receipt,true);
    const auto prefix=p.at("canonical_root").get<std::string>()+"/";
    auto bound=canonical;
    for(auto &f:bound.files) {
        if(f.path.rfind(prefix,0)!=0||f.path.size()==prefix.size()||f.identity[0]!=names.source_device()||
            f.path.find("..")!=std::string::npos||f.path.find('\0')!=std::string::npos||f.path.find('\\')!=std::string::npos)
            throw std::invalid_argument("Original part lies outside its sealed model namespace");
        f.path="/app0/qwen-runtime/model/"+f.path.substr(prefix.size());
        f.identity[0]=names.application_device();
    }
    return bound;
}
}
