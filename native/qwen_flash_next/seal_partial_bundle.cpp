// SPDX-License-Identifier: MIT
// Seal only positively written Expert triplets from a closed partial output.
#include "partial_bundle_plan.h"
#include <ps5platform/kernel.h>
#include <algorithm>
#include <array>
#include <cerrno>
#include <cstring>
#include <fcntl.h>
#include <stdexcept>
#include <string>
#include <sys/stat.h>
#include <unistd.h>
extern "C" {
#include "hash/sha256/sha256.h"
int split_report_line(const char*);int split_open_journal();int split_context(unsigned);
int split_headroom();int split_close_journal();
}
namespace {
using Key=std::array<std::uint64_t,10>;constexpr std::uint64_t stride=1540096,window_bytes=8u<<20;
void need(bool value,const char*message){if(!value)throw std::runtime_error(message);}
void line(const std::string&s){need(s.size()<1000&&split_report_line(s.c_str()),"Partial seal journal failed");}
[[noreturn]]void retain(){split_report_line("UNCERTAIN CPU_owner_retained=1 GPU_calls=0 retry=0");for(;;)sleep(1);}
Key key(const struct stat&s){return{std::uint64_t(s.st_dev),std::uint64_t(s.st_ino),std::uint64_t(s.st_mode),std::uint64_t(s.st_uid),std::uint64_t(s.st_gid),std::uint64_t(s.st_size),std::uint64_t(s.st_mtim.tv_sec),std::uint64_t(s.st_mtim.tv_nsec),std::uint64_t(s.st_ctim.tv_sec),std::uint64_t(s.st_ctim.tv_nsec)};}
Key named(){struct stat s{};need(!lstat(partial_bundle_path,&s)&&S_ISREG(s.st_mode),"Owned partial path differs");return key(s);}
Key descriptor(int fd){struct stat s{};need(fd>=0&&!fstat(fd,&s)&&S_ISREG(s.st_mode),"Owned partial descriptor differs");return key(s);}
std::string digest(sha256_t&h){unsigned char value[32];sha256_final(&h,value);std::string out;for(auto b:value){out+="0123456789abcdef"[b>>4];out+="0123456789abcdef"[b&15];}return out;}
}
int main(int argc,char**){if(!split_open_journal())return 2;bool ok=false,mapped=false;void*window=nullptr;std::int64_t physical=-1;int fd=-1;
try{
 line("BEGIN nonce=" PARTIAL_BUNDLE_NONCE " CPU_only=1 GPU_calls=0 title_launches=0 original_source_writes=0");
 need((argc==0||argc==1)&&split_context(1)&&split_context(2)&&split_headroom(),"Partial seal requires the current idle CPU owner");
 fd=open(partial_bundle_path,O_RDONLY|O_NOFOLLOW|O_DIRECT);const auto before=descriptor(fd);
 need((fcntl(fd,F_GETFL)&O_DIRECT)&&before==named()&&before[2]==0100600&&!before[3]&&!before[4]&&
      before[5]>=partial_bundle_count*stride&&before[5]<=(partial_bundle_count+1)*stride,"Only this closed owned partial is admitted");
 need(!sceKernelAllocateDirectMemory(0,sceKernelGetDirectMemorySize(),window_bytes,16384,PS5_KERNEL_DIRECT_TYPE_CPU,&physical)&&physical>=0,"Partial seal CPU window allocation failed");
 if(sceKernelMapDirectMemory(&window,window_bytes,3,0,physical,16384)||!window)retain();mapped=true;
 sha256_t whole;sha256_init(&whole);
 for(unsigned i=0;i<partial_bundle_count;++i){need(split_context(3)&&split_headroom(),"Partial seal CPU owner changed");
  need(pread(fd,window,stride,i*stride)==std::int64_t(stride)&&descriptor(fd)==before&&named()==before,"Partial triplet read changed");
  sha256_t local;sha256_init(&local);sha256_update(&local,static_cast<unsigned char*>(window),stride);const auto actual=digest(local);
  need(actual==partial_bundle_expected[i],"Previously completed triplet hash differs");sha256_update(&whole,static_cast<unsigned char*>(window),stride);
  line("VERIFIED_PARTIAL index="+std::to_string(i)+" SHA256="+actual);
 }
 const auto tail=before[5]-partial_bundle_count*stride;
 if(tail){const auto rounded=(tail+16383)&~std::uint64_t(16383);need(pread(fd,window,rounded,partial_bundle_count*stride)==std::int64_t(tail),"Unused partial tail read changed");sha256_update(&whole,static_cast<unsigned char*>(window),tail);}
 need(descriptor(fd)==before&&named()==before,"Partial identity changed before publication");
 need(!fchmod(fd,0444)&&!fsync(fd),"Own partial readonly finalization failed");const auto after=descriptor(fd);need(after==named()&&after[2]==0100444,"Readonly partial identity differs");
 for(unsigned i:{0u,1u,3u,4u,5u,6u,7u})need(after[i]==before[i],"Partial contents or owner changed during mode finalization");
 std::string identity;for(auto value:after){if(!identity.empty())identity+=",";identity+=std::to_string(value);}
 line("SEALED_PARTIAL bytes="+std::to_string(after[5])+" SHA256="+digest(whole)+" identity="+identity+" verified_Experts="+std::to_string(partial_bundle_count)+" unused_tail_bytes="+std::to_string(tail));
 ok=true;
}catch(const std::exception&e){try{line(std::string("REFUSED reason=")+e.what());}catch(...){retain();}}
if(fd>=0&&close(fd))retain();
if(mapped){if(sceKernelMunmap(window,window_bytes)||sceKernelReleaseDirectMemory(physical,window_bytes))retain();line("DIRECT known_completion_cleanup_returned=1 fully_released=1");}else if(physical>=0)retain();
if(!split_context(5)||!split_headroom())ok=false;
line(std::string("END success=")+(ok?"1":"0")+" nonce=" PARTIAL_BUNDLE_NONCE " GPU_calls=0 title_launches=0 original_source_writes=0 retry=0");return split_close_journal()?(ok?0:3):4;}
