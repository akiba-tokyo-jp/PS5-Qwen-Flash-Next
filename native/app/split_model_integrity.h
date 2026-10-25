// SPDX-License-Identifier: MIT
#pragma once
#include "prior_model_integrity.h"
#include <set>
namespace qwen_app {
struct SplitModelIntegrity {
    PriorModelIntegrity prior;
    std::vector<SourceFile> physical;
    std::vector<LogicalSourceFile> logical;
    std::string part_directory;
    SourceIdentity part_directory_identity{};
};
inline std::optional<SplitModelIntegrity> split_model_integrity(const nlohmann::json &gate,
        const nlohmann::json &receipt,std::uint64_t total_bytes) {
    if(!gate.contains("split_native_integrity"))return{};
    const auto require=[](bool value){if(!value)throw std::runtime_error("Complete sealed 512 MiB source integrity is not admitted");};
    require(!gate.contains("prior_native_integrity"));
    const auto &proof=gate.at("split_native_integrity");
    require(proof.at("schema")=="ps5-qwen-split512-native-integrity-policy-v1"&&
        proof.at("same_boot_bound_by_launcher")==true&&proof.at("host_originals_retained_and_verified")==true);
    const auto raw=proof.at("raw").get<std::string>();
    require(!raw.empty()&&raw.size()<=(2u<<20)&&sha256_metadata_bytes(raw)==proof.at("sha256"));
    const auto report=nlohmann::json::parse(raw);
    require(report.at("schema")=="ps5-qwen-split512-native-integrity-v1"&&
        report.at("original_receipt_sha256")==gate.at("model_receipt_sha256")&&
        report.at("part_bytes")==model_source_part_bytes&&report.at("logical_bytes")==total_bytes&&
        report.at("all_original_logical_SHA256_matched")==true&&report.at("all_physical_part_SHA256_matched")==true&&
        report.at("all_copy_publish_truncate_operations_completed")==true&&report.at("pending_operations")==0&&
        report.at("model_loaded")==false&&report.at("Vulkan_initialized")==false&&report.at("GPU_calls")==0&&
        report.at("maximum_source_window_bytes")==model_read_window&&report.at("automatic_retries")==0);
    const auto identity=[&](const nlohmann::json &value,bool directory) {
        require(value.is_array()&&value.size()==10);SourceIdentity key{};
        for(unsigned i=0;i<10;++i){require(value[i].is_number_integer()&&value[i]>=0);key[i]=value[i].get<std::uint64_t>();}
        require(key[0]&&key[1]&&key[5]&&key[3]==0&&key[4]==0&&
            (key[2]&0177777)==(directory?0040755:0100644)&&key[6]<=4102444800ull&&
            key[8]<=4102444800ull&&key[7]<1000000000&&key[9]<1000000000);
        return key;
    };
    const auto digest=[&](const nlohmann::json &value){
        require(value.is_string());const auto text=value.get<std::string>();
        require(text.size()==64&&text.find_first_not_of("0123456789abcdef")==std::string::npos);return text;
    };
    SplitModelIntegrity result;
    result.prior.directory=identity(report.at("directory_identity"),true);
    result.prior.receipt=identity(report.at("receipt_identity"),false);
    require(result.prior.receipt[5]==gate.at("model_receipt_bytes")&&
        result.prior.directory[0]==result.prior.receipt[0]);
    result.part_directory=report.at("part_directory").get<std::string>();
    require(result.part_directory.empty()||(result.part_directory.size()==41&&result.part_directory.substr(0,9)=="split512-"&&
        result.part_directory.substr(9).find_first_not_of("0123456789abcdef")==std::string::npos));
    result.part_directory_identity=identity(report.at("part_directory_identity"),true);
    require(result.part_directory_identity[0]==result.prior.directory[0]);
    if(result.part_directory.empty())require(result.part_directory_identity==result.prior.directory);
    const auto &files=report.at("logical_files");
    require(files.is_array()&&files.size()==receipt.at("files").size()&&!files.empty()&&files.size()<=256);
    std::set<std::string>paths;std::set<std::pair<std::uint64_t,std::uint64_t>>inodes;
    std::uint64_t total=0;
    for(std::size_t i=0;i<files.size();++i){
        const auto &file=files[i],&original=receipt.at("files")[i];
        const auto name=original.at("path").get<std::string>();const auto bytes=original.at("bytes").get<std::uint64_t>();
        require(name.size()>5&&name.size()<=240&&name.substr(name.size()-5)==".gguf"&&
            name.find_first_not_of("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._-")==std::string::npos&&
            bytes&&bytes<=(512ull<<30)&&total<=(512ull<<30)-bytes);
        require(file.at("path")==name&&file.at("bytes")==bytes&&digest(file.at("sha256"))==original.at("sha256"));
        const auto &parts=file.at("parts");
        require(parts.is_array()&&parts.size()==(bytes+model_source_part_bytes-1)/model_source_part_bytes);
        LogicalSourceFile logical{name,bytes,{}};std::uint64_t covered=0;
        for(std::size_t j=0;j<parts.size();++j){
            const auto &part=parts[j];const auto key=identity(part.at("identity"),false);
            const auto path=part.at("path").get<std::string>();
            const auto suffix=std::to_string(j);
            const auto expected=j?(result.part_directory.empty()?std::string{}:result.part_directory+"/")+name+".part-"+suffix:name;
            const auto count=std::min<std::uint64_t>(model_source_part_bytes,bytes-covered);
            require(path==expected&&paths.insert(path).second&&part.at("offset")==covered&&part.at("bytes")==count&&
                key[5]==count&&key[0]==result.prior.directory[0]&&inodes.emplace(key[0],key[1]).second);
            (void)digest(part.at("sha256"));
            require(result.physical.size()<1024);
            logical.parts.push_back(result.physical.size());result.physical.push_back({path,count,key});covered+=count;
        }
        require(covered==bytes);total+=covered;result.prior.files.push_back(result.physical[logical.parts.front()].identity);
        result.logical.push_back(std::move(logical));
    }
    require(total==total_bytes&&report.at("physical_files")==result.physical.size());
    result.prior.report_sha256=digest(proof.at("sha256"));result.prior.snapshot_sha256=result.prior.report_sha256;
    result.prior.original_elapsed_ms=report.at("verification_elapsed_ms").get<std::uint64_t>();
    require(result.prior.original_elapsed_ms&&result.prior.original_elapsed_ms<=7200000);
    return result;
}
}
