// SPDX-License-Identifier: MIT
#include "mapped_source.h"
#include "padded_bank_layout.h"
#include <iostream>
#include <map>
using namespace qwen_app;
static void check(bool value){if(!value)throw std::runtime_error("Six-bank source ownership control failed");}
struct Ops final:SourceReadOps {
    std::vector<SourceFile> files;std::map<int,unsigned> descriptors;
    unsigned reads=0,opens=0;bool changed=false,after=false,short_read=false;std::uint64_t free=512ull<<20;
    Ops(){for(unsigned i=0;i<3;++i){const auto bytes=(512ull<<20)-(i==2?7000:0);
        files.push_back({"part-"+std::to_string(i),bytes,{1,i+1,0100644,1,1,bytes,10,0,10,0}});descriptors[10+i]=i;}}
    SourceIdentity identity(int fd)override{auto id=files.at(descriptors.at(fd)).identity;if(changed||(after&&reads))++id[8];return id;}
    int open_direct(const std::string &path)override{for(unsigned i=0;i<files.size();++i)if(path==files[i].path){const int fd=100+int(++opens);descriptors[fd]=i;return fd;}return -1;}
    bool close_file(int fd)override{descriptors.erase(fd);return true;}
    std::uint64_t system_headroom()override{return free;}
    std::int64_t read_at(int fd,void *dst,std::size_t bytes,std::uint64_t offset)override{
        check(bytes%16384==0&&offset%16384==0&&reinterpret_cast<std::uintptr_t>(dst)%16384==0);
        const auto file=descriptors.at(fd);check(bytes&&offset+bytes<=files[file].bytes);++reads;
        std::memset(dst,int((file*19+offset/16384)%251),bytes);return std::int64_t(bytes)-(short_read?1:0);
    }
};
static constexpr std::uintptr_t base=1ull<<40,other=base+(2ull<<30);
static void setup(MappedSourceReader &reader){reader.register_mapping(base,1ull<<30,10);reader.register_mapping(other,(512ull<<20)-7000,12);reader.enable_source_schedule();}
static void *aligned(std::vector<unsigned char> &v){return reinterpret_cast<void *>((reinterpret_cast<std::uintptr_t>(v.data())+16383)&~std::uintptr_t(16383));}
int main(){try{
    const auto geometry=selected_padded_cache_geometry();const auto bytes=geometry.tensor_bytes();
    std::vector<unsigned char> window(model_read_window+16384),storage(3*(bytes+2*16384)+16384);
    auto owner=std::shared_ptr<void>(aligned(storage),[](void *){});const auto start=reinterpret_cast<std::uintptr_t>(owner.get());
    std::array<ExpertPrefetchDestination,3> banks;
    for(unsigned role=0;role<3;++role){auto *data=reinterpret_cast<unsigned char *>(start+role*(bytes+2*16384)+16384);
        banks[role]={data,bytes,4,std::shared_ptr<void>(owner,data)};}
    const std::array<int,2> slots{52,0};
    std::array<std::size_t,3> residues{32,96,160};std::array<std::uintptr_t,6> addresses{};
    auto addresses_for=[&]{for(unsigned role=0;role<3;++role){addresses[2*role]=base+(8u<<20)+residues[role];addresses[2*role+1]=other+(12u<<20)+residues[role];}};
    addresses_for();
    auto logical=[](const Ops &ops){return std::vector<LogicalSourceFile>{{ops.files[0].path,1ull<<30,{0,1}},{ops.files[2].path,ops.files[2].bytes,{2}}};};
    {
        Ops ops;MappedSourceReader reader(ops.files,ops,aligned(window),logical(ops));setup(reader);
        for(const auto shift:original_bank_residues){for(unsigned role=0;role<3;++role)residues[role]=shift;addresses_for();
            for(const auto &bank:banks){auto *at=static_cast<unsigned char *>(bank.data);std::memset(at-16384,0xa5,16384);std::memset(at+bytes,0xa5,16384);}
            check(reader.try_owned_bank_batch(addresses,banks,slots,residues,[&](const auto &requests){std::array<std::int64_t,6> got;
                for(unsigned i=0;i<6;++i)got[i]=ops.read_at(requests[i].fd,requests[i].target,requests[i].bytes,requests[i].offset);return got;}));
            for(const auto &bank:banks){auto *at=static_cast<unsigned char *>(bank.data);for(unsigned j=0;j<2;++j){
                const auto slot=geometry.slot(slots[j],shift,bytes,4);const auto value=static_cast<unsigned char>(((j?2*19:0)+(j?12u:8u)*64)%251);
                check(std::all_of(at+slot.aligned_write_offset,at+slot.aligned_write_offset+slot.requested_bytes,[&](auto x){return x==value;}));}
                check(std::all_of(at-16384,at,[](auto x){return x==0xa5;})&&std::all_of(at+bytes,at+bytes+16384,[](auto x){return x==0xa5;}));}
            reader.require_completed_window();
        }
        check(ops.reads==180&&reader.stats().physical_read_calls==180&&reader.stats().direct_bank_reads==180&&reader.stats().bytes==180*bank_expert_bytes);
        const auto reads=ops.reads,opens=ops.opens;residues.fill(32);addresses_for();addresses[1]=addresses[0]+bank_expert_bytes;
        check(!reader.try_owned_bank_batch(addresses,banks,slots,residues,[&](const auto &){throw std::runtime_error("Coalesced fallback issued a batch");return std::array<std::int64_t,6>{};}));
        addresses_for();addresses[0]=base+(512ull<<20)-bank_expert_bytes+32;
        check(!reader.try_owned_bank_batch(addresses,banks,slots,residues,[&](const auto &){throw std::runtime_error("Part crossing issued a batch");return std::array<std::int64_t,6>{};}));
        addresses_for();residues[0]=(ops.files[2].bytes-bank_expert_bytes)%16384;addresses[0]=other+ops.files[2].bytes-bank_expert_bytes;addresses[1]=other+(12u<<20)+residues[0];
        check(!reader.try_owned_bank_batch(addresses,banks,slots,residues,[&](const auto &){throw std::runtime_error("EOF fallback issued a batch");return std::array<std::int64_t,6>{};}));
        check(ops.reads==reads&&ops.opens==opens);reader.require_completed_window();
        reader.before_unmap(base,1ull<<30);reader.after_unmap(base,1ull<<30);reader.before_unmap(other,ops.files[2].bytes);reader.after_unmap(other,ops.files[2].bytes);reader.close_completed();
    }
    for(unsigned failure=0;failure<8;++failure){Ops ops;MappedSourceReader reader(ops.files,ops,aligned(window),logical(ops));setup(reader);
        residues.fill(32);addresses_for();auto test_banks=banks;auto test_slots=slots;
        if(failure==0)ops.free=0;if(failure==1)ops.changed=true;if(failure==2)ops.after=true;if(failure==3)ops.short_read=true;
        if(failure==4)test_banks[1]=test_banks[0];if(failure==5)test_banks[0].backing.reset();if(failure==6)test_slots[1]=test_slots[0];if(failure==7)addresses[0]=base-16384+32;
        bool refused=false;try{reader.try_owned_bank_batch(addresses,test_banks,test_slots,residues,[&](const auto &requests){std::array<std::int64_t,6> got;
            for(unsigned i=0;i<6;++i)got[i]=ops.read_at(requests[i].fd,requests[i].target,requests[i].bytes,requests[i].offset);return got;});}catch(const std::exception &){refused=true;}
        check(refused);const auto reads=ops.reads;check(failure==2||failure==3?reads==6:reads==0);
        refused=false;try{reader.require_completed_window();}catch(const std::exception &){refused=true;}check(refused&&ops.reads==reads);
    }
    std::cout<<"{\"original_residues\":30,\"exact_reads\":180,\"last_slot_guards\":true,\"pre_IO_fallbacks\":3,\"negative_controls\":8,\"source_conservation\":true}\n";
}catch(const std::exception &error){std::cerr<<error.what()<<'\n';return 1;}}
