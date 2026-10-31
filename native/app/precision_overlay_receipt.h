// SPDX-License-Identifier: MIT
#pragma once
#include <cstring>
#include "resident_all_q8_source.h"
#include "precision-plan.private.h"

namespace qwen_app {
inline bool precision_file(const nlohmann::json&r,const std::string&name){
    for(const auto&h:r.at("precision_overlay").at("headers"))if(h.at("file")==name)return true;
    return false;
}

class PrecisionOverlayReceipt {
    using Json=nlohmann::json;
    ResidentAllQ8Receipt parent_;
    struct ChangedTensor {std::string name,type;std::vector<std::uint64_t>shape;std::uint64_t bytes;};
    std::vector<ChangedTensor>changes_;
    static Json checked(const Json&r){
        if(sha256_metadata_bytes(precision_parent_raw)!=precision_parent_sha256||
           sha256_metadata_bytes(precision_candidate_raw)!=precision_candidate_sha256||
           r!=Json::parse(precision_candidate_raw))
            throw std::runtime_error("Exact complete precision candidate and parent required");
        return Json::parse(precision_parent_raw);
    }
public:
    std::uint64_t mapped_bytes;
    PrecisionOverlayReceipt(const Json&r,const std::string&parent,const std::string&base,const std::string&original):
        parent_(checked(r),parent,base,original),mapped_bytes(parent_.mapped_bytes){
        const auto&tensors=r.at("tensors");const auto&changes=r.at("precision_overlay").at("tensors");
        changes_.reserve(changes.size());
        for(const auto&c:changes){
            const auto t=std::find_if(tensors.begin(),tensors.end(),[&](const Json&v){return v.at("name")==c.at("name");});
            if(t==tensors.end())throw std::runtime_error("Selected precision tensor is missing");
            changes_.push_back({c.at("name").get<std::string>(),c.at("type").get<std::string>(),
                t->at("shape").get<std::vector<std::uint64_t>>(),c.at("bytes").get<std::uint64_t>()});
        }
    }
    void tensor(const std::string&name,const std::string&type,
                const std::vector<std::uint64_t>&shape,std::uint64_t bytes)const{
        const auto c=std::find_if(changes_.begin(),changes_.end(),[&](const ChangedTensor&v){return v.name==name;});
        if(c==changes_.end()){parent_.tensor(name,type,shape,bytes);return;}
        if(type!=c->type||bytes!=c->bytes||shape!=c->shape)
            throw std::runtime_error("Precision candidate tensor geometry changed");
    }
    void tensor_ne(const std::string&name,const std::string&type,const std::int64_t*ne,std::uint64_t bytes)const{
        if(!ne||ne[3]!=1)throw std::runtime_error("Precision candidate tensor rank changed");
        const auto c=std::find_if(changes_.begin(),changes_.end(),[&](const ChangedTensor&v){return v.name==name;});
        if(c==changes_.end()){parent_.tensor_ne(name,type,ne,bytes);return;}
        const auto&shape=c->shape;
        if(shape.size()>3)throw std::runtime_error("Precision candidate rank exceeds its exact model");
        for(unsigned i=0;i<3;++i)if(ne[i]!=std::int64_t(i<shape.size()?shape[i]:1))
            throw std::runtime_error("Precision candidate tensor extent changed");
        tensor(name,type,shape,bytes);
    }
};

inline void validate_precision_footprint(const ModelFootprint&m,std::uint64_t mapped){
    if(m.trunk_layers!=48||m.tensors!=1256||m.device_weights!=precision_device_bytes||
       m.mapped_experts!=precision_expert_bytes||m.lazy_ple!=102400491520ull||
       m.mapped_embeddings!=1271398400ull||m.skipped_mtp!=970284032ull||
       m.largest_device_tensor!=675430400ull||m.mapped_files!=mapped)
        throw std::runtime_error("Complete precision candidate footprint changed");
}

inline SplitModelIntegrity precision_source_integrity(const nlohmann::json&gate,
        const nlohmann::json&r,const nlohmann::json&parent,const nlohmann::json&base,
        const nlohmann::json&original,const std::string&base_root,
        const std::string&parent_root,const std::string&root,std::uint64_t total){
    using Json=nlohmann::json;
    const auto need=[](unsigned line,bool ok){if(!ok)throw std::runtime_error("Complete immutable precision source proof required at line "+std::to_string(line));};
    const auto&proof=gate.at("precision_source_integrity");
    need(__LINE__,proof.at("schema")=="ps5-qwen-precision-source-policy-v1");
    const auto raw=proof.at("raw").get<std::string>();
    need(__LINE__,!raw.empty()&&raw.size()<=(128u<<10)&&sha256_metadata_bytes(raw)==proof.at("sha256"));
    const auto seal=Json::parse(raw);const auto&details=r.at("precision_overlay");
    need(__LINE__,seal.at("schema")=="ps5-qwen-precision-native-source-v1"&&seal.at("completed")==true&&
         seal.at("model_receipt_sha256")==precision_candidate_sha256&&
         gate.at("model_receipt_sha256")==precision_candidate_sha256&&
         seal.at("parent_model_receipt_sha256")==precision_parent_sha256&&
         seal.at("source_directory")==root&&expert_q2_source_root(root)&&root!=precision_parent_root&&
         seal.at("canonical_source_directory")==std::string("/data/ai/native-moss-image-sft/PPSA99190")+root.substr(5));
    for(const char*k:{"all_new_parts_complete_Direct_SHA256_readback","all_parts_unchanged_since_readback",
        "CPU_owners_positively_closed","all_original_sources_preserved","header_prefixes_extracted_and_sealed",
        "previous_pack_and_receipt_identities_unchanged"})need(__LINE__,seal.at(k)==true);
    for(const char*k:{"GPU_calls","title_launches","automatic_retries","original_source_writes",
                     "production_permission_changes","mount_changes"})need(__LINE__,seal.at(k)==0);
    const auto identity=[&](const Json&j){need(__LINE__,j.is_array()&&j.size()==10);SourceIdentity out{};
        for(unsigned i=0;i<10;++i){need(__LINE__,j[i].is_number_integer()&&j[i]>=0);out[i]=j[i];}
        need(__LINE__,out[0]&&out[1]&&!out[3]&&!out[4]&&out[5]&&out[7]<1000000000&&out[9]<1000000000);return out;};
    const auto directory=identity(seal.at("directory_identity")),metadata=identity(seal.at("receipt_identity"));
    need(__LINE__,directory[2]==0040755&&metadata[2]==0100644&&metadata[5]==gate.at("model_receipt_bytes"));
    const auto baseline=Json::parse(precision_parent_raw);
    Json oldgate=gate;oldgate["model_receipt_sha256"]=precision_parent_sha256;
    oldgate["model_receipt_bytes"]=std::strlen(precision_parent_raw);
    auto result=resident_all_Q8_source_integrity(oldgate,baseline,parent,base,original,
                                                base_root,parent_root,precision_parent_root,total);
    need(__LINE__,seal.at("parts").size()==details.at("parts").size());std::vector<std::size_t>physical;
    for(std::size_t i=0;i<details.at("parts").size();++i){
        const auto&p=seal.at("parts")[i];const auto&e=details.at("parts")[i];const auto key=identity(p.at("identity"));
        const auto path=root+"/precision.part"+std::to_string(i)+".bin";
        need(__LINE__,p.at("path")==path&&p.at("bytes")==e.at("bytes")&&p.at("sha256")==e.at("sha256")&&key[2]==0100644&&key[5]==p.at("bytes"));
        physical.push_back(result.physical.size());result.physical.push_back({path,key[5],key});
    }
    need(__LINE__,seal.at("headers").size()==details.at("headers").size());
    for(const auto&h:details.at("headers")){
        const auto name=h.at("file").get<std::string>();
        auto file=std::find_if(result.logical.begin(),result.logical.end(),[&](const auto&f){return f.path.size()>name.size()&&f.path.substr(f.path.size()-name.size())==name;});need(__LINE__,file!=result.logical.end());
        auto plan=std::find_if(expert_q2_pending_segments.begin(),expert_q2_pending_segments.end(),[&](const auto&p){return p.path==file->path;});need(__LINE__,plan!=expert_q2_pending_segments.end());
        const auto prefix=std::find_if(seal.at("headers").begin(),seal.at("headers").end(),[&](const Json&p){return p.at("file")==name;});
        need(__LINE__,prefix!=seal.at("headers").end()&&prefix->at("path")==root+"/"+name&&prefix->at("bytes")==h.at("bytes")&&prefix->at("sha256")==h.at("sha256"));
        const auto key=identity(prefix->at("identity"));need(__LINE__,key[2]==0100644&&key[5]==h.at("bytes"));
        const auto header_physical=result.physical.size();result.physical.push_back({root+"/"+name,key[5],key});
        std::vector<ExpertQ2SourceSegment>compact{{0,receipt_integer(h,"bytes"),header_physical,0}};
        auto cursor=receipt_integer(h,"bytes");
        for(const auto&t:r.at("tensors"))if(t.at("file")==name){
            const auto bytes=receipt_integer(t,"bytes");need(__LINE__,t.at("offset")==cursor&&cursor<=file->bytes&&bytes<=file->bytes-cursor);
            const auto c=std::find_if(details.at("tensors").begin(),details.at("tensors").end(),[&](const Json&v){return v.at("name")==t.at("name");});
            if(c!=details.at("tensors").end()){
                const auto part=receipt_integer(*c,"part");need(__LINE__,part<physical.size());
                compact.push_back({cursor,bytes,physical[part],receipt_integer(*c,"pack_offset")});
            }else{
                const auto prior=std::find_if(baseline.at("tensors").begin(),baseline.at("tensors").end(),[&](const Json&v){return v.at("name")==t.at("name");});
                need(__LINE__,prior!=baseline.at("tensors").end()&&prior->at("bytes")==bytes&&prior->at("type")==t.at("type")&&prior->at("shape")==t.at("shape")&&prior->at("payload_sha256")==t.at("payload_sha256"));
                auto ranges=relocate_source_range(plan->segments,receipt_integer(*prior,"offset"),bytes,cursor);
                compact.insert(compact.end(),ranges.begin(),ranges.end());
            }
            cursor+=bytes;
        }
        if(cursor<file->bytes){auto tail=relocate_source_range(plan->segments,cursor,file->bytes-cursor,cursor);compact.insert(compact.end(),tail.begin(),tail.end());}
        (void)merge_source_overlays(compact,{},file->bytes);plan->segments=std::move(compact);
        file->path=root+"/"+name;plan->path=file->path;file->parts={header_physical};
        result.prior.files.at(std::size_t(file-result.logical.begin()))=key;
    }
    std::vector<bool>used(result.physical.size(),false);
    for(const auto&f:result.logical)for(auto i:f.parts){need(__LINE__,i<used.size());used[i]=true;}
    for(const auto&p:expert_q2_pending_segments)for(const auto&s:p.segments){need(__LINE__,s.physical<used.size());used[s.physical]=true;}
    std::vector<std::size_t>indices(used.size(),SIZE_MAX);std::vector<SourceFile>remaining;
    for(std::size_t i=0;i<used.size();++i)if(used[i]){indices[i]=remaining.size();remaining.push_back(result.physical[i]);}
    for(auto&f:result.logical)for(auto&i:f.parts){need(__LINE__,indices[i]!=SIZE_MAX);i=indices[i];}
    for(auto&p:expert_q2_pending_segments)for(auto&s:p.segments){need(__LINE__,indices[s.physical]!=SIZE_MAX);s.physical=indices[s.physical];}
    result.physical=std::move(remaining);result.prior.directory=directory;result.prior.receipt=metadata;
    result.part_directory.clear();result.part_directory_identity=directory;
    result.prior.report_sha256=proof.at("sha256").get<std::string>();
    result.prior.snapshot_sha256=result.prior.report_sha256;return result;
}
}
