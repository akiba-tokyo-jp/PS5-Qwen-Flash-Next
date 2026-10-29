// SPDX-License-Identifier: MIT
#pragma once
#include "expert_all_q2_source_integrity.h"
#include "resident_output_q8_receipt.h"
namespace qwen_app {
// Replace only the parent's resident output source. All other logical ranges,
// quantized payloads and native identity proofs stay bound to the closed parent.
inline SplitModelIntegrity resident_output_Q8_source_integrity(const nlohmann::json&gate,
        const nlohmann::json&r,const nlohmann::json&parent,const std::string&root,std::uint64_t total){
    using Json=nlohmann::json;const auto need=[](bool b){if(!b)throw std::runtime_error("Complete isolated output Q8 source proof required");};
    const auto&proof=gate.at("resident_output_Q8_source_integrity");
    need(proof.at("schema")=="ps5-qwen-resident-output-Q8-source-policy-v1");
    const auto raw=proof.at("raw").get<std::string>();need(!raw.empty()&&raw.size()<=(64u<<10)&&sha256_metadata_bytes(raw)==proof.at("sha256"));
    const auto sealed=Json::parse(raw);
    need(sealed.at("schema")=="ps5-qwen-resident-output-Q8-native-source-v1"&&sealed.at("completed")==true&&
        sealed.at("model_receipt_sha256")==gate.at("model_receipt_sha256")&&
        sealed.at("parent_model_receipt_sha256")==resident_output_Q8_parent_SHA256&&
        sealed.at("source_directory")==root&&expert_q2_source_root(root)&&
        sealed.at("canonical_source_directory")==std::string("/data/ai/native-moss-image-sft/PPSA99190")+root.substr(5));
    for(const char*k:{"all_new_parts_complete_Direct_SHA256_readback","all_parts_unchanged_since_readback","CPU_owners_positively_closed","all_original_sources_preserved"})need(sealed.at(k)==true);
    for(const char*k:{"GPU_calls","title_launches","automatic_retries","original_source_writes","production_permission_changes","mount_changes"})need(sealed.at(k)==0);
    const auto key=[&](const Json&v){need(v.is_array()&&v.size()==10);SourceIdentity out{};
        for(unsigned i=0;i<10;++i){need(v[i].is_number_unsigned()||(v[i].is_number_integer()&&v[i]>=0));out[i]=v[i];}
        need(out[0]&&out[1]&&!out[3]&&!out[4]&&out[5]&&out[7]<1000000000&&out[9]<1000000000);return out;};
    const auto directory=key(sealed.at("directory_identity")),metadata=key(sealed.at("receipt_identity"));
    need(directory[2]==0040755&&metadata[2]==0100644&&metadata[5]==gate.at("model_receipt_bytes"));
    const auto oldproof=Json::parse(gate.at("Expert_all_Q2_source_integrity").at("raw").get<std::string>());
    const auto parent_root=oldproof.at("source_directory").get<std::string>();need(parent_root!=root&&expert_q2_source_root(parent_root));
    Json oldgate=gate;oldgate["model_receipt_sha256"]=resident_output_Q8_parent_SHA256;oldgate["model_receipt_bytes"]=r.at("parent_all_Q2_receipt_ref").at("bytes");
    auto result=expert_all_q2_source_integrity(oldgate,parent,parent_root,receipt_integer(parent,"mapped_file_bytes"));
    need(result.logical.size()==76&&result.prior.files.size()==76&&result.logical.back().bytes==1271398560ull&&
        total+resident_output_Q8_saved_bytes==receipt_integer(parent,"mapped_file_bytes"));
    const auto name=r.at("files").back().at("path").get<std::string>();const auto&parts=sealed.at("parts");
    need(parts.is_array()&&parts.size()==2);auto&last=result.logical.back();last.path=root+"/"+name;last.bytes=675430560;last.parts.clear();
    std::uint64_t offset=0;
    for(unsigned i=0;i<2;++i){const auto&p=parts[i];const auto native=root+"/"+(i?"output-Q8.part1.bin":name);const auto expected=i?138559648ull:536870912ull;
        const auto identity=key(p.at("identity"));need(p.at("path")==native&&p.at("offset")==offset&&p.at("bytes")==expected&&identity[2]==0100644&&identity[5]==expected&&
            p.at("sha256")==r.at("resident_output_Q8").at("parts")[i].at("sha256"));
        last.parts.push_back(result.physical.size());result.physical.push_back({native,expected,identity});offset+=expected;
    }
    need(offset==last.bytes);result.prior.files.back()=result.physical[last.parts.front()].identity;
    // Drop only now-unreferenced old output parts and remap every retained
    // composite segment. The source reader still requires complete coverage.
    std::vector<bool>used(result.physical.size(),false);
    for(const auto&f:result.logical)for(auto i:f.parts){need(i<used.size());used[i]=true;}
    for(const auto&p:expert_q2_pending_segments)for(const auto&s:p.segments){need(s.physical<used.size());used[s.physical]=true;}
    std::vector<std::size_t>indices(used.size(),SIZE_MAX);std::vector<SourceFile>physical;
    for(std::size_t i=0;i<used.size();++i)if(used[i]){indices[i]=physical.size();physical.push_back(result.physical[i]);}
    for(auto&f:result.logical)for(auto&i:f.parts){need(indices[i]!=SIZE_MAX);i=indices[i];}
    for(auto&p:expert_q2_pending_segments)for(auto&s:p.segments){need(indices[s.physical]!=SIZE_MAX);s.physical=indices[s.physical];}
    result.physical=std::move(physical);result.prior.directory=directory;result.prior.receipt=metadata;
    result.part_directory.clear();result.part_directory_identity=directory;
    result.prior.report_sha256=proof.at("sha256").get<std::string>();result.prior.snapshot_sha256=result.prior.report_sha256;
    return result;
}
}
