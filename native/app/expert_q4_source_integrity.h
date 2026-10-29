// SPDX-License-Identifier: MIT
#pragma once
#include "expert_q4_receipt.h"
#include <split_model_integrity.h>
#include <set>

namespace qwen_app {
inline constexpr const char*original_model_source_root=
    "/app0/qwen-runtime/model";
inline bool expert_q4_source_root(const std::string&root) {
    const std::string prefix="/app0/expert-q4-";
    return root.size()==prefix.size()+32&&root.compare(0,prefix.size(),prefix)==0&&
        root.substr(prefix.size()).find_first_not_of("0123456789abcdef")==std::string::npos;
}
inline std::string expert_q4_logical_path(const nlohmann::json&receipt,const std::string&root,const std::string&name) {
    if(!expert_q4_source_root(root))throw std::runtime_error("Exact isolated Expert Q4 source root required");
    for(const auto&file:receipt.at("files"))if(file.at("path")==name)
        return std::string(file.at("reused_original")==true?original_model_source_root:root)+"/"+name;
    throw std::runtime_error("Expert Q4 logical path is absent from the complete receipt");
}

// Reuse two unchanged original files by exact native identities and earlier
// complete logical hashes. Newly encoded parts require their own complete
// Direct readback and a post-publication identity seal. No hard links, source
// truncation, parent ownership changes or payload rereads are needed at startup.
inline SplitModelIntegrity expert_q4_source_integrity(const nlohmann::json&gate,
        const nlohmann::json&receipt,const std::string&root,std::uint64_t total_bytes) {
    const auto require=[](bool ok){if(!ok)throw std::runtime_error("Complete sealed Expert Q4 source integrity is not admitted");};
    require(expert_q4_source_root(root));
    const auto&proof=gate.at("Expert_Q4_source_integrity");
    require(proof.at("schema")=="ps5-qwen-expert-q4-source-policy-v1");
    const auto raw=proof.at("raw").get<std::string>();
    require(!raw.empty()&&raw.size()<=(2u<<20)&&sha256_metadata_bytes(raw)==proof.at("sha256"));
    const auto sealed=nlohmann::json::parse(raw);
    require(sealed.at("schema")=="ps5-qwen-expert-q4-native-source-integrity-v1"&&
        sealed.at("model_receipt_sha256")==gate.at("model_receipt_sha256")&&sealed.at("source_directory")==root&&
        sealed.at("canonical_source_directory")==std::string("/data/ai/native-moss-image-sft/PPSA99190")+root.substr(5)&&
        sealed.at("same_existing_title_nullfs_namespace")==true&&sealed.at("original_BF16_directories_and_parts_unchanged")==true&&
        sealed.at("permission_changes")==0&&sealed.at("mount_changes")==0&&
        sealed.at("all_new_parts_complete_Direct_SHA256_readback")==true&&
        sealed.at("all_parts_unchanged_since_readback")==true&&sealed.at("CPU_owners_positively_closed")==true&&
        sealed.at("source_writes")==0&&sealed.at("GPU_calls")==0&&sealed.at("model_loaded")==false&&
        sealed.at("automatic_retries")==0&&sealed.at("part_bytes")==model_source_part_bytes&&
        sealed.at("logical_bytes")==total_bytes);
    const auto identity=[&](const nlohmann::json&row,bool directory){
        require(row.is_array()&&row.size()==10);SourceIdentity key{};
        for(unsigned i=0;i<10;++i){require(row[i].is_number_integer()&&row[i]>=0);key[i]=row[i].get<std::uint64_t>();}
        require(key[0]&&key[1]&&key[5]&&!key[3]&&!key[4]&&
            (key[2]&0177777)==(directory?0040755:0100644)&&key[6]<=4102444800ull&&key[8]<=4102444800ull&&
            key[7]<1000000000&&key[9]<1000000000);return key;
    };
    const auto digest=[&](const nlohmann::json&row){
        require(row.is_string());const auto s=row.get<std::string>();
        require(s.size()==64&&s.find_first_not_of("0123456789abcdef")==std::string::npos);return s;
    };
    const auto&original=receipt.at("original_BF16_receipt");
    nlohmann::json original_gate={{"model_receipt_sha256",original_receipt_sha256},{"model_receipt_bytes",95068},
        {"split_native_integrity",sealed.at("original_split_integrity")}};
    const auto old=split_model_integrity(original_gate,original,validate_model_receipt(original));
    require(bool(old));
    SplitModelIntegrity result;result.prior.directory=identity(sealed.at("directory_identity"),true);
    result.prior.receipt=identity(sealed.at("receipt_identity"),false);
    require(result.prior.receipt[5]==gate.at("model_receipt_bytes")&&result.prior.receipt[0]==result.prior.directory[0]);
    result.part_directory="";result.part_directory_identity=result.prior.directory;
    const auto&files=sealed.at("logical_files");require(files.is_array()&&files.size()==76&&files.size()==receipt.at("files").size());
    std::set<std::string>paths;std::set<std::pair<std::uint64_t,std::uint64_t>>inodes;
    std::uint64_t total=0;unsigned reused=0,new_files=0;
    for(unsigned i=0;i<files.size();++i){
        const auto&file=files[i],&expected=receipt.at("files")[i];
        const auto name=expected.at("path").get<std::string>();const auto bytes=receipt_integer(expected,"bytes");
        require(file.at("path")==name&&file.at("bytes")==bytes&&digest(file.at("sha256"))==expected.at("sha256"));
        const bool reuse=expected.at("reused_original")==true;
        const auto logical_path=expert_q4_logical_path(receipt,root,name);
        LogicalSourceFile logical{logical_path,bytes,{}};
        const auto&parts=file.at("parts");require(parts.is_array()&&parts.size()==(bytes+model_source_part_bytes-1)/model_source_part_bytes);
        if(reuse)++reused;else ++new_files;
        std::uint64_t covered=0;
        for(unsigned j=0;j<parts.size();++j){
            const auto&part=parts[j];const auto key=identity(part.at("identity"),false);
            const auto count=std::min<std::uint64_t>(model_source_part_bytes,bytes-covered);
            std::string physical_path;
            if(reuse){
                require(j<old->logical.at(i).parts.size());const auto&old_part=old->physical.at(old->logical.at(i).parts[j]);
                require(key==old_part.identity&&count==old_part.bytes);physical_path=std::string(original_model_source_root)+"/"+old_part.path;
            }else physical_path=root+"/"+name+(j?".part-"+std::to_string(j):"");
            require(part.at("path")==physical_path&&part.at("offset")==covered&&part.at("bytes")==count&&key[5]==count&&
                key[0]==result.prior.directory[0]&&paths.insert(physical_path).second&&inodes.emplace(key[0],key[1]).second);
            (void)digest(part.at("sha256"));require(result.physical.size()<1024);
            logical.parts.push_back(result.physical.size());result.physical.push_back({physical_path,count,key});covered+=count;
        }
        require(covered==bytes&&result.physical.at(logical.parts.front()).path==logical.path);
        result.prior.files.push_back(result.physical.at(logical.parts.front()).identity);result.logical.push_back(std::move(logical));total+=bytes;
    }
    require(total==total_bytes&&reused==2&&new_files==74&&sealed.at("physical_files")==result.physical.size());
    result.prior.report_sha256=digest(proof.at("sha256"));result.prior.snapshot_sha256=result.prior.report_sha256;
    result.prior.original_elapsed_ms=receipt_integer(sealed,"verification_elapsed_ms");
    require(result.prior.original_elapsed_ms&&result.prior.original_elapsed_ms<=7200000);return result;
}
}
