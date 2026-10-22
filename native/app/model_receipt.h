// SPDX-License-Identifier: MIT
#pragma once
#include "memory_admission.h"
#include "nlohmann/json.hpp"
#include <fstream>
#include <unordered_set>

namespace qwen_app {
inline constexpr const char * original_model_revision = "de4b8e4d43b917e7706784d8bb445c9af86a3540";
inline constexpr const char * original_converter_revision = "0a1ef309cdbb9f2024f58a38fb4c42352c5db569";
inline constexpr const char * original_tensor_layout = "8f558e3ad4114c6b733d2a871394187557c24d430f4b38352146c1082bddd260";
inline constexpr std::uint64_t original_converted_tensor_bytes = 359235922432ull;

inline std::uint64_t receipt_integer(const nlohmann::json & object,const char * name) {
    const auto & value=object.at(name);
    if(!value.is_number_unsigned() && (!value.is_number_integer() || value.get<std::int64_t>()<0))
        throw std::runtime_error(std::string("Receipt requires a nonnegative integer: ")+name);
    return value.get<std::uint64_t>();
}
inline void receipt_number(const nlohmann::json & object,const char * name,std::uint64_t expected) {
    if(receipt_integer(object,name)!=expected) throw std::runtime_error(std::string("Original receipt count differs: ")+name);
}
inline void receipt_flag(const nlohmann::json & object,const char * name,bool expected) {
    const auto & value=object.at(name);
    if(!value.is_boolean() || value.get<bool>()!=expected) throw std::runtime_error(std::string("Original receipt flag differs: ")+name);
}
inline void receipt_text(const nlohmann::json & object,const char * name,const char * expected) {
    const auto & value=object.at(name);
    if(!value.is_string() || value.get<std::string>()!=expected) throw std::runtime_error(std::string("Original receipt identity differs: ")+name);
}
inline void validate_converter_sources(const nlohmann::json & source) {
    receipt_number(source,"python_files",237);
    receipt_text(source,"python_tree_sha256","7d14bdf4f3a7422efb04945f9bc56c6b324b1ef15b6762fb11606fe493bff94c");
    receipt_text(source,"source_archive_sha256","1e8acbe578c49f32d9b039d938ca7efd291ed3e0d0efa597efb0074463249437");
}
inline std::uint64_t validate_model_receipt(const nlohmann::json & receipt) {
    if(receipt.contains("test_fixture_only")) throw std::runtime_error("A metadata test fixture is not a model receipt");
    receipt_text(receipt,"schema","ps5-qwen-bf16-conversion-v2");
    receipt_text(receipt,"original_revision",original_model_revision);
    receipt_text(receipt,"upstream_revision",original_converter_revision);
    receipt_text(receipt,"outtype","bf16");
    receipt_flag(receipt,"original_shards_verified",true);
    receipt_flag(receipt,"console_access",false);
    receipt_flag(receipt,"learned_inference_performed",false);
    validate_converter_sources(receipt.at("converter_sources"));
    const auto & audit=receipt.at("conversion_audit");
    receipt_text(audit,"schema","ps5-qwen-conversion-audit-v2");
    receipt_text(audit,"original_revision",original_model_revision);
    receipt_text(audit,"tensor_layout_sha256",original_tensor_layout);
    validate_converter_sources(audit.at("converter_sources"));
    for(const auto * field:{"complete_tensor_set","exact_shapes_and_precision","exact_PLE_integer_constants",
                            "complete_converted_tensor_payload_verified","original_shards_verified"}) receipt_flag(audit,field,true);
    for(const auto * field:{"physical_memory_admitted","console_access","learned_inference_performed"}) receipt_flag(audit,field,false);
    receipt_number(audit,"tensor_count",1256);
    receipt_number(audit,"trunk_layers",48);receipt_number(audit,"mtp_layers",1);
    receipt_number(audit,"PLE_parts_verified",128);
    receipt_number(audit,"PLE_payload_bytes_verified",102400491520ull);
    receipt_number(audit,"expert_projection_tensors_verified",147);
    receipt_number(audit,"expert_payload_bytes_verified",246625075200ull);
    receipt_number(audit,"embedding_payload_bytes_verified",2542796800ull);
    receipt_number(audit,"dense_tensors_replayed",1106);
    receipt_number(audit,"dense_payload_bytes_replayed",7667558912ull);
    const auto & files=receipt.at("files");
    if(!files.is_array() || files.empty() || files.size()>256) throw std::runtime_error("Bounded original model splits are required");
    std::unordered_set<std::string> names;std::uint64_t total=0;
    for(const auto & file:files) {
        const auto name=file.at("path").get<std::string>();
        if(name.size()<=5 || name.size()>240 || name.substr(name.size()-5)!=".gguf" ||
           name.find_first_not_of("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._-")!=std::string::npos ||
           !names.insert(name).second) throw std::runtime_error("Unique relative GGUF basenames are required");
        const auto digest=file.at("sha256").get<std::string>();
        if(digest.size()!=64 || digest.find_first_not_of("0123456789abcdef")!=std::string::npos)
            throw std::runtime_error("Original model split SHA256 is required");
        const auto bytes=receipt_integer(file,"bytes");
        if(!bytes || bytes>(512ull<<30)) throw std::runtime_error("Original model split size exceeds its bound");
        total=checked_memory_sum(total,bytes);
        if(total>(512ull<<30)) throw std::runtime_error("Original model mapping exceeds its bound");
    }
    if(total<original_converted_tensor_bytes) throw std::runtime_error("Model splits cannot contain every original tensor");
    receipt_number(audit,"mapped_file_bytes",total);
    return total;
}
inline nlohmann::json read_model_receipt(const std::string & path) {
    std::ifstream input(path,std::ios::binary|std::ios::ate);
    const auto size=input ? input.tellg() : std::streampos(-1);
    if(size<=0 || size>std::streampos(1<<20)) throw std::runtime_error("Bounded original model receipt is required");
    std::string bytes(static_cast<std::size_t>(size),'\0');input.seekg(0);
    if(!input.read(bytes.data(),static_cast<std::streamsize>(bytes.size()))) throw std::runtime_error("Original model receipt read failed");
    return nlohmann::json::parse(bytes);
}
inline void validate_original_footprint(const ModelFootprint & model,std::uint64_t mapped_files) {
    if(model.trunk_layers!=48 || model.tensors!=1256 || model.device_weights!=8755105280ull ||
       model.mapped_experts!=241591910400ull || model.lazy_ple!=102400491520ull ||
       model.mapped_embeddings!=1271398400ull || model.skipped_mtp!=5217016832ull ||
       model.largest_device_tensor!=1271398400ull || model.mapped_files!=mapped_files)
        throw std::runtime_error("Transferred GGUF footprint differs from the complete original model plan");
}
}
