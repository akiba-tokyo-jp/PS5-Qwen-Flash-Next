// SPDX-License-Identifier: MIT
#pragma once
#include "resident_shared_q8_source.h"
#include "resident_all_q8_receipt.h"
namespace qwen_app {
inline SplitModelIntegrity resident_all_Q8_source_integrity(const nlohmann::json&gate,
        const nlohmann::json&r,const nlohmann::json&parent,const nlohmann::json&base,const nlohmann::json&original,
        const std::string&base_root,const std::string&parent_root,const std::string&root,std::uint64_t total){
    using Json=nlohmann::json;const auto need=[](bool b){if(!b)throw std::runtime_error("Complete immutable resident-Q8 source proof required");};
    const auto&proof=gate.at("resident_all_Q8_source_integrity");need(proof.at("schema")=="ps5-qwen-all-resident-Q8-source-policy-v1");
    const auto raw=proof.at("raw").get<std::string>();need(!raw.empty()&&raw.size()<=(128u<<10)&&sha256_metadata_bytes(raw)==proof.at("sha256"));
    const auto seal=Json::parse(raw);const auto&details=r.at("resident_all_Q8_overlay");
    need(seal.at("schema")=="ps5-qwen-all-resident-Q8-native-source-v1"&&seal.at("completed")==true&&seal.at("model_receipt_sha256")==gate.at("model_receipt_sha256")&&seal.at("parent_model_receipt_sha256")==all_Q8_parent_SHA256);
    need(seal.at("source_directory")==root&&expert_q2_source_root(root)&&root!=parent_root&&root!=base_root&&seal.at("canonical_source_directory")==std::string("/data/ai/native-moss-image-sft/PPSA99190")+root.substr(5));
    for(const char*k:{"all_new_parts_complete_Direct_SHA256_readback","all_parts_unchanged_since_readback","CPU_owners_positively_closed","all_original_sources_preserved","header_prefixes_extracted_and_sealed","previous_pack_and_receipt_identities_unchanged"})need(seal.at(k)==true);
    for(const char*k:{"GPU_calls","title_launches","automatic_retries","original_source_writes","production_permission_changes","mount_changes"})need(seal.at(k)==0);
    const auto identity=[&](const Json&j){need(j.is_array()&&j.size()==10);SourceIdentity out{};for(unsigned i=0;i<10;++i){need(j[i].is_number_integer()&&j[i]>=0);out[i]=j[i];}
        need(out[0]&&out[1]&&!out[3]&&!out[4]&&out[5]&&out[7]<1000000000&&out[9]<1000000000);return out;};
    const auto directory=identity(seal.at("directory_identity")),metadata=identity(seal.at("receipt_identity"));need(directory[2]==0040755&&metadata[2]==0100644&&metadata[5]==gate.at("model_receipt_bytes"));
    Json oldgate=gate;oldgate["model_receipt_sha256"]=all_Q8_parent_SHA256;oldgate["model_receipt_bytes"]=details.at("parent").at("bytes");
    auto result=resident_shared_Q8_source_integrity(oldgate,parent,base,original,base_root,parent_root,total);
    need(seal.at("parts").size()==details.at("parts").size());std::vector<std::size_t>physical;
    for(std::size_t i=0;i<details.at("parts").size();++i){const auto&p=seal.at("parts")[i];const auto&expected=details.at("parts")[i];const auto key=identity(p.at("identity"));
        const auto path=root+"/resident-all-Q8.part"+std::to_string(i)+".bin";need(p.at("path")==path&&p.at("bytes")==expected.at("bytes")&&p.at("sha256")==expected.at("sha256")&&key[2]==0100644&&key[5]==p.at("bytes"));
        physical.push_back(result.physical.size());result.physical.push_back({path,key[5],key});
    }
    need(seal.at("headers").size()==details.at("headers").size());
    for(const auto&h:details.at("headers")){const auto name=h.at("file").get<std::string>();
        auto file=std::find_if(result.logical.begin(),result.logical.end(),[&](const auto&f){return f.path.size()>name.size()&&f.path.substr(f.path.size()-name.size())==name;});need(file!=result.logical.end());
        auto plan=std::find_if(expert_q2_pending_segments.begin(),expert_q2_pending_segments.end(),[&](const auto&p){return p.path==file->path;});need(plan!=expert_q2_pending_segments.end());
        (void)merge_source_overlays(plan->segments,{},file->bytes);
        const auto prefix=std::find_if(seal.at("headers").begin(),seal.at("headers").end(),[&](const Json&p){return p.at("file")==name;});
        need(prefix!=seal.at("headers").end()&&prefix->at("path")==root+"/"+name&&prefix->at("bytes")==h.at("bytes")&&prefix->at("sha256")==h.at("sha256"));
        const auto key=identity(prefix->at("identity"));need(key[2]==0100644&&key[5]==h.at("bytes"));const auto header_physical=result.physical.size();result.physical.push_back({root+"/"+name,key[5],key});
        std::vector<ExpertQ2SourceSegment>compact{{0,receipt_integer(h,"bytes"),header_physical,0}};auto cursor=receipt_integer(h,"bytes");
        for(const auto&t:r.at("tensors"))if(t.at("file")==name){const auto bytes=receipt_integer(t,"bytes");need(t.at("offset")==cursor&&cursor<=file->bytes&&bytes<=file->bytes-cursor);
            const auto c=std::find_if(details.at("tensors").begin(),details.at("tensors").end(),[&](const Json&v){return v.at("name")==t.at("name");});
            if(c!=details.at("tensors").end()){const auto part=receipt_integer(*c,"part");need(part<physical.size());compact.push_back({cursor,bytes,physical[part],receipt_integer(*c,"pack_offset")});}
            else{const auto prior=std::find_if(parent.at("tensors").begin(),parent.at("tensors").end(),[&](const Json&v){return v.at("name")==t.at("name");});
                need(prior!=parent.at("tensors").end()&&prior->at("bytes")==bytes&&prior->at("type")==t.at("type")&&prior->at("shape")==t.at("shape")&&prior->at("payload_sha256")==t.at("payload_sha256"));
                auto ranges=relocate_source_range(plan->segments,receipt_integer(*prior,"offset"),bytes,cursor);compact.insert(compact.end(),ranges.begin(),ranges.end());}
            cursor+=bytes;
        }
        if(cursor<file->bytes){auto tail=relocate_source_range(plan->segments,cursor,file->bytes-cursor,cursor);compact.insert(compact.end(),tail.begin(),tail.end());}
        (void)merge_source_overlays(compact,{},file->bytes);plan->segments=std::move(compact);file->path=root+"/"+name;plan->path=file->path;file->parts={header_physical};result.prior.files.at(std::size_t(file-result.logical.begin()))=key;
    }
    std::vector<bool>used(result.physical.size(),false);for(const auto&f:result.logical)for(auto i:f.parts){need(i<used.size());used[i]=true;}
    for(const auto&p:expert_q2_pending_segments)for(const auto&s:p.segments){need(s.physical<used.size());used[s.physical]=true;}
    std::vector<std::size_t>indices(used.size(),SIZE_MAX);std::vector<SourceFile>remaining;
    for(std::size_t i=0;i<used.size();++i)if(used[i]){indices[i]=remaining.size();remaining.push_back(result.physical[i]);}
    for(auto&f:result.logical)for(auto&i:f.parts){need(indices[i]!=SIZE_MAX);i=indices[i];}
    for(auto&p:expert_q2_pending_segments)for(auto&s:p.segments){need(indices[s.physical]!=SIZE_MAX);s.physical=indices[s.physical];}
    result.physical=std::move(remaining);result.prior.directory=directory;result.prior.receipt=metadata;result.part_directory.clear();result.part_directory_identity=directory;
    result.prior.report_sha256=proof.at("sha256").get<std::string>();result.prior.snapshot_sha256=result.prior.report_sha256;return result;
}
}
