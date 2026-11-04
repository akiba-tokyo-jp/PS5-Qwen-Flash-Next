// SPDX-License-Identifier: MIT
#pragma once
#include "precision_overlay_receipt.h"
#include "shared-Q4-plan.private.h"

namespace qwen_app {
// Preserve the entire selected 109-matrix receipt and validate only the
// additional 144 projections through this outer, independently sealed layer.
class SharedQ4Receipt {
    using Json=nlohmann::json;
    PrecisionOverlayReceipt parent_;
    struct Changed {std::string name;std::vector<std::uint64_t>shape;std::uint64_t bytes;};
    std::vector<Changed>changes_;
    static Json checked(const Json&r){
        if(sha256_metadata_bytes(shared_Q4_parent_raw)!=precision_candidate_sha256||
           sha256_metadata_bytes(shared_Q4_candidate_raw)!=shared_Q4_candidate_sha256||
           r!=Json::parse(shared_Q4_candidate_raw))
            throw std::runtime_error("Exact complete additional shared-Q4 layer required");
        return Json::parse(shared_Q4_parent_raw);
    }
public:
    std::uint64_t mapped_bytes;
    SharedQ4Receipt(const Json&r,const std::string&parent,const std::string&base,const std::string&original):
        parent_(checked(r),parent,base,original),mapped_bytes(parent_.mapped_bytes){
        const auto&changes=r.at("shared_Q4_overlay").at("tensors");
        if(changes.size()!=144)throw std::runtime_error("All 144 shared projections are required");
        changes_.reserve(144);
        for(const auto&c:changes){
            if(c.at("type")!="Q4_0"||c.at("control_type")!="Q8_0")
                throw std::runtime_error("Only the explicit shared-Q8 to shared-Q4 layer is admitted");
            changes_.push_back({c.at("name").get<std::string>(),c.at("shape").get<std::vector<std::uint64_t>>(),
                c.at("bytes").get<std::uint64_t>()});
        }
    }
    void tensor(const std::string&name,const std::string&type,const std::vector<std::uint64_t>&shape,std::uint64_t bytes)const{
        const auto c=std::find_if(changes_.begin(),changes_.end(),[&](const Changed&v){return v.name==name;});
        if(c==changes_.end()){parent_.tensor(name,type,shape,bytes);return;}
        if(type!="Q4_0"||bytes!=c->bytes||shape!=c->shape)throw std::runtime_error("Shared-Q4 tensor geometry changed");
    }
    void tensor_ne(const std::string&name,const std::string&type,const std::int64_t*ne,std::uint64_t bytes)const{
        const auto c=std::find_if(changes_.begin(),changes_.end(),[&](const Changed&v){return v.name==name;});
        if(c==changes_.end()){parent_.tensor_ne(name,type,ne,bytes);return;}
        if(!ne||ne[3]!=1||c->shape.size()!=2||ne[0]!=std::int64_t(c->shape[0])||ne[1]!=std::int64_t(c->shape[1])||ne[2]!=1)
            throw std::runtime_error("Shared-Q4 complete tensor extent changed");
        tensor(name,type,c->shape,bytes);
    }
};

inline bool shared_Q4_file(const nlohmann::json&r,const std::string&name){
    for(const auto&h:r.at("shared_Q4_overlay").at("headers"))if(h.at("file")==name)return true;
    return false;
}
inline void validate_shared_Q4_footprint(const ModelFootprint&m,std::uint64_t mapped){
    if(m.device_weights+117964800ull!=precision_device_bytes)
        throw std::runtime_error("Exact additional shared-Q4 device footprint required");
    auto prior=m;prior.device_weights=precision_device_bytes;validate_precision_footprint(prior,mapped);
}

inline SplitModelIntegrity shared_Q4_source_integrity(const nlohmann::json&gate,const nlohmann::json&r,
        const nlohmann::json&parent,const nlohmann::json&base,const nlohmann::json&original,
        const std::string&base_root,const std::string&parent_root,const std::string&root,std::uint64_t total){
    using Json=nlohmann::json;
    const auto need=[](unsigned line,bool ok){if(!ok)throw std::runtime_error("Complete additional shared-Q4 source proof required at line "+std::to_string(line));};
    const auto&proof=gate.at("shared_Q4_source_integrity");const auto raw=proof.at("raw").get<std::string>();
    need(__LINE__,proof.at("schema")=="ps5-qwen-additional-shared-Q4-source-policy-v1"&&!raw.empty()&&raw.size()<=(64u<<10)&&
         sha256_metadata_bytes(raw)==proof.at("sha256"));
    const auto seal=Json::parse(raw);const auto&details=r.at("shared_Q4_overlay");
    need(__LINE__,seal.at("schema")=="ps5-qwen-additional-shared-Q4-source-v1"&&
         seal.at("model_receipt_sha256")==shared_Q4_candidate_sha256&&gate.at("model_receipt_sha256")==shared_Q4_candidate_sha256&&
         seal.at("parent_model_receipt_sha256")==precision_candidate_sha256&&seal.at("source_directory")==root&&expert_q2_source_root(root)&&
         root!=shared_Q4_parent_root&&seal.at("canonical_source_directory")==std::string("/data/ai/native-moss-image-sft/PPSA99190")+root.substr(5));
    need(__LINE__,seal.at("complete_physical_and_alias_SHA256_EOF")==true&&
         seal.at("parent_518_identities_and_directory_snapshots_unchanged")==true);
    for(const char*k:{"original_source_writes","GPU_calls","title_launches","initializer_requests","mount_changes","automatic_retries"})
        need(__LINE__,seal.at(k)==0);
    const auto identity=[&](const Json&j,bool directory){
        need(__LINE__,j.is_array()&&j.size()==10);SourceIdentity key{};
        for(unsigned i=0;i<10;++i){need(__LINE__,j[i].is_number_integer()&&j[i]>=0);key[i]=j[i];}
        need(__LINE__,key[0]&&key[1]&&key[2]==(directory?0040755u:0100644u)&&!key[3]&&!key[4]&&key[5]&&
             key[7]<1000000000&&key[9]<1000000000);return key;
    };
    const auto directory=identity(seal.at("directory_identity"),true),metadata=identity(seal.at("receipt_identity"),false);
    need(__LINE__,metadata[5]==gate.at("model_receipt_bytes"));
    const auto baseline=Json::parse(shared_Q4_parent_raw);
    Json oldgate=gate;oldgate["model_receipt_sha256"]=precision_candidate_sha256;oldgate["model_receipt_bytes"]=std::strlen(precision_candidate_raw);
    auto result=precision_source_integrity(oldgate,baseline,parent,base,original,base_root,parent_root,shared_Q4_parent_root,total);
    const auto&pack=seal.at("pack");const auto pack_key=identity(pack.at("identity"),false);
    need(__LINE__,pack.at("path")==root+"/shared-q4.bin"&&pack.at("bytes")==details.at("pack").at("bytes")&&
         pack.at("sha256")==details.at("pack").at("sha256")&&pack_key[5]==pack.at("bytes"));
    const auto pack_physical=result.physical.size();result.physical.push_back({pack.at("path"),pack_key[5],pack_key});
    need(__LINE__,details.at("headers").size()==51&&seal.at("headers").size()==51);
    for(const auto&h:details.at("headers")){
        const auto name=h.at("file").get<std::string>();
        auto file=std::find_if(result.logical.begin(),result.logical.end(),[&](const auto&f){return f.path.size()>name.size()&&f.path.substr(f.path.size()-name.size())==name;});
        need(__LINE__,file!=result.logical.end());
        auto plan=std::find_if(expert_q2_pending_segments.begin(),expert_q2_pending_segments.end(),[&](const auto&p){return p.path==file->path;});
        if(plan==expert_q2_pending_segments.end()){
            std::vector<std::uint64_t>physical_bytes;for(const auto&p:result.physical)physical_bytes.push_back(p.bytes);
            expert_q2_pending_segments.push_back({file->path,output_plain_segments(file->bytes,file->parts,physical_bytes)});
            plan=expert_q2_pending_segments.end()-1;
        }
        const auto prefix=std::find_if(seal.at("headers").begin(),seal.at("headers").end(),[&](const Json&p){return p.at("file")==name;});
        need(__LINE__,prefix!=seal.at("headers").end()&&prefix->at("path")==root+"/"+name&&prefix->at("bytes")==h.at("bytes")&&prefix->at("sha256")==h.at("sha256"));
        const auto key=identity(prefix->at("identity"),false);need(__LINE__,key[5]==h.at("bytes"));
        const auto header_physical=result.physical.size();result.physical.push_back({root+"/"+name,key[5],key});
        std::vector<ExpertQ2SourceSegment>compact{{0,key[5],header_physical,0}};auto cursor=key[5];
        for(const auto&t:r.at("tensors"))if(t.at("file")==name){
            const auto bytes=receipt_integer(t,"bytes");need(__LINE__,t.at("offset")==cursor&&cursor<=file->bytes&&bytes<=file->bytes-cursor);
            const auto c=std::find_if(details.at("tensors").begin(),details.at("tensors").end(),[&](const Json&v){return v.at("name")==t.at("name");});
            if(c!=details.at("tensors").end()){
                need(__LINE__,c->at("bytes")==bytes&&c->at("payload_sha256")==t.at("payload_sha256")&&
                     receipt_integer(*c,"pack_offset")<=pack_key[5]&&bytes<=pack_key[5]-receipt_integer(*c,"pack_offset"));
                compact.push_back({cursor,bytes,pack_physical,receipt_integer(*c,"pack_offset")});
            }else{
                const auto prior=std::find_if(baseline.at("tensors").begin(),baseline.at("tensors").end(),[&](const Json&v){return v.at("name")==t.at("name");});
                need(__LINE__,prior!=baseline.at("tensors").end()&&prior->at("bytes")==bytes&&prior->at("type")==t.at("type")&&
                     prior->at("shape")==t.at("shape")&&prior->at("payload_sha256")==t.at("payload_sha256"));
                auto ranges=relocate_source_range(plan->segments,receipt_integer(*prior,"offset"),bytes,cursor);
                compact.insert(compact.end(),ranges.begin(),ranges.end());
            }
            cursor+=bytes;
        }
        if(cursor<file->bytes){auto tail=relocate_source_range(plan->segments,cursor,file->bytes-cursor,cursor);compact.insert(compact.end(),tail.begin(),tail.end());}
        (void)merge_source_overlays(compact,{},file->bytes);plan->segments=std::move(compact);
        file->path=root+"/"+name;plan->path=file->path;file->parts={header_physical};result.prior.files.at(std::size_t(file-result.logical.begin()))=key;
    }
    std::vector<bool>used(result.physical.size(),false);
    for(const auto&f:result.logical)for(auto i:f.parts){need(__LINE__,i<used.size());used[i]=true;}
    for(const auto&p:expert_q2_pending_segments)for(const auto&s:p.segments){need(__LINE__,s.physical<used.size());used[s.physical]=true;}
    std::vector<std::size_t>indices(used.size(),SIZE_MAX);std::vector<SourceFile>remaining;
    for(std::size_t i=0;i<used.size();++i)if(used[i]){indices[i]=remaining.size();remaining.push_back(result.physical[i]);}
    for(auto&f:result.logical)for(auto&i:f.parts)i=indices[i];
    for(auto&p:expert_q2_pending_segments)for(auto&s:p.segments)s.physical=indices[s.physical];
    result.physical=std::move(remaining);result.prior.directory=directory;result.prior.receipt=metadata;
    result.part_directory.clear();result.part_directory_identity=directory;
    result.prior.report_sha256=proof.at("sha256").get<std::string>();result.prior.snapshot_sha256=result.prior.report_sha256;return result;
}
}
