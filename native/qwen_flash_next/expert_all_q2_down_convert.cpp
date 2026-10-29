// SPDX-License-Identifier: MIT
// Convert only original BF16 Down tensors. Gate/Up and all controls are retained.
#include "expert_all_q2_down_plan.h"
#include <ps5platform/kernel.h>
#include <algorithm>
#include <array>
#include <cerrno>
#include <condition_variable>
#include <cpuid.h>
#include <cstdio>
#include <cstring>
#include <fcntl.h>
#include <memory>
#include <mutex>
#include <stdexcept>
#include <string>
#include <sys/mount.h>
#include <sys/stat.h>
#include <thread>
#include <unistd.h>
extern "C" {
#include "hash/sha256/sha256.h"
int split_report_line(const char*);int split_open_journal();int split_context(unsigned);
int split_headroom();int split_close_journal();uint64_t split_now_ns();
int qwen_quantize_bf16_q2_0(const uint16_t*,uint8_t*,size_t);
unsigned qwen_sha256_acceleration_available();
}
namespace {
using Key=std::array<uint64_t,10>;
constexpr size_t io=4u<<20,owned_bytes=32u<<20,matrix_bytes=3276800,encoded_bytes=460800;
constexpr uint64_t part_bytes=512ull<<20;
uint64_t begun=0,completed=0,matrices=0;
unsigned char *input,*matrix,*encoded,*output,*readback;
void need(bool v,const char*m){if(!v)throw std::runtime_error(m);}
[[noreturn]]void retain(){split_report_line("UNCERTAIN CPU_owners_retained=1 retry=0");for(;;)sleep(1);}
void line(const std::string&s){need(s.size()<1000&&split_report_line(s.c_str()),"Durable CPU journal failed");}
Key key(const struct stat&s){return{uint64_t(s.st_dev),uint64_t(s.st_ino),uint64_t(s.st_mode),uint64_t(s.st_uid),uint64_t(s.st_gid),uint64_t(s.st_size),uint64_t(s.st_mtim.tv_sec),uint64_t(s.st_mtim.tv_nsec),uint64_t(s.st_ctim.tv_sec),uint64_t(s.st_ctim.tv_nsec)};}
Key path_key(const char*p,bool dir=false){struct stat s{};need(!lstat(p,&s)&&(dir?S_ISDIR(s.st_mode):S_ISREG(s.st_mode)),"Sealed source path missing");return key(s);}
Key fd_key(int fd){struct stat s{};need(!fstat(fd,&s)&&S_ISREG(s.st_mode)&&s.st_size>0,"Regular Direct descriptor required");return key(s);}
void close_fd(int&fd){if(fd>=0){int old=fd;fd=-1;if(close(old))retain();}}
void boundary(){const auto n=split_now_ns();need(n>=begun&&n-begun<=7200000000000ULL&&split_headroom(),"CPU deadline or memory boundary refused");}
void roots(){need(path_key(down_original_root,true)==down_original_root_identity&&path_key(down_original_parts_root,true)==down_original_parts_identity,"Original BF16 directory seal changed");}
void all_sources(){roots();for(const auto&p:down_original_parts)need(path_key(p.path)==p.identity,"Original BF16 part identity changed");}
std::string hex(sha256_t*h){unsigned char d[32];sha256_final(h,d);std::string s;for(auto v:d){s+="0123456789abcdef"[v>>4];s+="0123456789abcdef"[v&15];}return s;}
void record_key(const std::string&label,const Key&k){auto s=label;for(auto v:k)s+=" "+std::to_string(v);line(s);}
void capacity(uint64_t remaining){struct statfs s{};need(!statfs(down_destination_parent,&s)&&s.f_bsize==65536&&s.f_bavail>0&&uint64_t(s.f_bavail)*s.f_bsize>=remaining+(2ull<<30)+(64ull<<20),"Down conversion must retain two GiB and metadata disk headroom");}
struct Pool {
 std::mutex mutex;std::condition_variable ready,done;std::array<std::thread,4>threads;
 unsigned epoch=0,finished=0;bool stopping=false;std::array<int,4>results{};
 Pool(){try{for(unsigned slot=0;slot<4;++slot)threads[slot]=std::thread([this,slot]{unsigned seen=0;std::unique_lock<std::mutex>lock(mutex);for(;;){ready.wait(lock,[&]{return stopping||seen!=epoch;});if(stopping)return;seen=epoch;lock.unlock();const int rc=qwen_quantize_bf16_q2_0(reinterpret_cast<uint16_t*>(matrix+slot*matrix_bytes),encoded+slot*encoded_bytes,1638400);lock.lock();results[slot]=rc;if(++finished==4)done.notify_one();}});}catch(...){stop();throw;}}
 void stop(){{std::lock_guard<std::mutex>lock(mutex);stopping=true;}ready.notify_all();for(auto&t:threads)if(t.joinable())t.join();}
 ~Pool(){stop();}
 void encode(){std::unique_lock<std::mutex>lock(mutex);finished=0;++epoch;ready.notify_all();done.wait(lock,[&]{return finished==4;});for(int v:results)need(v==0,"Qualified MSE encoder refused input");}
};
struct Source {
 const DownTensor&t;int fd=-1;unsigned part=UINT32_MAX;uint64_t cursor,cache_start=0;size_t cached=0;sha256_t hash;
 explicit Source(const DownTensor&v):t(v),cursor(v.source_offset){sha256_init(&hash);}
 ~Source(){close_fd(fd);}
 void load(){boundary();unsigned wanted=unsigned(cursor/part_bytes);need(wanted<t.part_count,"BF16 payload exceeds source parts");
  if(part!=wanted){close_fd(fd);part=wanted;const auto&p=down_original_parts[t.first_part+part];fd=open(p.path,O_RDONLY|O_NOFOLLOW|O_DIRECT);need(fd>=0&&(fcntl(fd,F_GETFL)&O_DIRECT)&&fd_key(fd)==p.identity&&path_key(p.path)==p.identity,"Original BF16 Direct identity differs");}
  const auto&p=down_original_parts[t.first_part+part];const uint64_t local=(cursor%part_bytes)&~uint64_t(16383);need(local<p.identity[5],"Original Direct range invalid");
  const auto n=size_t(std::min<uint64_t>(io,p.identity[5]-local));line("BEFORE Down_BF16_read layer="+std::to_string(t.layer)+" offset="+std::to_string(uint64_t(part)*part_bytes+local));
  const auto got=pread(fd,input,(n+16383)&~size_t(16383),local);line("RETURN Down_BF16_read bytes="+std::to_string(got));
  need(got==ssize_t(n)&&fd_key(fd)==p.identity&&path_key(p.path)==p.identity,"Original BF16 Direct read or identity failed");cache_start=uint64_t(part)*part_bytes+local;cached=n;
 }
 void copy(unsigned char*out,size_t count){need(cursor>=t.source_offset&&count<=t.source_bytes-(cursor-t.source_offset),"BF16 payload bounds differ");while(count){if(!cached||cursor<cache_start||cursor>=cache_start+cached)load();const auto n=size_t(std::min<uint64_t>(count,cache_start+cached-cursor));const auto*p=input+cursor-cache_start;memcpy(out,p,n);sha256_update(&hash,p,n);out+=n;cursor+=n;count-=n;}}
 void finish(){need(cursor==t.source_offset+t.source_bytes&&hex(&hash)==t.original_payload_sha256,"Complete original Down payload SHA256 differs");close_fd(fd);}
};
struct Writer {
 const DownTensor&t;int fd=-1;uint64_t written=0;size_t buffered=0;sha256_t hash;std::string target,pending;
 explicit Writer(const DownTensor&v):t(v),target(std::string(down_destination)+"/"+v.output_name),pending(target+".pending"){
  struct stat s{};errno=0;need(lstat(target.c_str(),&s)<0&&errno==ENOENT,"New Down final path must be absent");
  fd=open(pending.c_str(),O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW|O_DIRECT,0600);need(fd>=0&&(fcntl(fd,F_GETFL)&O_DIRECT),"Exclusive new Down Direct output required");sha256_init(&hash);
 }
 ~Writer(){close_fd(fd);}
 void flush(){if(!buffered)return;boundary();need(buffered%16384==0,"Dense Down output must be Direct aligned without a padded tail");line("BEFORE Down_output_write layer="+std::to_string(t.layer)+" offset="+std::to_string(written));const auto got=pwrite(fd,output,buffered,written);line("RETURN Down_output_write bytes="+std::to_string(got));need(got==ssize_t(buffered),"Down output write was short");written+=buffered;buffered=0;}
 void put(const unsigned char*p,size_t n){need(n<=235929600-written-buffered,"Down output bounds differ");sha256_update(&hash,p,n);while(n){const auto take=std::min(n,io-buffered);memcpy(output+buffered,p,take);p+=take;n-=take;buffered+=take;if(buffered==io)flush();}}
 std::string finish(){flush();need(written==235929600&&!fsync(fd),"Complete Down output size/fsync differs");close_fd(fd);fd=open(pending.c_str(),O_RDONLY|O_NOFOLLOW|O_DIRECT);need(fd>=0&&(fcntl(fd,F_GETFL)&O_DIRECT),"New Down Direct readback required");const auto before=fd_key(fd);need(before[5]==written,"Down readback size differs");sha256_t h;sha256_init(&h);
  for(uint64_t at=0;at<written;){boundary();const auto n=size_t(std::min<uint64_t>(io,written-at));line("BEFORE Down_readback layer="+std::to_string(t.layer)+" offset="+std::to_string(at));const auto got=pread(fd,readback,n,at);line("RETURN Down_readback bytes="+std::to_string(got));need(got==ssize_t(n),"Complete Down readback short");sha256_update(&h,readback,n);at+=n;}
  const auto expected=hex(&hash);need(hex(&h)==expected&&fd_key(fd)==before&&path_key(pending.c_str())==before&&pread(fd,readback,16384,written)==0,"Down whole readback SHA256, identity or EOF differs");
  need(!fchmod(fd,0644)&&!fsync(fd),"Down output seal failed");close_fd(fd);need(!rename(pending.c_str(),target.c_str()),"New Down publication failed");const auto published=path_key(target.c_str());need(published[5]==written&&published[2]==0100644&&!published[3]&&!published[4],"Published Down identity differs");
  line("DOWN_FILE layer="+std::to_string(t.layer)+" bytes="+std::to_string(written)+" SHA256="+expected+" original_payload_SHA256="+t.original_payload_sha256);record_key("DOWN_ID layer="+std::to_string(t.layer),published);return expected;
 }
};
}
int main(int argc,char**){if(!split_open_journal())return 2;begun=split_now_ns();bool ok=false,mapped=false;void*owned=nullptr;int64_t physical=-1;std::unique_ptr<Source>source;std::unique_ptr<Writer>writer;
 try{line("BEGIN nonce=" DOWN_NONCE " CPU_only=1 source_writes=0 GPU_calls=0 title_launches=0 window_bytes=33554432 CPU_workers=4");need((argc==0||argc==1)&&begun&&split_context(1)&&split_context(2),"Fresh idle CPU conversion required");boundary();all_sources();capacity(11560550400ULL);need(qwen_sha256_acceleration_available()==1,"Qualified SHA extension required");unsigned a,b,c,d;need(__get_cpuid(1,&a,&b,&c,&d)&&(c&bit_F16C),"Qualified F16C encoder required");
  need(!sceKernelAllocateDirectMemory(0,sceKernelGetDirectMemorySize(),owned_bytes,16384,PS5_KERNEL_DIRECT_TYPE_CPU,&physical)&&physical>=0,"Bounded Down CPU Direct allocation failed");if(sceKernelMapDirectMemory(&owned,owned_bytes,3,0,physical,16384)||!owned||uintptr_t(owned)%16384)retain();mapped=true;
  input=static_cast<unsigned char*>(owned);matrix=input+(4u<<20);encoded=input+(17u<<20);output=input+(20u<<20);readback=input+(24u<<20);
  need(!mkdir(down_destination,0755),"Fresh candidate directory must not exist");Pool pool;bool parallel_checked=false;
  for(const auto&t:down_tensors){boundary();roots();need(split_context(3),"Idle CPU owner changed");capacity((49-completed)*235929600ULL);source=std::make_unique<Source>(t);writer=std::make_unique<Writer>(t);
   for(unsigned first=0;first<512;first+=4){for(unsigned i=0;i<4;++i)source->copy(matrix+i*matrix_bytes,matrix_bytes);boundary();pool.encode();
    if(!parallel_checked){for(unsigned i=0;i<4;++i)need(!qwen_quantize_bf16_q2_0(reinterpret_cast<uint16_t*>(matrix+i*matrix_bytes),readback,1638400)&&!memcmp(readback,encoded+i*encoded_bytes,encoded_bytes),"Four-worker Down differs from qualified serial encoder");parallel_checked=true;line("CPU_POOL MSE_Q2_0=1 workers=4 serial_byte_checks=4 exact=1");}
    for(unsigned i=0;i<4;++i){for(const auto&s:down_samples)if(s.layer==t.layer&&s.expert==first+i){sha256_t h;sha256_init(&h);sha256_update(&h,encoded+i*encoded_bytes,encoded_bytes);need(hex(&h)==s.sha256,"Down matrix differs from independently host-qualified MSE bytes");line("DOWN_SAMPLE layer="+std::to_string(t.layer)+" expert="+std::to_string(first+i)+" exact_host_SHA256=1");}writer->put(encoded+i*encoded_bytes,encoded_bytes);++matrices;}}
   source->finish();source.reset();writer->finish();writer.reset();++completed;roots();}
  need(completed==49&&matrices==25088&&parallel_checked,"Complete 49-layer / 512-Expert Down conversion required");pool.stop();line("CPU_POOL all_workers_joined=1");all_sources();record_key("DOWN_DIRECTORY",path_key(down_destination,true));ok=true;
 }catch(const std::exception&e){try{line(std::string("REFUSED reason=")+e.what()+" partial_candidate_retained=1 original_sources_unchanged=1");}catch(...){retain();}}
 source.reset();writer.reset();if(mapped){if(sceKernelMunmap(owned,owned_bytes)||sceKernelReleaseDirectMemory(physical,owned_bytes))retain();if(!split_report_line("DIRECT known_completion_cleanup_returned=1 fully_released=1"))retain();}else if(physical>=0)retain();
 if(!split_context(5)||!split_headroom())ok=false;try{line("END success="+std::to_string(ok)+" files="+std::to_string(completed)+" matrices="+std::to_string(matrices)+" active_calls=0 source_writes=0 GPU_calls=0 title_launches=0 retry=0");}catch(...){retain();}if(!split_close_journal())return 2;return ok?0:1;
}
