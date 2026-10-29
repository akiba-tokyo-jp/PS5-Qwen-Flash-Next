// SPDX-License-Identifier: MIT
#pragma once
#include "expert_all_q2_receipt.h"
#include "model_integrity.h"
namespace qwen_app {
inline constexpr const char*resident_output_Q8_parent_SHA256="efd101c3661e6eb81f17306c43fc41b361f94aa58495f2025401659228163191";
inline constexpr std::uint64_t resident_output_Q8_saved_bytes=595968000;
// Validate the byte-exact parent separately from this explicit output-only
// exception. No parent precision flag describes the candidate's output head.
class ResidentOutputQ8Receipt {
    using Json=nlohmann::json;
    ExpertAllQ2Receipt parent_;
    static Json checked_parent(const Json&r,const std::string&raw){
        receipt_text(r,"schema","ps5-qwen-expert-all-q2-output-Q8-model-v1");
        if(raw.empty()||raw.size()>(1u<<20)||sha256_metadata_bytes(raw)!=resident_output_Q8_parent_SHA256)
            throw std::runtime_error("Exact original all-Q2 parent receipt required");
        const auto old=Json::parse(raw);Json expected=old;
        const auto&details=r.at("resident_output_Q8");const auto&file=details.at("converted");
        if(file.at("bytes")!=675430560ull||details.at("original_BF16_payload_bytes")!=1271398400ull||
           details.at("Q8_payload_bytes")!=675430400ull||details.at("saved_payload_bytes")!=resident_output_Q8_saved_bytes||
           details.at("pinned_reference")!="quantize_row_q8_0_ref"||details.at("F32_activation_input_required")!=true||
           details.at("parts").size()!=2||details.at("parts")[0].at("offset")!=0||details.at("parts")[0].at("bytes")!=(512u<<20)||
           details.at("parts")[1].at("offset")!=(512u<<20)||details.at("parts")[1].at("bytes")!=138559648ull)
            throw std::runtime_error("Bounded original-BF16 output Q8 conversion differs");
        const auto valid_hash=[](const Json&j){const auto s=j.get<std::string>();return s.size()==64&&s.find_first_not_of("0123456789abcdef")==std::string::npos;};
        if(!valid_hash(file.at("sha256"))||!valid_hash(details.at("payload_sha256"))||
           details.at("original").at("sha256")!=old.at("original_BF16_receipt").at("files").back().at("sha256"))
            throw std::runtime_error("Original output provenance or complete Q8 hashes differ");
        expected["schema"]="ps5-qwen-expert-all-q2-output-Q8-model-v1";
        expected["non_Expert_payload_bytes_preserved"]=false;
        expected["non_Expert_except_output_payload_bytes_preserved"]=true;
        expected["mapped_file_bytes"]=receipt_integer(old,"mapped_file_bytes")-resident_output_Q8_saved_bytes;
        expected["files"].back()["bytes"]=675430560ull;expected["files"].back()["sha256"]=file.at("sha256");expected["files"].back()["reused_original"]=false;
        unsigned changed=0;
        for(auto&t:expected["tensors"])if(t.at("name")=="output.weight"){
            if(t.at("type")!="BF16"||t.at("bytes")!=1271398400ull||t.at("offset")!=160)
                throw std::runtime_error("Original output tensor geometry differs");
            t["type"]="Q8_0";t["bytes"]=675430400ull;t["payload_sha256"]=details.at("payload_sha256");++changed;
        }
        expected["resident_output_Q8"]=details;
        expected["parent_all_Q2_receipt_ref"]={{"bytes",raw.size()},{"sha256",resident_output_Q8_parent_SHA256}};
        if(changed!=1||expected!=r)throw std::runtime_error("The Q8 exception changed a tensor, route or source outside the resident output");
        return old;
    }
public:
    std::uint64_t mapped_bytes;
    ResidentOutputQ8Receipt(const Json&r,const std::string&parent_raw):parent_(checked_parent(r,parent_raw)),mapped_bytes(parent_.mapped_bytes-resident_output_Q8_saved_bytes){}
    void tensor(const std::string&name,const std::string&type,const std::vector<std::uint64_t>&shape,std::uint64_t bytes)const{
        if(name!="output.weight"){parent_.tensor(name,type,shape,bytes);return;}
        if(type!="Q8_0"||shape!=std::vector<std::uint64_t>({2560,248320})||bytes!=675430400ull)
            throw std::runtime_error("Resident output Q8 tensor escaped its exact shape or type");
    }
    void tensor_ne(const std::string&name,const std::string&type,const std::int64_t*ne,std::uint64_t bytes)const{
        if(name!="output.weight"){parent_.tensor_ne(name,type,ne,bytes);return;}
        if(!ne||ne[0]!=2560||ne[1]!=248320||ne[2]!=1||ne[3]!=1)
            throw std::runtime_error("Resident output Q8 dimensions differ");
        tensor(name,type,{2560,248320},bytes);
    }
};
inline void validate_resident_output_Q8_footprint(const ModelFootprint&m,std::uint64_t mapped){
    if(m.trunk_layers!=48||m.tensors!=1256||m.device_weights!=8159137280ull||m.mapped_experts!=37748736000ull||
       m.lazy_ple!=102400491520ull||m.mapped_embeddings!=1271398400ull||m.skipped_mtp!=970284032ull||
       m.largest_device_tensor!=675430400ull||m.mapped_files!=mapped)
        throw std::runtime_error("Resident output Q8 full-model footprint differs");
}
}
