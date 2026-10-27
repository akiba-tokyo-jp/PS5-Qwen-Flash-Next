// SPDX-License-Identifier: MIT
#include "mapped_source.h"
#include "padded_bank_layout.h"
#include <map>
#include <iostream>
using namespace qwen_app;
static void check(bool v){if(!v)throw std::runtime_error("Owned bank I/O control failed");}
template<class F>static void refused(F action){bool bad=false;try{action();}catch(const std::exception&){bad=true;}check(bad);}
struct Ops final:SourceReadOps{
    std::vector<SourceFile> files;std::map<int,unsigned> descriptors;
    unsigned reads=0,opens=0,parallel=0,pipeline=0;bool short_read=false,changed=false;
    std::uint64_t free=512ull<<20;
    Ops(){for(unsigned i=0;i<3;++i){const auto bytes=(512ull<<20)-(i==2?7000:0);
        files.push_back({"part-"+std::to_string(i),bytes,{1,i+1,0100644,1,1,bytes,10,0,10,0}});descriptors[10+i]=i;}}
    SourceIdentity identity(int fd)override{auto result=files.at(descriptors.at(fd)).identity;if(changed)++result[8];return result;}
    int open_direct(const std::string &path)override{for(unsigned i=0;i<files.size();++i)if(files[i].path==path){const int fd=100+int(++opens);descriptors[fd]=i;return fd;}return -1;}
    bool close_file(int fd)override{descriptors.erase(fd);return true;}
    std::int64_t read_at(int fd,void *dst,std::size_t bytes,std::uint64_t offset)override{
        check(bytes&&bytes%16384==0&&offset%16384==0&&reinterpret_cast<std::uintptr_t>(dst)%16384==0);
        const auto file=descriptors.at(fd);check(offset+bytes<=files[file].bytes);++reads;
        const auto value=static_cast<unsigned char>((file*19+offset/16384)%251);
        std::memset(dst,value,bytes);return std::int64_t(bytes)-(short_read?1:0);
    }
    std::array<std::int64_t,2> read_pair(const std::array<SourceReadRequest,2>&r)override{
        ++parallel;return {read_at(r[0].fd,r[0].target,r[0].bytes,r[0].offset),read_at(r[1].fd,r[1].target,r[1].bytes,r[1].offset)};
    }
    SourcePipelineTimes pipeline_pair(const std::array<SourceReadRequest,2>&r,const std::array<std::uint64_t,2>&expected,
        const std::function<void(unsigned)> &before,const std::function<void(unsigned,const void*)>&consume)override{
        ++pipeline;for(unsigned i=0;i<2;++i){before(i);check(read_at(r[i].fd,r[i].target,r[i].bytes,r[i].offset)==std::int64_t(expected[i]));consume(i,r[i].target);}
        return {1,1,1};
    }
    std::uint64_t system_headroom()override{return free;}
};
static constexpr std::uintptr_t base=1ull<<40,other=base+(2ull<<30);
static std::vector<LogicalSourceFile> logical(const Ops &ops){return {{ops.files[0].path,1ull<<30,{0,1}},
    {ops.files[2].path,ops.files[2].bytes,{2}}};}
static void setup(MappedSourceReader &reader){reader.register_mapping(base,1ull<<30,10);
    reader.register_mapping(other,(512ull<<20)-7000,12);reader.enable_source_schedule();}
static void *aligned(std::vector<unsigned char>&v){const auto at=reinterpret_cast<std::uintptr_t>(v.data());
    return reinterpret_cast<void*>((at+16383)&~std::uintptr_t(16383));}
int main(int argc,char **argv){try{
    if(argc==2&&std::string(argv[1])=="--large")select_experimental_padded_cache_128();
    else if(argc!=1)throw std::invalid_argument("Unknown padded source test scope");
    const auto geometry=selected_padded_cache_geometry();const auto last=geometry.active_slots-1;
    const auto bytes=geometry.tensor_bytes();
    std::vector<unsigned char> window(model_read_window+16384),storage(bytes+3*16384);
    auto *scratch=aligned(window);auto *guard=static_cast<unsigned char*>(aligned(storage));auto *bank=guard+16384;
    const int slots[2]={int(last),0};
    {
        Ops ops;MappedSourceReader reader(ops.files,ops,scratch,logical(ops));setup(reader);
        for(const auto residue:original_bank_residues){
            std::memset(bank+last*padded_bank_stride-16384,0xa5,16384);
            std::memset(bank+geometry.active_slots*padded_bank_stride,0xa5,16384);
            check(reader.source_bank_residue(base+(8u<<20)+residue,bank_expert_bytes)==residue);
            check(reader.try_owned_bank_reads({base+(8u<<20)+residue,other+(12u<<20)+residue},2,slots,residue,bank,bytes,4));
            for(const auto slot:{std::size_t(0),last}){
                const auto value=static_cast<unsigned char>(((slot==0?2*19:0)+(slot==0?12u:8u)*64)%251);
                check(std::all_of(bank+slot*padded_bank_stride,bank+(slot+1)*padded_bank_stride,[&](auto b){return b==value;}));
            }
            check(std::all_of(bank+last*padded_bank_stride-16384,bank+last*padded_bank_stride,[](auto b){return b==0xa5;}));
            check(std::all_of(bank+geometry.active_slots*padded_bank_stride,bank+geometry.active_slots*padded_bank_stride+16384,[](auto b){return b==0xa5;}));
        }
        check(ops.parallel==30&&reader.stats().direct_bank_reads==60&&reader.stats().direct_bank_bytes==60*bank_expert_bytes);
        check(reader.try_owned_bank_reads({base+32,other+32},2,slots,32,bank,bytes,4));check(ops.pipeline==1);
        check(reader.try_owned_bank_reads({base+(8u<<20)+32,0},1,slots,32,bank,bytes,4));
        const auto reads=ops.reads,opens=ops.opens;
        check(!reader.try_owned_bank_reads({base+32,base+32+bank_expert_bytes},2,slots,32,bank,bytes,4));
        check(!reader.try_owned_bank_reads({base+(512ull<<20)-bank_expert_bytes+32,0},1,slots,32,bank,bytes,4));
        const auto eof=other+ops.files[2].bytes-bank_expert_bytes;
        check(!reader.try_owned_bank_reads({eof,0},1,slots,(ops.files[2].bytes-bank_expert_bytes)%16384,bank,bytes,4));
        check(ops.reads==reads&&ops.opens==opens);reader.require_completed_window();
        reader.record_padded_scatter(2*bank_expert_bytes);check(reader.stats().padded_scatter_bytes==2*bank_expert_bytes);
        reader.before_unmap(base,1ull<<30);reader.after_unmap(base,1ull<<30);
        reader.before_unmap(other,ops.files[2].bytes);reader.after_unmap(other,ops.files[2].bytes);reader.close_completed();
    }
    for(unsigned failure=0;failure<8;++failure){
        Ops ops;MappedSourceReader reader(ops.files,ops,scratch,logical(ops));setup(reader);
        if(failure==0)ops.short_read=true;if(failure==1)ops.free=0;
        const int badslots[2]={int(last),int(failure==2?last:geometry.active_slots)};
        refused([&]{reader.try_owned_bank_reads({base+(8u<<20)+(failure==4?34:32),other+(12u<<20)+32},failure==0?1:2,
            (failure==2||failure==3)?badslots:slots,32,failure==5?bank+1:bank,
            failure==6?bytes-1:bytes,failure==7?256:4);});
        const auto reads=ops.reads;refused([&]{reader.require_completed_window();});
        refused([&]{reader.try_owned_bank_reads({base+32,0},1,slots,32,bank,bytes,4);});check(ops.reads==reads);
        check(failure==0?reads==1:reads==0);
    }
    std::cout<<"Owned aligned bank bytes, both read schedules, all original residues, last-slot guards, pre-I/O fallback and no-retry quarantine passed\n";
}catch(const std::exception &e){std::cerr<<e.what()<<'\n';return 1;}}
