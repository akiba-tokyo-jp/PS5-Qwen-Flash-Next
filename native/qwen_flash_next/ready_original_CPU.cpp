// SPDX-License-Identifier: MIT
// The actual original-source reader, CPU-only scratch; no model or GPU lease.
#include "ready_original_source.h"
#include "model_integrity.h"
#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>
extern "C" {
#include "hash/sha256/sha256.h"
int ready_CPU_permit(void);
int ready_CPU_record(const char *);
}
namespace {
using namespace qwen_app;
std::string digest(const void *at,std::size_t bytes){sha256_t h;sha256_init(&h);sha256_update(&h,static_cast<const unsigned char *>(at),bytes);
    unsigned char raw[32];sha256_final(&h,raw);std::string out;for(auto b:raw){out+="0123456789abcdef"[b>>4];out+="0123456789abcdef"[b&15];}return out;}
struct Ops final:SourceReadOps {
    SourceIdentity identity(int fd)override {
        struct stat s{};if(fd<0||!(fcntl(fd,F_GETFL)&O_DIRECT)||fstat(fd,&s)||!S_ISREG(s.st_mode)||!s.st_ino||s.st_size<=0||s.st_size>(512ll<<20)||(s.st_mode&0022))
            throw std::runtime_error("CPU source requires its exact sealed read-only Direct part");
        return {std::uint64_t(s.st_dev),std::uint64_t(s.st_ino),std::uint64_t(s.st_mode),std::uint64_t(s.st_uid),std::uint64_t(s.st_gid),
            std::uint64_t(s.st_size),std::uint64_t(s.st_mtim.tv_sec),std::uint64_t(s.st_mtim.tv_nsec),std::uint64_t(s.st_ctim.tv_sec),std::uint64_t(s.st_ctim.tv_nsec)};
    }
    int open_direct(const std::string &path)override{return open(path.c_str(),O_RDONLY|O_NOFOLLOW|O_DIRECT);}
    bool close_file(int fd)override{return close(fd)==0;}
    std::int64_t read_at(int fd,void *to,std::size_t bytes,std::uint64_t offset)override{return pread(fd,to,bytes,offset);}
    std::uint64_t system_headroom()override{return ready_CPU_permit()?256u<<20:0;}
};
bool verify(const ReadyOriginalMatrix &m,const void *at,void *) {
    return digest(at,padded_bank_stride)==m.envelope&&digest(static_cast<const unsigned char *>(at)+m.residue,bank_expert_bytes)==m.raw;
}
void stage(const char *text){if(!ready_CPU_record(text))throw std::runtime_error("CPU source journal did not persist");}
std::uint64_t now(){return std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now().time_since_epoch()).count();}
}
namespace qwen_app {std::string sha256_metadata_bytes(const std::string &text){return digest(text.data(),text.size());}}
extern "C" int ready_CPU_run(void *scratch,std::size_t bytes) {
    ReadyOriginalSource *source=nullptr;
    try {
        const auto *plan=compiled_ready_original_plan();if(!plan)throw std::runtime_error("Private original-source plan is missing");
        const auto deadline=std::chrono::steady_clock::now()+std::chrono::seconds(50);
        const unsigned widths[]={1,2,2,1,1,2,2,1};
        for(unsigned i=0;i<8;++i) {
            if(!ready_CPU_permit())throw std::runtime_error("CPU source no longer retains its operational reserves");
            auto *ops=new Ops;source=new ReadyOriginalSource(*plan,ReadyOriginalCPUScratch{scratch,bytes},widths[i],*ops,verify,nullptr,stage,deadline);
            stage(("CPU_CASE_BEFORE index="+std::to_string(i)+" width="+std::to_string(widths[i])).c_str());
            const auto start=now();source->fill_CPU_group(0);source->fill_CPU_group(1);const auto end=now();
            auto result=source->completed_report();result.update({{"schema","ps5-qwen-ready-original-CPU-case-v1"},{"index",i},
                {"elapsed_ns",end-start},{"model_loaded",false},{"GPU_calls",0},{"Vulkan_owner_claimed",false}});
            stage(("CPU_CASE_RESULT "+result.dump()).c_str());delete source;source=nullptr;delete ops;
        }
        return 1;
    }catch(const std::exception &e) {
        (void)ready_CPU_record((std::string("CPU_SOURCE_REFUSAL ")+e.what()).c_str());
        if(!source)return 0;
        try{return source->close_returned_CPU_failure()?0:-1;}catch(...){return -1;}
    }
}
