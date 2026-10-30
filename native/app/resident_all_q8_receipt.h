// SPDX-License-Identifier: MIT
#pragma once
#include "resident_shared_q8_receipt.h"
namespace qwen_app {
inline constexpr const char*all_Q8_parent_SHA256="7ba7bbf919eba43a365f570930558b9405b60ad66f9e3cdeea104ce5557377fb";
inline constexpr std::uint64_t all_Q8_saved_bytes=3163852800ull;
inline bool resident_all_Q8_name(const std::string&name){
    ModelFootprint f;f.trunk_layers=48;f.tensor(name,1);return f.device_weights==1;
}
inline bool resident_all_Q8_file(const nlohmann::json&r,const std::string&name){
    for(const auto&h:r.at("resident_all_Q8_overlay").at("headers"))if(h.at("file")==name)return true;return false;
}
class ResidentAllQ8Receipt {
    using Json=nlohmann::json;
    ResidentSharedQ8Receipt parent_;
    Json changes_,tensors_;
    static Json checked_parent(const Json&r,const std::string&raw){
        const auto need=[](bool b){if(!b)throw std::runtime_error("Complete resident-Q8 precision proof required");};
        need(!raw.empty()&&raw.size()<=(1u<<20)&&sha256_metadata_bytes(raw)==all_Q8_parent_SHA256);
        Json parent=Json::parse(raw),expected=parent;
        const auto&o=r.at("resident_all_Q8_overlay");const auto&parts=o.at("parts");const auto&changes=o.at("tensors");
        need(o.at("schema")=="ps5-qwen-all-resident-Q8-overlay-v1"&&changes.size()==544&&parts.is_array()&&parts.size()>0&&parts.size()<=16);
        need(o.at("parent")==Json({{"bytes",raw.size()},{"sha256",all_Q8_parent_SHA256}})&&o.at("saved_resident_payload_bytes")==all_Q8_saved_bytes);
        need(o.at("pinned_quantizer_revision")=="0a1ef309cdbb9f2024f58a38fb4c42352c5db569");
        for(const char*k:{"original_Expert_payloads_preserved","F32_activation_input_required","KV_precision_preserved","logical_file_lengths_preserved","tensor_offsets_compacted","narrow_convolution_BF16_preserved"})need(o.at(k)==true);
        const auto hash=[&](const Json&v){const auto s=v.get<std::string>();need(s.size()==64&&s.find_first_not_of("0123456789abcdef")==std::string::npos);};
        std::vector<std::vector<std::pair<std::uint64_t,std::uint64_t>>>ranges(parts.size());
        for(const auto&p:parts){need(receipt_integer(p,"bytes")>0&&receipt_integer(p,"bytes")<=512ull<<20);hash(p.at("sha256"));}
        auto span=[&](const Json&c){const auto part=receipt_integer(c,"part"),at=receipt_integer(c,"pack_offset"),bytes=receipt_integer(c,"bytes");
            need(part<parts.size()&&at%16384==0&&bytes>0&&at<=receipt_integer(parts[part],"bytes")&&bytes<=receipt_integer(parts[part],"bytes")-at);ranges[part].push_back({at,at+bytes});};
        std::set<std::string>allowed,seen,files;
        for(const auto&t:parent.at("tensors"))if(t.at("type")=="BF16"&&t.at("name")!="blk.1.ple_conv1d.weight"&&resident_all_Q8_name(t.at("name")))allowed.insert(t.at("name").get<std::string>());
        need(allowed.size()==544);std::uint64_t saved=0;
        for(const auto&c:changes){const auto name=c.at("name").get<std::string>();need(allowed.count(name)&&seen.insert(name).second);
            auto t=std::find_if(expected["tensors"].begin(),expected["tensors"].end(),[&](const Json&v){return v.at("name")==name;});need(t!=expected["tensors"].end());
            const auto old=receipt_integer(*t,"bytes"),bytes=receipt_integer(c,"bytes");
            need(old==c.at("original_bytes")&&old%64==0&&bytes==old/64*34&&t->at("payload_sha256")==c.at("parent_payload_sha256"));hash(c.at("payload_sha256"));span(c);saved+=old-bytes;
            const auto shape=t->at("shape").get<std::vector<std::uint64_t>>();need(shape.size()==2);
            need(shape[0]%32==0);
            (*t)["type"]="Q8_0";(*t)["bytes"]=bytes;(*t)["payload_sha256"]=c.at("payload_sha256");files.insert(t->at("file").get<std::string>());
        }
        need(seen==allowed&&saved==all_Q8_saved_bytes&&o.at("headers").size()==files.size());
        for(const auto&h:o.at("headers")){const auto name=h.at("file").get<std::string>();need(files.erase(name)==1);span(h);hash(h.at("sha256"));
            const auto f=std::find_if(parent.at("files").begin(),parent.at("files").end(),[&](const Json&v){return v.at("path")==name;});need(f!=parent.at("files").end()&&f->at("header_bytes")==h.at("bytes"));
            auto cursor=receipt_integer(h,"bytes");for(auto&t:expected["tensors"])if(t.at("file")==name){t["offset"]=cursor;const auto n=receipt_integer(t,"bytes");need(cursor<=receipt_integer(*f,"bytes")&&n<=receipt_integer(*f,"bytes")-cursor);cursor+=n;need(cursor%32==0);}
        }
        for(auto&part:ranges){need(!part.empty());std::sort(part.begin(),part.end());for(std::size_t i=1;i<part.size();++i)need(part[i-1].second<=part[i].first);}
        expected.erase("original_BF16_receipt");expected.erase("resident_Q8_overlay");expected["schema"]="ps5-qwen-all-resident-Q8-overlay-v1";
        expected["non_Expert_except_output_and_shared_payload_bytes_preserved"]=false;expected["resident_all_Q8_overlay"]=o;
        need(expected==r);return parent;
    }
public:
    std::uint64_t mapped_bytes;
    ResidentAllQ8Receipt(const Json&r,const std::string&parent,const std::string&base,const std::string&original):
        parent_(checked_parent(r,parent),base,original),changes_(r.at("resident_all_Q8_overlay").at("tensors")),tensors_(r.at("tensors")),mapped_bytes(parent_.mapped_bytes){}
    void tensor(const std::string&name,const std::string&type,const std::vector<std::uint64_t>&shape,std::uint64_t bytes)const{
        const auto c=std::find_if(changes_.begin(),changes_.end(),[&](const Json&v){return v.at("name")==name;});
        if(c==changes_.end()){parent_.tensor(name,type,shape,bytes);return;}
        const auto t=std::find_if(tensors_.begin(),tensors_.end(),[&](const Json&v){return v.at("name")==name;});
        if(t==tensors_.end()||type!="Q8_0"||bytes!=c->at("bytes")||shape!=t->at("shape").get<std::vector<std::uint64_t>>())throw std::runtime_error("Resident Q8 tensor geometry differs");
    }
    void tensor_ne(const std::string&name,const std::string&type,const std::int64_t*ne,std::uint64_t bytes)const{
        const auto c=std::find_if(changes_.begin(),changes_.end(),[&](const Json&v){return v.at("name")==name;});
        if(c==changes_.end()){parent_.tensor_ne(name,type,ne,bytes);return;}
        if(!ne||ne[0]<=0||ne[1]<=0||ne[2]!=1||ne[3]!=1)throw std::runtime_error("Resident Q8 rank differs");
        tensor(name,type,{std::uint64_t(ne[0]),std::uint64_t(ne[1])},bytes);
    }
};
inline void validate_resident_all_Q8_footprint(const ModelFootprint&m,std::uint64_t mapped){
    if(m.trunk_layers!=48||m.tensors!=1256||m.device_weights!=4774100480ull||m.mapped_experts!=37748736000ull||
       m.lazy_ple!=102400491520ull||m.mapped_embeddings!=1271398400ull||m.skipped_mtp!=970284032ull||m.largest_device_tensor!=675430400ull||m.mapped_files!=mapped)
        throw std::runtime_error("All-resident Q8 footprint differs");
}
}
