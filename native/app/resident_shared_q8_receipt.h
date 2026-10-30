// SPDX-License-Identifier: MIT
#pragma once
#include "resident_output_q8_receipt.h"
#include <set>
#include <cstring>
namespace qwen_app {
inline constexpr const char*shared_Q8_base_SHA256="458c4b06bcc4c77fa23ce7d1fb6fadf5901439504e712be024e0cc3bf625a6fb";
inline constexpr std::uint64_t shared_Q8_saved_bytes=221184000;
inline bool resident_shared_Q8_file(const nlohmann::json&r,const std::string&name){
    for(const auto&h:r.at("resident_Q8_overlay").at("headers"))if(h.at("file")==name)return true;return false;
}
inline bool resident_shared_Q8_name(const char*name){
    if(!name||std::strncmp(name,"blk.",4))return false;const char*p=name+4;unsigned layer=0,digits=0;
    while(*p>='0'&&*p<='9'){layer=layer*10+unsigned(*p++-'0');if(++digits>2||layer>=48)return false;}
    if(!digits||*p++!='.')return false;
    return !std::strcmp(p,"ffn_gate_shexp.weight")||!std::strcmp(p,"ffn_up_shexp.weight")||!std::strcmp(p,"ffn_down_shexp.weight");
}
class ResidentSharedQ8Receipt {
    using Json=nlohmann::json;
    ResidentOutputQ8Receipt parent_;
    Json changes_;
    static Json checked_base(const Json&r,const std::string&raw){
        if(raw.empty()||raw.size()>(1u<<20)||sha256_metadata_bytes(raw)!=shared_Q8_base_SHA256)
            throw std::runtime_error("Exact installed output-Q8 base receipt required");
        const Json base=Json::parse(raw);Json expected=base;
        const auto&overlay=r.at("resident_Q8_overlay");const auto&pack=overlay.at("pack");const auto&changes=overlay.at("tensors");
        const auto hash=[](const Json&j){const auto s=j.get<std::string>();return s.size()==64&&s.find_first_not_of("0123456789abcdef")==std::string::npos;};
        if(overlay.at("schema")!="ps5-qwen-resident-shared-Q8-overlay-v1"||overlay.at("family")!="active_shared_Expert_projections"||
           overlay.at("saved_resident_payload_bytes")!=shared_Q8_saved_bytes||changes.size()!=144||
           !receipt_integer(pack,"bytes")||receipt_integer(pack,"bytes")>(512u<<20)||!hash(pack.at("sha256"))||
           overlay.at("pinned_quantizer_revision")!="0a1ef309cdbb9f2024f58a38fb4c42352c5db569")
            throw std::runtime_error("Bounded active shared-Q8 conversion required");
        for(const char*k:{"logical_file_lengths_preserved","tensor_offsets_compacted","unconsumed_parent_tails_retained","original_Expert_payloads_preserved","F32_activation_input_required"})
            if(overlay.at(k)!=true)throw std::runtime_error("Shared Q8 changed an original source boundary");
        std::set<std::string>allowed,seen,files;
        for(unsigned layer=0;layer<48;++layer)for(const char*role:{"gate","up","down"})
            allowed.insert("blk."+std::to_string(layer)+".ffn_"+role+"_shexp.weight");
        Json spans=Json::array();std::uint64_t saved=0;std::vector<std::pair<std::uint64_t,std::uint64_t>>pack_ranges;
        for(const auto&c:changes){const auto name=c.at("name").get<std::string>();
            if(!allowed.count(name)||!seen.insert(name).second||c.at("original_bytes")!=3276800||c.at("bytes")!=1740800||!hash(c.at("payload_sha256")))
                throw std::runtime_error("Shared Q8 projection omitted, duplicated or malformed");
            auto tensor=std::find_if(expected["tensors"].begin(),expected["tensors"].end(),[&](const Json&t){return t.at("name")==name;});
            if(tensor==expected["tensors"].end()||tensor->at("type")!="BF16"||tensor->at("bytes")!=c.at("original_bytes")||
               tensor->at("shape")!=c.at("shape")||tensor->at("file")!=c.at("file")||tensor->at("offset")!=c.at("parent_logical_offset")||
               tensor->at("payload_sha256")!=c.at("parent_payload_sha256"))throw std::runtime_error("Original shared projection provenance differs");
            const auto at=receipt_integer(c,"pack_offset"),bytes=receipt_integer(c,"bytes");
            if(at%16384||at>receipt_integer(pack,"bytes")||bytes>receipt_integer(pack,"bytes")-at)
                throw std::runtime_error("Shared Q8 payload exceeds its owned pack");
            pack_ranges.push_back({at,at+bytes});
            (*tensor)["type"]="Q8_0";(*tensor)["bytes"]=bytes;(*tensor)["payload_sha256"]=c.at("payload_sha256");saved+=3276800-bytes;
            spans.push_back({{"file",c.at("file")},{"logical_offset",c.at("logical_offset")},{"bytes",bytes},{"pack_offset",at},{"kind","Q8_0"},{"tensor",name}});
            files.insert(c.at("file").get<std::string>());
        }
        if(seen!=allowed||saved!=shared_Q8_saved_bytes||spans!=overlay.at("overlays")||overlay.at("headers").size()!=files.size())
            throw std::runtime_error("Every original active shared projection and header must be covered");
        for(const auto&h:overlay.at("headers")){const auto name=h.at("file").get<std::string>();
            const auto f=std::find_if(base.at("files").begin(),base.at("files").end(),[&](const Json&v){return v.at("path")==name;});
            const auto at=receipt_integer(h,"pack_offset"),bytes=receipt_integer(h,"bytes");
            if(!files.erase(name)||f==base.at("files").end()||h.at("logical_offset")!=0||h.at("kind")!="header"||
               f->at("header_bytes")!=bytes||at%16384||at>receipt_integer(pack,"bytes")||bytes>receipt_integer(pack,"bytes")-at||!hash(h.at("sha256")))
                throw std::runtime_error("Bounded unique shared-Q8 header differs");
            pack_ranges.push_back({at,at+bytes});
            std::uint64_t cursor=bytes;
            for(auto&t:expected["tensors"])if(t.at("file")==name){
                t["offset"]=cursor;
                const auto changed=std::find_if(changes.begin(),changes.end(),[&](const Json&c){return c.at("name")==t.at("name");});
                if(changed!=changes.end()&&changed->at("logical_offset")!=cursor)throw std::runtime_error("Shared-Q8 compact offset differs");
                const auto n=receipt_integer(t,"bytes");if(cursor>receipt_integer(*f,"bytes")||n>receipt_integer(*f,"bytes")-cursor)throw std::runtime_error("Compacted tensor exceeds its base file");
                cursor+=n;if(cursor%32)throw std::runtime_error("Compacted GGUF tensor is unaligned");
            }
        }
        std::sort(pack_ranges.begin(),pack_ranges.end());for(std::size_t i=1;i<pack_ranges.size();++i)
            if(pack_ranges[i].first<pack_ranges[i-1].second)throw std::runtime_error("Shared-Q8 physical payloads overlap");
        expected["schema"]="ps5-qwen-output-Q8-with-resident-shared-overlay-v1";
        expected["files_are_immutable_base_descriptors"]=true;expected["candidate_whole_GGUF_hash_claimed"]=false;
        expected["non_Expert_except_output_payload_bytes_preserved"]=false;expected["non_Expert_except_output_and_shared_payload_bytes_preserved"]=true;
        expected["base_output_Q8_receipt_ref"]={{"bytes",raw.size()},{"sha256",shared_Q8_base_SHA256}};
        expected["resident_Q8_overlay"]=overlay;
        if(expected!=r)throw std::runtime_error("Shared Q8 changed a weight or policy outside its explicit overlay");
        return base;
    }
public:
    std::uint64_t mapped_bytes;
    ResidentSharedQ8Receipt(const Json&r,const std::string&base,const std::string&original):parent_(checked_base(r,base),original),changes_(r.at("resident_Q8_overlay").at("tensors")),mapped_bytes(parent_.mapped_bytes){}
    void tensor(const std::string&name,const std::string&type,const std::vector<std::uint64_t>&shape,std::uint64_t bytes)const{
        const auto at=std::find_if(changes_.begin(),changes_.end(),[&](const Json&c){return c.at("name")==name;});
        if(at==changes_.end()){parent_.tensor(name,type,shape,bytes);return;}
        if(type!="Q8_0"||shape!=at->at("shape").get<std::vector<std::uint64_t>>()||bytes!=1740800)
            throw std::runtime_error("Active shared-Q8 tensor escaped its exact shape or type");
    }
    void tensor_ne(const std::string&name,const std::string&type,const std::int64_t*ne,std::uint64_t bytes)const{
        const auto at=std::find_if(changes_.begin(),changes_.end(),[&](const Json&c){return c.at("name")==name;});
        if(at==changes_.end()){parent_.tensor_ne(name,type,ne,bytes);return;}
        if(!ne||ne[2]!=1||ne[3]!=1||ne[0]<=0||ne[1]<=0)throw std::runtime_error("Shared tensor dimensions differ");
        tensor(name,type,{std::uint64_t(ne[0]),std::uint64_t(ne[1])},bytes);
    }
};
inline void validate_resident_shared_Q8_footprint(const ModelFootprint&m,std::uint64_t mapped){
    if(m.trunk_layers!=48||m.tensors!=1256||m.device_weights!=8159137280ull-shared_Q8_saved_bytes||m.mapped_experts!=37748736000ull||
       m.lazy_ple!=102400491520ull||m.mapped_embeddings!=1271398400ull||m.skipped_mtp!=970284032ull||m.largest_device_tensor!=675430400ull||m.mapped_files!=mapped)
        throw std::runtime_error("Resident shared-Q8 footprint differs");
}
}
