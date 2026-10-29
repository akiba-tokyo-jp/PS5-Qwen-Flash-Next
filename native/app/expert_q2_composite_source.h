// SPDX-License-Identifier: MIT
#pragma once
#include "expert_q2_source_integrity.h"
#include "expert_q4_source_integrity.h"
#include "expert_q2_sparse.h"
#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>
#include <map>
#include <cerrno>
#if !defined(_WIN32)
#include <ps5platform/kernel.h>
#endif

namespace qwen_app {
inline std::vector<ExpertQ2SourceSegments> expert_q2_pending_segments;
#if !defined(_WIN32)
inline SourceIdentity expert_q2_metadata_key(const struct stat&s){
    return {std::uint64_t(s.st_dev),std::uint64_t(s.st_ino),std::uint64_t(s.st_mode),
        std::uint64_t(s.st_uid),std::uint64_t(s.st_gid),std::uint64_t(s.st_size),
        std::uint64_t(s.st_mtim.tv_sec),std::uint64_t(s.st_mtim.tv_nsec),
        std::uint64_t(s.st_ctim.tv_sec),std::uint64_t(s.st_ctim.tv_nsec)};
}
// Small immutable metadata only. Weight payloads retain the original Direct
// source reader. The existing title nullfs may translate only st_dev.
inline nlohmann::json expert_q2_backing_metadata(const std::string&path,
        const nlohmann::json&record,const SourceIdentity&expected,std::string*raw_out=nullptr){
    const auto bytes=receipt_integer(record,"bytes");
    if(!bytes||bytes>(1u<<20)||expected[5]!=bytes)
        throw std::runtime_error("Bounded sealed backing metadata required");
    const int fd=open(path.c_str(),O_RDONLY|O_NOFOLLOW|O_DIRECT);
    if(fd<0)throw std::runtime_error("Backing metadata open failed");
    struct stat before{},after{},current{};
    bool ok=!fstat(fd,&before)&&S_ISREG(before.st_mode)&&before.st_mode==0100644&&
        !before.st_uid&&!before.st_gid&&std::uint64_t(before.st_size)==bytes;
    const auto identity=expert_q2_metadata_key(before);
    for(unsigned i=1;i<10;++i)ok=ok&&identity[i]==expected[i];
    if(!ok){const int closed=close(fd);
        throw std::runtime_error("Backing metadata identity differs "+nlohmann::json({{"path",path},
            {"actual",identity},{"expected",expected},{"close_rc",closed}}).dump());}
    std::string raw(bytes,'\0');void*window=nullptr;std::int64_t physical=-1;
    constexpr std::size_t window_bytes=1u<<20;
    const auto requested=(bytes+16383)&~std::uint64_t(16383);
    const int allocated=sceKernelAllocateDirectMemory(0,sceKernelGetDirectMemorySize(),window_bytes,
        16384,PS5_KERNEL_DIRECT_TYPE_CPU,&physical);
    if(allocated||physical<0){(void)close(fd);throw std::runtime_error("Explicit CPU Direct metadata allocation failed");}
    if(sceKernelMapDirectMemory(&window,window_bytes,3,0,physical,16384)||!window||
       reinterpret_cast<std::uintptr_t>(window)%16384){(void)close(fd);
        throw std::runtime_error("CPU Direct metadata map incomplete; physical owner retained until ordinary close");}
    errno=0;const auto got=pread(fd,window,requested,0);const int read_error=errno;
    ok=got==static_cast<ssize_t>(bytes);if(ok)std::memcpy(raw.data(),window,bytes);
    const auto tail=ok?pread(fd,window,16384,static_cast<off_t>(requested)):-1;
    const int after_rc=fstat(fd,&after);
    // Match the qualified application's descriptor ABI. Reopening with
    // O_NOFOLLOW independently binds the current named inode without lstat.
    const int named=open(path.c_str(),O_RDONLY|O_NOFOLLOW);
    const int path_rc=named<0?-1:fstat(named,&current);
    const int path_error=errno;
    const int named_closed=named<0?0:close(named);
    const auto actual_digest=sha256_metadata_bytes(raw);
    ok=ok&&tail==0&&!after_rc&&!path_rc&&
        expert_q2_metadata_key(after)==identity&&expert_q2_metadata_key(current)==identity&&
        actual_digest==record.at("sha256");
    const int closed=close(fd);
    if(closed||named_closed)throw std::runtime_error("CPU metadata descriptor close uncertain; Direct owner retained");
    if(sceKernelMunmap(window,window_bytes)||sceKernelReleaseDirectMemory(physical,window_bytes))
        throw std::runtime_error("CPU metadata Direct retirement uncertain; owner retained");
    if(!ok)throw std::runtime_error("Backing metadata read/SHA/identity failed "+nlohmann::json({
        {"path",path},{"read_bytes",got},{"read_errno",read_error},{"expected_bytes",bytes},{"EOF_return",tail},
        {"actual_SHA256",actual_digest},{"expected_SHA256",record.at("sha256")},{"before",identity},
        {"after",expert_q2_metadata_key(after)},{"path_identity",expert_q2_metadata_key(current)},
        {"fstat_rc",after_rc},{"named_fstat_rc",path_rc},{"named_errno",path_error},
        {"Direct_owner_positively_retired",true}}).dump());
    if(raw_out)*raw_out=raw;return nlohmann::json::parse(raw);
}

#else
inline nlohmann::json expert_q2_backing_metadata(const std::string&,const nlohmann::json&,
        const SourceIdentity&,std::string* =nullptr){
    throw std::runtime_error("Native backing metadata requires the PS5 descriptor ABI");
}
#endif

template<class MetadataRead>inline SplitModelIntegrity expert_q2_composite_source_integrity(const nlohmann::json&gate,
        const nlohmann::json&receipt,const std::string&root,std::uint64_t total_bytes,MetadataRead read_metadata){
    using Json=nlohmann::json;
    const auto require=[](bool ok){if(!ok)throw std::runtime_error("Complete packed Q2/Q4 source plan is not admitted");};
    require(expert_q2_source_root(root)&&receipt.at("packed_composite_sources")==true&&expert_q2_pending_segments.empty());
    const auto&proof=gate.at("Expert_Q2_source_integrity");
    require(proof.at("schema")=="ps5-qwen-expert-q2-source-policy-v1");
    const auto raw=proof.at("raw").get<std::string>();
    require(!raw.empty()&&raw.size()<=(2u<<20)&&sha256_metadata_bytes(raw)==proof.at("sha256"));
    const auto sealed=Json::parse(raw);
    require(sealed.at("schema")=="ps5-qwen-expert-q2-packed-source-integrity-v1"&&
        sealed.at("model_receipt_sha256")==gate.at("model_receipt_sha256")&&sealed.at("source_directory")==root&&
        sealed.at("canonical_source_directory")==std::string("/data/ai/native-moss-image-sft/PPSA99190")+root.substr(5)&&
        sealed.at("same_existing_title_nullfs_namespace")==true&&sealed.at("CPU_owners_positively_closed")==true&&
        sealed.at("all_new_parts_complete_Direct_SHA256_readback")==true&&sealed.at("all_parts_unchanged_since_readback")==true&&
        sealed.at("original_BF16_directories_and_parts_unchanged")==true&&sealed.at("source_writes")==0&&
        sealed.at("GPU_calls")==0&&sealed.at("model_loaded")==false&&sealed.at("automatic_retries")==0&&
        sealed.at("permission_changes")==0&&sealed.at("mount_changes")==0&&sealed.at("logical_bytes")==total_bytes);
    const auto key=[&](const Json&row){
        require(row.is_array()&&row.size()==10);SourceIdentity id{};
        for(unsigned i=0;i<10;++i){require(row[i].is_number_integer()&&row[i]>=0);id[i]=row[i].get<std::uint64_t>();}
        require(id[0]&&id[1]&&id[5]&&!id[3]&&!id[4]&&(id[2]==0100644||id[2]==0040755)&&
            id[7]<1000000000&&id[9]<1000000000);return id;
    };
    const auto&sidecars=sealed.at("backing_metadata");require(sidecars.size()==2);
    std::string prior_seal_raw;
    const Json prior_seal=read_metadata(root+"/retained-Q4-proof.json",
        receipt.at("retained_Q4_source_seal"),key(sidecars.at(0).at("identity")),&prior_seal_raw);
    require(prior_seal.at("schema")=="ps5-qwen-expert-q4-native-source-integrity-v1");
    const auto oldroot=prior_seal.at("source_directory").get<std::string>();require(expert_q4_source_root(oldroot));
    const auto oldreceipt_key=key(prior_seal.at("receipt_identity"));
    const Json pinned={{"bytes",606636},{"sha256","c88b821d6187fa2ca448c71ff8cbcc8db650ba720a0e698684338018fb71349b"}};
    const Json oldreceipt=read_metadata(oldroot+"/model-receipt.json",pinned,oldreceipt_key,nullptr);
    ExpertQ4Receipt old_manifest(oldreceipt);
    Json oldgate={{"model_receipt_sha256",pinned.at("sha256")},{"model_receipt_bytes",606636},
        {"Expert_Q4_source_integrity",{{"schema","ps5-qwen-expert-q4-source-policy-v1"},
            {"raw",prior_seal_raw},{"sha256",receipt.at("retained_Q4_source_seal").at("sha256")}}}};
    // Reuse the exact attested raw metadata, including its original line endings.
    const Json layout=read_metadata(root+"/retained-Q4-layout.json",
        receipt.at("retained_Q4_conversion"),key(sidecars.at(1).at("identity")),nullptr);
    require(layout.at("completed")==true&&layout.at("format")=="Q4_0"&&layout.at("files").size()==76);
    const auto old=expert_q4_source_integrity(oldgate,oldreceipt,oldroot,old_manifest.mapped_bytes);
    std::map<std::string,Json> old_tensors,old_layout,new_tensors;
    for(const auto&t:oldreceipt.at("tensors"))require(old_tensors.emplace(t.at("name").get<std::string>(),t).second);
    for(const auto&t:layout.at("tensors"))require(old_layout.emplace(t.at("name").get<std::string>(),t).second);
    for(const auto&t:receipt.at("tensors"))require(new_tensors.emplace(t.at("name").get<std::string>(),t).second);
    for(unsigned i=0;i<76;++i)require(layout.at("files")[i].at("path")==oldreceipt.at("files")[i].at("path")&&
        layout.at("files")[i].at("bytes")==oldreceipt.at("files")[i].at("bytes")&&
        layout.at("files")[i].at("sha256")==oldreceipt.at("files")[i].at("sha256"));
    SplitModelIntegrity result;result.prior.directory=key(sealed.at("directory_identity"));
    result.prior.receipt=key(sealed.at("receipt_identity"));result.part_directory_identity=result.prior.directory;
    require(result.prior.directory[2]==0040755&&result.prior.receipt[2]==0100644&&
        result.prior.receipt[5]==gate.at("model_receipt_bytes"));
    std::map<std::string,std::size_t> physical;
    const auto add=[&](const SourceFile&file){
        const auto found=physical.find(file.path);
        if(found!=physical.end()){require(result.physical[found->second].identity==file.identity&&result.physical[found->second].bytes==file.bytes);return found->second;}
        require(result.physical.size()<1024);const auto index=result.physical.size();physical.emplace(file.path,index);result.physical.push_back(file);return index;
    };
    const auto&files=sealed.at("logical_files");require(files.size()==76);
    std::vector<ExpertQ2SourceSegments> plans;std::uint64_t logical_total=0;
    for(unsigned i=0;i<76;++i){const auto&f=receipt.at("files")[i],&s=files[i];
        const auto name=f.at("path").get<std::string>();const auto bytes=receipt_integer(f,"bytes");
        require(s.at("path")==name&&s.at("bytes")==bytes&&s.at("sha256")==f.at("sha256"));
        const bool reused=f.at("reused_original")==true;LogicalSourceFile logical{expert_q2_logical_path(receipt,root,name),bytes,{}};
        if(reused){require(f.at("sha256")==oldreceipt.at("files")[i].at("sha256"));
            for(const auto index:old.logical[i].parts)logical.parts.push_back(add(old.physical[index]));
        }else{
            const auto packed=receipt_integer(f,"packed_bytes");require(packed&&packed<=bytes&&s.at("packed_bytes")==packed);
            const auto&parts=s.at("parts");require(parts.size()==(packed+model_source_part_bytes-1)/model_source_part_bytes);
            for(unsigned j=0;j<parts.size();++j){const auto&part=parts[j];const auto id=key(part.at("identity"));
                const auto count=std::min<std::uint64_t>(model_source_part_bytes,packed-j*model_source_part_bytes);
                const auto path=root+"/"+name+(j?".part-"+std::to_string(j):"");
                const auto digest=part.at("sha256").get<std::string>();
                require(part.at("path")==path&&part.at("bytes")==count&&part.at("offset")==j*model_source_part_bytes&&id[5]==count&&id[2]==0100644&&
                    digest.size()==64&&digest.find_first_not_of("0123456789abcdef")==std::string::npos&&digest==f.at("parts")[j].at("sha256"));
                logical.parts.push_back(add({path,count,id}));
            }
            ExpertQ2SourceSegments plan{logical.path,{}};const auto&regions=f.at("regions");
            std::uint64_t cursor=0,stored=0;std::size_t region_index=0;
            const auto emit=[&](std::uint64_t lo,std::uint64_t count,const char*storage,std::uint64_t offset,const Json*tensor){
                require(region_index<regions.size());const auto&r=regions[region_index++];
                require(r.at("logical_offset")==lo&&r.at("bytes")==count&&r.at("storage")==storage&&r.at("storage_offset")==offset);
                const auto*source=&logical.parts;
                if(std::string(storage)=="retained_Q4"){
                    require(tensor&&r.at("retained_file")==name&&r.at("tensor")==tensor->at("name")&&r.at("payload_sha256")==tensor->at("payload_sha256"));
                    source=&old.logical[i].parts;
                }
                for(std::uint64_t done=0;done<count;){const auto at=offset+done,part=at/model_source_part_bytes;
                    require(part<source->size());const auto original_index=(*source)[part];
                    const auto index=std::string(storage)=="new"?original_index:add(old.physical[original_index]);
                    const auto inside=at%model_source_part_bytes;require(inside<result.physical[index].bytes);
                    const auto n=std::min(count-done,result.physical[index].bytes-inside);
                    plan.segments.push_back({lo+done,n,index,inside});done+=n;
                }
            };
            const auto header=receipt_integer(f,"header_bytes");require(header&&header<=(64u<<20));
            emit(0,header,"new",0,nullptr);cursor=stored=header;
            for(const auto&t:receipt.at("tensors"))if(t.at("file")==name){
                const auto offset=receipt_integer(t,"offset"),count=receipt_integer(t,"bytes");require(offset==cursor);
                if(t.at("type")=="Q2_K"){emit(cursor,count,"new",stored,&t);stored+=count;}
                else{const auto tensor_name=t.at("name").get<std::string>();const auto&prior=old_tensors.at(tensor_name),&position=old_layout.at(tensor_name);
                    require(prior.at("file")==name&&prior.at("type")==t.at("type")&&prior.at("bytes")==count&&
                        prior.at("payload_sha256")==t.at("payload_sha256")&&position.at("output_payload_sha256")==t.at("payload_sha256")&&position.at("output_bytes")==count);
                    emit(cursor,count,"retained_Q4",receipt_integer(position,"output_offset"),&t);
                }
                cursor+=count;const auto padding=(-cursor)&31u;
                if(padding){emit(cursor,padding,"new",stored,nullptr);cursor+=padding;stored+=padding;}
            }
            require(cursor==bytes&&stored==packed&&region_index==regions.size());plans.push_back(std::move(plan));
        }
        require(!logical.parts.empty());result.prior.files.push_back(result.physical[logical.parts.front()].identity);
        logical_total+=bytes;result.logical.push_back(std::move(logical));
    }
    require(logical_total==total_bytes&&plans.size()==74);
    result.prior.report_sha256=proof.at("sha256").get<std::string>();result.prior.snapshot_sha256=result.prior.report_sha256;
    result.prior.original_elapsed_ms=receipt_integer(sealed,"verification_elapsed_ms");
    expert_q2_pending_segments=std::move(plans);return result;
}
inline SplitModelIntegrity expert_q2_composite_source_integrity(const nlohmann::json&gate,
        const nlohmann::json&receipt,const std::string&root,std::uint64_t total_bytes){
    return expert_q2_composite_source_integrity(gate,receipt,root,total_bytes,expert_q2_backing_metadata);
}

}
