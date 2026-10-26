// SPDX-License-Identifier: MIT
#pragma once
#include <nlohmann/json.hpp>
#include <cstdint>
#include <stdexcept>
#include <string>
namespace qwen_app {
inline void require_vector_bank_policy(const nlohmann::json &policy, bool display) {
    using Json = nlohmann::json;
    const auto check=[](bool ok) { if(!ok) throw std::runtime_error("Exact bounded vector-bank policy is required"); };
    const auto &p=policy.at("native_vector_bank_validation");
    const bool compact=p.value("schema",std::string())=="ps5-qwen-vector-bank-compact-v2";
    check(!display&&p.is_object()&&p.size()==(compact?12:11)&&
        (compact||p.at("schema")=="ps5-qwen-vector-bank-v1")&&p.at("enabled")==true&&
        p.at("driver_revision")=="872cc1264ad8ba5d6b888b092968fa5858a38c58"&&
        p.at("profile")=="cumulative-idle"&&
        p.at("native_archive_sha256")=="b57fe26e969940d147be05c1ffae830503d4865877281dffe03af32328f49925"&&
        p.at("model_loading_enabled")==false&&p.at("persistent_caches_enabled")==false&&
        p.at("maximum_GPU_memory_bytes").is_number_unsigned()&&p.at("rounds").is_number_unsigned()&&
        p.at("maximum_GPU_memory_bytes")==536870912u&&p.at("rounds")==8u);
    if(compact)check(p.at("journal_style")=="batch-memory-events-v1");
    auto hash=[&](const Json &v) {
        check(v.is_string());const auto text=v.get<std::string>();
        check(text.size()==64&&text.find_first_not_of("0123456789abcdef")==std::string::npos);
    };
    // This mode uses the application's linked GGML shader registry. Qualify
    // every original shader on the CPU before any Vulkan/device initialization.
    const auto &storage=policy.at("native_shader_storage");
    check(storage.is_object()&&storage.size()==11&&storage.at("schema")=="ps5-qwen-shader-storage-policy-v1"&&
        storage.at("enabled")==true&&storage.at("verify_all_original_assets_before_Vulkan")==true&&
        storage.at("model_and_shader_precision_unchanged")==true&&storage.at("persistent_caches_enabled")==false);
    hash(storage.at("registry_sha256"));
    for(const auto *key:{"shader_count","original_bytes","stored_bytes","lookup_entries"})
        check(storage.at(key).is_number_unsigned()&&storage.at(key).get<std::uint64_t>()>0);
    check(storage.at("shader_count")<=8192u&&storage.at("original_bytes")<=(512u<<20)&&
        storage.at("stored_bytes")<=(128u<<20)&&storage.at("lookup_entries")<=65536u);
    const auto &file=storage.at("external_file");check(file.is_object()&&file.size()==7);
    hash(file.at("sha256"));
    check(file.at("schema")=="ps5-qwen-external-shader-file-policy-v1"&&file.at("single_read_only_descriptor")==true&&
        file.at("new_model_source_window")==false&&file.at("bytes").is_number_unsigned()&&file.at("bytes")==storage.at("stored_bytes")&&
        file.at("path")==std::string("/app0/qwen-runtime/shader-storage-")+file.at("sha256").get<std::string>()+".bin"&&
        file.at("input_window_bytes").is_number_unsigned());
    const auto shader_window=file.at("input_window_bytes").get<std::uint64_t>();
    check(shader_window>0&&shader_window<=(1u<<20)&&shader_window%16384==0);
    const auto &packs=p.at("packs");check(packs.is_array()&&packs.size()==2);
    for(unsigned i=0;i<2;++i) {
        const auto &v=packs.at(i);check(v.is_object()&&v.size()==3);
        check(v.at("path")==std::string("/app0/qwen-runtime/vector-bank-")+std::to_string(i)+".pack");
        check(v.at("bytes").is_number_unsigned());const auto bytes=v.at("bytes").get<std::uint64_t>();
        check(bytes>4194304&&bytes<=(128u<<20)&&bytes%16384==0);hash(v.at("sha256"));
    }
    const auto &groups=p.at("groups");check(groups.is_array()&&groups.size()==13);
    unsigned seen[30]{};
    const unsigned residues[]={32,160,256,640,832,1120,1152,1184,1632,1696,1728,1760,1792,1824,2080,
        2208,2240,2304,2336,2784,3232,6688,6720,8320,11360,11424,12768,12832,12864,12928};
    for(unsigned g=0;g<13;++g) {
        const auto &group=groups.at(g);check(group.is_object()&&group.size()==2&&group.at("pack").is_number_unsigned()&&group.at("pack")==unsigned(g<3?0:1));
        const auto &items=group.at("matrices");check(items.is_array()&&items.size()==6);
        const auto size=packs.at(g<3?0:1).at("bytes").get<std::uint64_t>();
        for(unsigned i=0;i<6;++i) {
            const auto &m=items.at(i);check(m.is_object()&&m.size()==4&&m.at("offset").is_number_unsigned()&&m.at("residue").is_number_unsigned());
            const auto off=m.at("offset").get<std::uint64_t>(),r=m.at("residue").get<std::uint64_t>();
            check(off>=4194304&&off%16384==0&&off<=size&&3293184<=size-off&&r<16384&&r+3276800<=3293184);
            hash(m.at("raw_sha256"));hash(m.at("envelope_sha256"));
            if(i>=2)check(off==items.at(i%2).at("offset").get<std::uint64_t>()+(i/2)*3293184);
            if(i%2)check(m.at("residue")==items.at(i-1).at("residue"));
            for(unsigned j=0;j<i;++j) {
                const auto other=items.at(j).at("offset").get<std::uint64_t>();
                const bool duplicate=g>=3&&j==i-1&&i%2==1&&off==other;
                check(off>=other+3293184||other>=off+3293184||duplicate);
                if(duplicate)check(m==items.at(j));
            }
            if(g>=3) {
                bool found=false;for(unsigned j=0;j<30;++j)if(r==residues[j]){++seen[j];found=true;}
                check(found);
            }
        }
    }
    for(auto n:seen)check(n==2);
}
nlohmann::json admit_vector_bank(const nlohmann::json &,const std::string &);
}
