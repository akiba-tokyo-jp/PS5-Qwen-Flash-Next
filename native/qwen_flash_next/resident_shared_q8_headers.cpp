// SPDX-License-Identifier: MIT
// Extract only owned new GGUF prefixes; retain every immutable parent file.
#include "shared_Q8_headers_plan.h"
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
int split_headroom();int split_close_journal();std::uint64_t split_now_ns();
}
namespace {
using Key=std::array<std::uint64_t,10>;constexpr std::size_t window_bytes=8u<<20;
void need(bool b,const char*m){if(!b)throw std::runtime_error(m);}
[[noreturn]]void retain(){split_report_line("UNCERTAIN CPU_resources_retained=1 retry=0");for(;;)sleep(1);}
void line(const std::string&s){need(s.size()<1000&&split_report_line(s.c_str()),"Shared header journal failed");}
Key key(const struct stat&s){return{std::uint64_t(s.st_dev),std::uint64_t(s.st_ino),std::uint64_t(s.st_mode),std::uint64_t(s.st_uid),std::uint64_t(s.st_gid),std::uint64_t(s.st_size),std::uint64_t(s.st_mtim.tv_sec),std::uint64_t(s.st_mtim.tv_nsec),std::uint64_t(s.st_ctim.tv_sec),std::uint64_t(s.st_ctim.tv_nsec)};}
Key named(const char*p,bool directory=false){struct stat s{};need(!lstat(p,&s)&&(directory?S_ISDIR(s.st_mode):S_ISREG(s.st_mode)),"Owned shared header path differs");return key(s);}
Key descriptor(int fd){struct stat s{};need(fd>=0&&!fstat(fd,&s)&&S_ISREG(s.st_mode),"Shared header descriptor differs");return key(s);}
void close_fd(int&fd){if(fd>=0){const int old=fd;fd=-1;if(close(old))retain();}}
std::string digest(sha256_t&h){unsigned char raw[32];sha256_final(&h,raw);std::string s;for(auto b:raw){s+="0123456789abcdef"[b>>4];s+="0123456789abcdef"[b&15];}return s;}
void emit(const std::string&label,const Key&k){std::string s=label;for(auto v:k)s+=" "+std::to_string(v);line(s);}
}
int main(int argc,char**){if(!split_open_journal())return 2;bool ok=false,mapped=false;void*window=nullptr;std::int64_t physical=-1;int input=-1,output=-1;const auto begun=split_now_ns();
 try{
    line("BEGIN nonce=" SHARED_Q8_HEADERS_NONCE " CPU_only=1 GPU_calls=0 original_source_writes=0");
    need((argc==0||argc==1)&&begun&&split_context(1)&&split_context(2)&&split_headroom(),"Current idle owner or CPU memory refused");
    need(named(shared_header_directory,true)==shared_header_directory_key&&named(shared_header_pack)==shared_header_pack_key&&named(shared_header_receipt)==shared_header_receipt_key,"Published shared assets changed before header extraction");
    need(!sceKernelAllocateDirectMemory(0,sceKernelGetDirectMemorySize(),window_bytes,16384,PS5_KERNEL_DIRECT_TYPE_CPU,&physical)&&physical>=0,"Bounded CPU header allocation failed");
    if(sceKernelMapDirectMemory(&window,window_bytes,3,0,physical,16384)||!window||std::uintptr_t(window)%16384)retain();mapped=true;
    input=open(shared_header_pack,O_RDONLY|O_NOFOLLOW|O_DIRECT);need(input>=0&&descriptor(input)==shared_header_pack_key,"Immutable Q8 pack cannot reopen");
    for(unsigned i=0;i<std::size(shared_headers);++i){const auto&h=shared_headers[i];
        need(split_context(3)&&split_headroom()&&split_now_ns()-begun<300000000000ull,"Header owner, memory or deadline refused");
        struct stat absent{};errno=0;need(lstat(h.path,&absent)&&errno==ENOENT,"Header extraction may not overwrite a file");
        output=open(h.path,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0600);need(output>=0,"Exclusive new GGUF header creation failed");
        sha256_t expected;sha256_init(&expected);
        for(std::uint64_t at=0;at<h.bytes;){const auto n=std::size_t(std::min<std::uint64_t>(window_bytes,h.bytes-at)),count=(n+16383)&~std::size_t(16383);
            need(split_headroom()&&h.offset+at<=shared_header_pack_key[5]&&count<=shared_header_pack_key[5]-h.offset-at,"Header source exceeds its immutable pack");
            line("BEFORE owned_header_read index="+std::to_string(i)+" offset="+std::to_string(at));const auto got=pread(input,window,count,h.offset+at);
            need(got==std::int64_t(count)&&descriptor(input)==shared_header_pack_key,"Complete owned header source read required");
            sha256_update(&expected,static_cast<unsigned char*>(window),n);need(write(output,window,n)==std::int64_t(n),"Owned header write was short");at+=n;
        }
        need(digest(expected)==h.sha256&&!fchmod(output,0644)&&!fsync(output),"Header source hash or durability differs");const auto written=descriptor(output);close_fd(output);
        output=open(h.path,O_RDONLY|O_NOFOLLOW|O_DIRECT);need(output>=0&&descriptor(output)==written&&written[2]==0100644&&!written[3]&&!written[4]&&written[5]==h.bytes,"New readonly header identity differs");
        sha256_t actual;sha256_init(&actual);
        for(std::uint64_t at=0;at<h.bytes;){const auto n=std::size_t(std::min<std::uint64_t>(window_bytes,h.bytes-at)),count=(n+16383)&~std::size_t(16383);
            need(split_headroom()&&pread(output,window,count,at)==std::int64_t(n),"New header Direct readback incomplete");sha256_update(&actual,static_cast<unsigned char*>(window),n);at+=n;}
        need(digest(actual)==h.sha256&&pread(output,window,16384,(h.bytes+16383)&~std::uint64_t(16383))==0&&descriptor(output)==written&&named(h.path)==written,"New header full SHA256, EOF or identity differs");
        close_fd(output);emit("SEALED_HEADER index="+std::to_string(i),written);
    }
    need(descriptor(input)==shared_header_pack_key&&named(shared_header_pack)==shared_header_pack_key&&named(shared_header_receipt)==shared_header_receipt_key,"Immutable pack or receipt changed during extraction");
    const auto directory=named(shared_header_directory,true);need(std::equal(directory.begin(),directory.begin()+5,shared_header_directory_key.begin()),"Owned shared directory identity changed");emit("SEALED_DIRECTORY",directory);
    need(split_context(5)&&split_headroom(),"Final idle CPU owner refused");ok=true;
 }catch(const std::exception&e){try{line(std::string("REFUSED reason=")+e.what()+" own_new_headers_retained=1 original_sources_unchanged=1");}catch(...){retain();}}
 close_fd(output);close_fd(input);if(mapped){if(sceKernelMunmap(window,window_bytes)||sceKernelReleaseDirectMemory(physical,window_bytes))retain();line("DIRECT known_completion_cleanup_returned=1 fully_released=1");}else if(physical>=0)retain();
 line("END success="+std::to_string(ok)+" nonce=" SHARED_Q8_HEADERS_NONCE " active_calls=0 original_source_writes=0 GPU_calls=0 title_launches=0 retry=0");if(!split_close_journal())return 2;return ok?0:1;
}
