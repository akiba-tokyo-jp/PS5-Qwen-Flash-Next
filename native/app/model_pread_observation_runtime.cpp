// SPDX-License-Identifier: MIT
#include "model_pread_observation.h"
#include "model_pread_observation_runtime.h"
#include <algorithm>
#include <cstring>
#include <fcntl.h>
#include <new>
#include <ps5platform/heap.h>
#include <pthread.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>
extern "C" {
#include "hash/sha256/sha256.h"
ssize_t __real_pread(int,void*,std::size_t,off_t);
}
namespace {
using Trace=qwen_app::ModelPreadObservation<>;
Trace*owner=nullptr;
bool attempted=false;
void need(bool value,const char*message){if(!value)throw std::runtime_error(message);}
std::int64_t original(int fd,void*to,std::size_t bytes,std::int64_t offset){return __real_pread(fd,to,bytes,off_t(offset));}
qwen_app::ObservedReadIdentity inspect(int fd)noexcept{
    qwen_app::ObservedReadIdentity out;struct stat s{};
    out.flags=fcntl(fd,F_GETFL);const int rc=fstat(fd,&s);
    if(!rc)out.fields={std::uint64_t(s.st_dev),std::uint64_t(s.st_ino),std::uint64_t(s.st_size),
        std::uint64_t(s.st_mode),std::uint64_t(s.st_uid),std::uint64_t(s.st_gid),std::uint64_t(s.st_nlink),
        std::uint64_t(s.st_flags),std::uint64_t(s.st_mtim.tv_sec),std::uint64_t(s.st_mtim.tv_nsec),
        std::uint64_t(s.st_ctim.tv_sec),std::uint64_t(s.st_ctim.tv_nsec)};
    out.valid=!rc&&out.flags>=0&&(out.flags&O_ACCMODE)==O_RDONLY&&(out.flags&O_DIRECT)&&
        S_ISREG(s.st_mode)&&s.st_ino&&s.st_size>0&&!(s.st_mode&0022)&&s.st_nlink<=1;
    return out;
}
std::uint64_t now()noexcept{
    timespec t{};if(clock_gettime(CLOCK_MONOTONIC,&t)||t.tv_sec<0||t.tv_nsec<0||t.tv_nsec>=1000000000)return 0;
    return std::uint64_t(t.tv_sec)*1000000000ull+std::uint64_t(t.tv_nsec);
}
std::uint64_t thread()noexcept{
    const auto id=pthread_self();static_assert(sizeof(id)<=8,"Bounded diagnostic thread identity");
    std::uint64_t bits=0;std::memcpy(&bits,&id,sizeof(id));return bits;
}
}
extern "C" ssize_t __wrap_pread(int fd,void*to,std::size_t bytes,off_t offset){
    if(!owner)return __real_pread(fd,to,bytes,offset);
    return ssize_t(owner->read(fd,to,bytes,std::int64_t(offset)));
}
namespace qwen_app {
void begin_model_pread_observation(){
    need(!attempted&&!owner,"One model read observation preparation required");attempted=true;
    owner=new Trace({original,inspect,now,thread});
    need(ps5_heap_owns(owner),"Model read observation must use the tracked CPU heap");owner->begin();
}
void stop_model_pread_observation_after_request_completion(){
    need(owner,"A prepared source observation is required");owner->stop_after_original_source_completion();
}
nlohmann::json export_model_pread_observation_after_owner_retirement(const std::string&path,const nlohmann::json&binding){
    need(owner&&owner->stopped()&&path.rfind("/app0/qwen-runtime/plan-",0)==0&&path.size()<240,
         "Only completed source observations may be exported after original owner retirement");
    std::array<unsigned char,16384>header{};std::memcpy(header.data(),"QWENIO1",8);
    const std::uint32_t version=1,header_bytes=header.size(),row_bytes=sizeof(ObservedReadRow);
    const auto records=owner->retained();const auto json=binding.dump();const std::uint32_t json_bytes=json.size();
    need(json.size()<=header.size()-128,"A bounded model read observation binding is required");
    std::memcpy(header.data()+8,&version,4);std::memcpy(header.data()+12,&header_bytes,4);
    std::memcpy(header.data()+16,&row_bytes,4);std::memcpy(header.data()+20,&json_bytes,4);
    const std::uint64_t count=records;std::memcpy(header.data()+24,&count,8);std::memcpy(header.data()+128,json.data(),json.size());
    const int fd=open(path.c_str(),O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0644);
    need(fd>=0&&fchmod(fd,0644)==0,"Fresh readable source observation output required; retain owner on uncertainty");
    sha256_t hash;sha256_init(&hash);std::uint64_t written=0;
    const auto emit=[&](const unsigned char*data,std::size_t bytes){
        for(std::size_t at=0;at<bytes;){const auto n=std::min<std::size_t>(65536,bytes-at);
            need(::write(fd,data+at,n)==ssize_t(n),"Source observation write did not return its complete byte count; retain owner");
            sha256_update(&hash,data+at,n);at+=n;written+=n;}
    };
    emit(header.data(),header.size());emit(reinterpret_cast<const unsigned char*>(owner->rows()),records*sizeof(ObservedReadRow));
    struct stat s{};need(!fsync(fd)&&!fstat(fd,&s)&&s.st_size==off_t(written),"Source observation sync or exact size failed; retain owner");
    need(!close(fd),"Source observation descriptor close failed; retain owner");
    unsigned char digest[32];sha256_final(&hash,digest);std::string hex;
    for(auto byte:digest){hex+="0123456789abcdef"[byte>>4];hex+="0123456789abcdef"[byte&15];}
    const auto forwarded=owner->forwarded(),candidates=owner->candidates(),calls=owner->calls();delete owner;owner=nullptr;
    return {{"completed",true},{"path",path},{"bytes",written},{"sha256",hex},{"row_bytes",row_bytes},{"records",records},
        {"candidate_calls",candidates},{"observed_calls",calls},{"overflow_records",calls-records},{"forwarded_original_calls",forwarded},
        {"original_call_arguments_results_and_errno_preserved",true},{"original_reads_retried",0},
        {"source_payload_bytes_inspected",0},{"additional_workers",0},{"GPU_calls_added",0},
        {"source_file_opens_added",0},{"timings_usable_for_performance",false},
        {"exported_after_all_original_owners_retired",true},{"diagnostic_owners_positively_retired",true},
        {"native_generated_stream_SHA256",true},{"native_whole_file_readback_claimed",false}};
}
}
