// SPDX-License-Identifier: MIT
#pragma once
#include <model_receipt.h>
#include "expert_q4_geometry.h"
#include <array>
#include <unordered_map>

namespace qwen_app {
inline constexpr std::uint64_t expert_q4_tensor_bytes=181974149632ull;
inline constexpr std::uint64_t expert_q4_payload_bytes=69363302400ull;
inline constexpr const char * original_receipt_sha256=
    "d2a0705e0e8d8d5999cf2e6bd9519ccb0654837abcf1ab47d0295030a8bb5495";

// An explicit separate receipt admits the owner's lossy Expert-only candidate.
// The original BF16 admission function is deliberately unchanged.
class ExpertQ4Receipt {
    struct Tensor {
        std::string type;
        std::vector<std::uint64_t> shape;
        std::uint64_t bytes;
    };
    std::unordered_map<std::string,Tensor> tensors_;
public:
    std::uint64_t mapped_bytes=0;
    explicit ExpertQ4Receipt(const nlohmann::json &receipt) {
        receipt_text(receipt,"schema","ps5-qwen-expert-q4-model-v1");
        receipt_text(receipt,"original_revision",original_model_revision);
        receipt_text(receipt,"upstream_revision",original_converter_revision);
        receipt_text(receipt,"Expert_format","Q4_0");
        receipt_text(receipt,"original_receipt_sha256",original_receipt_sha256);
        for(const char *field:{"completed","all_Experts_retained","non_Expert_payload_bytes_preserved"})
            receipt_flag(receipt,field,true);
        for(const char *field:{"activation_quantization","KV_quantization","host_model_inference"})
            receipt_flag(receipt,field,false);
        const auto &original=receipt.at("original_BF16_receipt");
        (void)validate_model_receipt(original);
        const auto &files=receipt.at("files"),&old=original.at("files");
        if(files.size()!=76 || files.size()!=old.size())throw std::runtime_error("All original logical splits required for Expert Q4");
        unsigned replacements=0;
        for(unsigned i=0;i<files.size();++i) {
            const auto &row=files[i];
            if(row.at("path")!=old[i].at("path") || row.at("original_sha256")!=old[i].at("sha256"))
                throw std::runtime_error("Expert Q4 source split provenance differs");
            const auto bytes=receipt_integer(row,"bytes");
            const auto digest=row.at("sha256").get<std::string>();
            if(!bytes || bytes>receipt_integer(old[i],"bytes") || digest.size()!=64 ||
               digest.find_first_not_of("0123456789abcdef")!=std::string::npos)
                throw std::runtime_error("Bounded complete Expert Q4 split required");
            if(row.at("reused_original")==true) {
                if(bytes!=receipt_integer(old[i],"bytes") || digest!=old[i].at("sha256"))
                    throw std::runtime_error("Reused non-Expert split differs from original");
            } else ++replacements;
            mapped_bytes=checked_memory_sum(mapped_bytes,bytes);
        }
        if(replacements!=74)throw std::runtime_error("Exactly 74 Expert-containing replacements required");
        receipt_number(receipt,"mapped_file_bytes",mapped_bytes);
        const auto &manifest=receipt.at("tensors");
        if(!manifest.is_array() || manifest.size()!=1256)throw std::runtime_error("Complete Expert Q4 tensor manifest required");
        std::array<std::array<bool,3>,49> projections{};
        unsigned experts=0;std::uint64_t total=0,quantized=0;
        for(const auto &row:manifest) {
            const auto name=row.at("name").get<std::string>();
            Tensor t{row.at("type").get<std::string>(),row.at("shape").get<std::vector<std::uint64_t>>(),receipt_integer(row,"bytes")};
            if(name.empty() || t.shape.empty() || t.shape.size()>4 || !t.bytes || !tensors_.emplace(name,t).second)
                throw std::runtime_error("Unique complete Expert Q4 tensor geometry required");
            std::uint64_t values=1;
            for(auto dimension:t.shape) {
                if(!dimension || dimension>(UINT64_MAX/values))throw std::runtime_error("Expert Q4 shape overflow");
                values*=dimension;
            }
            const auto marker=name.find(".ffn_");
            const bool expert=marker!=std::string::npos && name.size()>12 && name.substr(name.size()-12)=="_exps.weight";
            if(expert) {
                if(name.rfind("blk.",0)!=0 || marker<=4 || t.type!="Q4_0" || t.shape.size()!=3 || t.shape[2]!=512)
                    throw std::runtime_error("Only complete original Experts may be Q4_0");
                const auto layer_text=name.substr(4,marker-4);
                if(layer_text.find_first_not_of("0123456789")!=std::string::npos)throw std::runtime_error("Expert layer differs");
                const auto layer=std::stoul(layer_text);
                const auto role=name.substr(marker+5);
                const unsigned projection=role=="gate_exps.weight"?0:role=="up_exps.weight"?1:role=="down_exps.weight"?2:3;
                if(layer>=49 || projection>=3 || projections[layer][projection] ||
                   t.shape[0]!=(projection==2?640u:2560u) || t.shape[1]!=(projection==2?2560u:640u) ||
                   t.bytes!=values/32*18)
                    throw std::runtime_error("Original 49-layer Expert projection set differs");
                projections[layer][projection]=true;++experts;quantized+=t.bytes;
            } else if((t.type!="BF16" && t.type!="F32") || t.bytes!=values*(t.type=="BF16"?2:4))
                throw std::runtime_error("Non-Expert precision or geometry changed");
            total=checked_memory_sum(total,t.bytes);
        }
        if(experts!=147 || quantized!=expert_q4_payload_bytes || total!=expert_q4_tensor_bytes || mapped_bytes<total)
            throw std::runtime_error("Expert Q4 complete model byte accounting differs");
    }
    void tensor(const std::string &name,const std::string &type,
                const std::vector<std::uint64_t>&shape,std::uint64_t bytes) const {
        const auto found=tensors_.find(name);
        if(found==tensors_.end() || found->second.type!=type || found->second.shape!=shape || found->second.bytes!=bytes)
            throw std::runtime_error("GGUF tensor differs from the sealed Expert Q4 manifest");
    }
    void tensor_ne(const std::string&name,const std::string&type,const std::int64_t*ne,std::uint64_t bytes) const {
        const auto found=tensors_.find(name);
        if(found==tensors_.end()||!ne||found->second.type!=type||found->second.bytes!=bytes)
            throw std::runtime_error("GGUF type/span differs from the sealed Expert Q4 manifest");
        for(unsigned i=0;i<4;++i){const auto expected=i<found->second.shape.size()?found->second.shape[i]:1;
            if(ne[i]<=0||std::uint64_t(ne[i])!=expected)throw std::runtime_error("GGUF dimensions differ from the complete Expert Q4 manifest");}
    }
};
inline void validate_expert_q4_footprint(const ModelFootprint &model,std::uint64_t mapped_files) {
    if(model.trunk_layers!=48 || model.tensors!=1256 || model.device_weights!=8755105280ull ||
       model.mapped_experts!=67947724800ull || model.lazy_ple!=102400491520ull ||
       model.mapped_embeddings!=1271398400ull || model.skipped_mtp!=1599429632ull ||
       model.largest_device_tensor!=1271398400ull || model.mapped_files!=mapped_files)
        throw std::runtime_error("Expert Q4 footprint differs from the complete mixed-precision model");
}
}
