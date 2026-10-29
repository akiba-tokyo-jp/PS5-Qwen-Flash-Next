// SPDX-License-Identifier: MIT
// Move only the completed experiment's own directory into its existing title.
// No original weights, directory permissions, hard links or mounts change.
#include "expert_q4_relocation_context.h"
#include <ps5platform/kernel.h>
#include <array>
#include <cerrno>
#include <cstdio>
#include <cstring>
#include <fcntl.h>
#include <stdexcept>
#include <string>
#include <sys/stat.h>
#include <unistd.h>
extern "C" {
#include "hash/sha256/sha256.h"
int split_report_line(const char*);int split_open_journal();int split_context(unsigned);
int split_headroom();std::uint64_t split_now_ns();int split_close_journal();
}
namespace {
using Key=std::array<std::uint64_t,10>;
void need(bool ok,const char*text){if(!ok)throw std::runtime_error(text);}
void line(const std::string&text){need(text.size()<1000&&split_report_line(text.c_str()),"Relocation journal failed");}
Key key(const struct stat&s){return {std::uint64_t(s.st_dev),std::uint64_t(s.st_ino),std::uint64_t(s.st_mode),std::uint64_t(s.st_uid),std::uint64_t(s.st_gid),
    std::uint64_t(s.st_size),std::uint64_t(s.st_mtim.tv_sec),std::uint64_t(s.st_mtim.tv_nsec),std::uint64_t(s.st_ctim.tv_sec),std::uint64_t(s.st_ctim.tv_nsec)};}
Key path_key(const char*p,bool directory=false){struct stat s{};need(!lstat(p,&s)&&(directory?S_ISDIR(s.st_mode):S_ISREG(s.st_mode)),"Relocation path identity failed");return key(s);}
void emit(const std::string&label,const Key&k){auto text=label;for(auto x:k)text+=" "+std::to_string(x);line(text);}
void originals(){need(path_key(q4_original_directory,true)==q4_original_directory_identity&&
    path_key(q4_original_part_directory,true)==q4_original_part_directory_identity,"Original BF16 directories changed");}
std::string destination(const char*p,bool moved){const std::string source=q4_seal_directory;const std::string path=p;
    return moved&&path.compare(0,source.size()+1,source+"/")==0?std::string(q4_relocation_target)+path.substr(source.size()):path;}
void parts(bool moved){for(const auto&p:q4_seal_parts)need(path_key(destination(p.path,moved).c_str())==p.identity,"A fully readback-verified model part changed");}
[[noreturn]]void retain(){(void)split_report_line("UNCERTAIN CPU_owners_retained=1 automatic_retry=0");for(;;)sleep(1);}
}
int main(int argc,char**){
    if(!split_open_journal())return 2;
    bool ok=false,mapped=false,moved=false;void*window=nullptr;std::int64_t physical=-1;int fd=-1;const auto begun=split_now_ns();
    try{
        line("BEGIN nonce=" Q4_RELOCATION_NONCE " CPU_only=1 original_source_writes=0 GPU_calls=0 title_launches=0");
        need((argc==0||argc==1)&&begun&&split_context(1)&&split_context(2)&&split_headroom(),"Current owner or memory admission refused");
        originals();need(path_key(q4_seal_directory,true)==q4_seal_root_identity,"Exact closed candidate root required");parts(false);
        const auto parent=path_key(q4_relocation_parent,true);
        need(parent[0]==q4_seal_root_identity[0]&&!parent[3]&&!parent[4]&&(parent[2]&0700)==0700,"Existing same-filesystem root-owned title directory required");
        struct stat absent{};errno=0;need(lstat(q4_relocation_target,&absent)<0&&errno==ENOENT,"New title-visible destination must be absent");
        constexpr std::size_t bytes=8u<<20;
        need(!sceKernelAllocateDirectMemory(0,sceKernelGetDirectMemorySize(),bytes,16384,PS5_KERNEL_DIRECT_TYPE_CPU,&physical)&&physical>=0,"Relocation metadata Direct allocation refused");
        if(sceKernelMapDirectMemory(&window,bytes,3,0,physical,16384)||!window||reinterpret_cast<std::uintptr_t>(window)%16384)retain();mapped=true;
        need(q4_seal_receipt_bytes<bytes,"Bounded receipt required");fd=open(q4_seal_receipt,O_RDONLY|O_NOFOLLOW|O_DIRECT);
        need(fd>=0&&(fcntl(fd,F_GETFL)&O_DIRECT)&&path_key(q4_seal_receipt)==q4_relocation_receipt_identity,"Exact sealed receipt required");
        const auto requested=(q4_seal_receipt_bytes+16383)&~std::uint64_t(16383);line("BEFORE receipt_Direct_read");
        const auto got=pread(fd,window,requested,0);line("RETURN receipt_Direct_read");need(got==static_cast<ssize_t>(q4_seal_receipt_bytes),"Complete receipt read failed");
        sha256_t hash;sha256_init(&hash);sha256_update(&hash,static_cast<unsigned char*>(window),q4_seal_receipt_bytes);
        unsigned char raw[32];sha256_final(&hash,raw);char hex[65]{};for(unsigned i=0;i<32;++i){hex[2*i]="0123456789abcdef"[raw[i]>>4];hex[2*i+1]="0123456789abcdef"[raw[i]&15];}
        need(!std::strcmp(hex,q4_seal_receipt_sha256)&&path_key(q4_seal_receipt)==q4_relocation_receipt_identity,"Complete sealed receipt SHA256 or identity differs");
        const int closing=fd;fd=-1;if(close(closing))retain();originals();parts(false);
        need(path_key(q4_seal_directory,true)==q4_seal_root_identity&&path_key(q4_relocation_parent,true)==parent&&split_headroom(),"Relocation preconditions changed");
        line("BEFORE owned_Q4_directory_rename original_data_untouched=1 permission_changes=0 mount_changes=0");
        errno=0;const auto rc=rename(q4_seal_directory,q4_relocation_target);const int error=errno;
        line("RETURN owned_Q4_directory_rename rc="+std::to_string(rc)+" errno="+std::to_string(error));need(!rc,"Candidate directory relocation refused");moved=true;
        const auto root=path_key(q4_relocation_target,true);
        for(unsigned i=0;i<6;++i)need(root[i]==q4_seal_root_identity[i],"Relocation changed candidate root beyond its timestamps");
        originals();parts(true);need(path_key((std::string(q4_relocation_target)+"/model-receipt.json").c_str())==q4_relocation_receipt_identity,"Relocated receipt changed");
        emit("RELOCATED_DIRECTORY",root);emit("RELOCATED_RECEIPT",q4_relocation_receipt_identity);
        need(split_context(5)&&split_headroom()&&split_now_ns()-begun<=60000000000ULL,"Final relocation admission refused");ok=true;
    }catch(const std::exception&e){(void)split_report_line((std::string("REFUSED ")+e.what()).c_str());}
    if(fd>=0&&close(fd))retain();
    if(mapped){constexpr std::size_t bytes=8u<<20;if(sceKernelMunmap(window,bytes)||sceKernelReleaseDirectMemory(physical,bytes))retain();
        if(!split_report_line("DIRECT known_completion_cleanup_returned=1 fully_released=1"))retain();}else if(physical>=0)retain();
    char end[256];std::snprintf(end,sizeof(end),"END success=%u moved=%u active_calls=0 original_source_writes=0 GPU_calls=0 title_launches=0 retry=0",unsigned(ok),unsigned(moved));
    if(!split_report_line(end)||!split_close_journal())return 2;return ok?0:1;
}
