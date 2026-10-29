// SPDX-License-Identifier: MIT
// Publish and seal only three owned metadata files. Model parts stay read-only.
#include "expert_q2_seal_context.h"
#include <ps5platform/kernel.h>
#include <algorithm>
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
int split_report_line(const char*);
int split_open_journal();
int split_context(unsigned);
int split_headroom();
std::uint64_t split_now_ns();
int split_close_journal();
}
namespace {
using Key=std::array<std::uint64_t,10>;
constexpr std::size_t window_bytes=8u<<20;
void need(bool ok,const char*text){if(!ok)throw std::runtime_error(text);}
void line(const std::string&text){need(text.size()<1000&&split_report_line(text.c_str()),"Seal journal failed");}
Key key(const struct stat&s){return {std::uint64_t(s.st_dev),std::uint64_t(s.st_ino),std::uint64_t(s.st_mode),
    std::uint64_t(s.st_uid),std::uint64_t(s.st_gid),std::uint64_t(s.st_size),std::uint64_t(s.st_mtim.tv_sec),
    std::uint64_t(s.st_mtim.tv_nsec),std::uint64_t(s.st_ctim.tv_sec),std::uint64_t(s.st_ctim.tv_nsec)};}
Key path_key(const char*p,bool directory=false){struct stat s{};need(!lstat(p,&s)&&(directory?S_ISDIR(s.st_mode):S_ISREG(s.st_mode)),"Seal path identity failed");return key(s);}
Key fd_key(int fd){struct stat s{};need(!fstat(fd,&s)&&S_ISREG(s.st_mode),"Seal descriptor identity failed");return key(s);}
void emit_key(const std::string&label,const Key&value){std::string text=label;for(auto x:value)text+=" "+std::to_string(x);line(text);}
void parts_intact(){for(const auto&p:q2_seal_parts)need(path_key(p.path)==p.identity,"A fully verified model part changed before the seal");}
[[noreturn]]void retain(){(void)split_report_line("UNCERTAIN owners_retained=1 automatic_retry=0");for(;;)sleep(1);}
}
int main(int argc,char**){
    if(!split_open_journal())return 2;
    bool ok=false,mapped=false;void*window=nullptr;std::int64_t physical=-1;int fd=-1;
    const auto begun=split_now_ns();
    try{
        line("BEGIN nonce=" Q2_SEAL_NONCE " CPU_only=1 source_writes=0 GPU_calls=0 title_launches=0");
        need((argc==0||argc==1)&&begun&&split_context(1)&&split_context(2)&&split_headroom(),"Seal current owner or memory admission refused");
        const auto root=path_key(q2_seal_directory,true);
        need(root[0]==q2_seal_root_identity[0]&&root[1]==q2_seal_root_identity[1]&&root[2]==0040755&&!root[3]&&!root[4],"Exact owned candidate directory required");
        parts_intact();
        need(!sceKernelAllocateDirectMemory(0,sceKernelGetDirectMemorySize(),window_bytes,16384,PS5_KERNEL_DIRECT_TYPE_CPU,&physical)&&physical>=0,"Seal Direct allocation refused");
        if(sceKernelMapDirectMemory(&window,window_bytes,3,0,physical,16384)||!window||reinterpret_cast<std::uintptr_t>(window)%16384)retain();mapped=true;
        for(unsigned metadata_index=0;metadata_index<3;++metadata_index){
        const auto&metadata=q2_seal_metadata[metadata_index];
        struct stat absent{};errno=0;
        need(lstat(metadata.destination,&absent)&&errno==ENOENT,"A new candidate metadata destination already exists");
        fd=open(metadata.path,O_RDONLY|O_NOFOLLOW|O_DIRECT);need(fd>=0&&(fcntl(fd,F_GETFL)&O_DIRECT),"Candidate receipt Direct open failed");
        const auto before=fd_key(fd);need(before==path_key(metadata.path)&&before[5]==metadata.bytes&&!before[3]&&!before[4],"Exact newly published candidate receipt required");
        sha256_t hash;sha256_init(&hash);
        for(std::uint64_t at=0;at<metadata.bytes;){
            need(split_headroom()&&split_now_ns()-begun<=60000000000ULL,"Seal deadline or memory admission refused");
            const auto n=std::size_t(std::min<std::uint64_t>(window_bytes,metadata.bytes-at));
            const auto requested=(n+16383)&~std::size_t(16383);line("BEFORE receipt_Direct_read");
            const auto got=pread(fd,window,requested,static_cast<off_t>(at));line("RETURN receipt_Direct_read");
            need(got==static_cast<ssize_t>(n),"Candidate receipt read failed");sha256_update(&hash,static_cast<unsigned char*>(window),n);at+=n;
        }
        line("BEFORE receipt_Direct_EOF");
        const auto tail=pread(fd,window,16384,static_cast<off_t>((metadata.bytes+16383)&~std::uint64_t(16383)));
        line("RETURN receipt_Direct_EOF");need(tail==0,"Candidate receipt EOF differs");
        unsigned char digest[32];sha256_final(&hash,digest);char text[65]{};
        for(unsigned i=0;i<32;++i){text[2*i]="0123456789abcdef"[digest[i]>>4];text[2*i+1]="0123456789abcdef"[digest[i]&15];}
        need(!std::strcmp(text,metadata.sha256)&&fd_key(fd)==before&&path_key(metadata.path)==before,"Complete candidate receipt SHA256 or stable identity failed");
        line("RECEIPT complete_SHA256_verified=1 before_permission_tightening=1");
        // This is the new isolated receipt, never a shared production directory.
        need(!fchmod(fd,0644),"New candidate receipt permission finalization failed");
        const auto after=fd_key(fd);need(after==path_key(metadata.path)&&after[2]==0100644&&!after[3]&&!after[4]&&after[0]==before[0]&&after[1]==before[1]&&after[5]==before[5],"Final candidate receipt identity differs");
        const int closing=fd;fd=-1;if(close(closing))retain();
        errno=0;need(lstat(metadata.destination,&absent)&&errno==ENOENT,"Candidate metadata publication cannot overwrite an existing path");
        line("BEFORE own_candidate_metadata_rename index="+std::to_string(metadata_index));
        const int published=rename(metadata.path,metadata.destination);
        line("RETURN own_candidate_metadata_rename index="+std::to_string(metadata_index)+" rc="+std::to_string(published));
        need(!published,"Own candidate metadata publication failed");
        const auto sealed=path_key(metadata.destination);
        need(sealed[0]==after[0]&&sealed[1]==after[1]&&sealed[2]==after[2]&&sealed[3]==after[3]&&sealed[4]==after[4]&&sealed[5]==after[5]&&
            sealed[6]==after[6]&&sealed[7]==after[7],"Published candidate metadata inode, mode or payload changed");
        emit_key("SEALED_METADATA index="+std::to_string(metadata_index),sealed);
        if(!metadata_index)emit_key("SEALED_RECEIPT",sealed);
        }
        parts_intact();const auto final_root=path_key(q2_seal_directory,true);
        need(std::equal(root.begin(),root.begin()+5,final_root.begin()),"Candidate directory owner or inode changed during own metadata publication");
        for(unsigned i=0;i<sizeof(q2_seal_parts)/sizeof(q2_seal_parts[0]);++i)emit_key("SEALED_PART index="+std::to_string(i),q2_seal_parts[i].identity);
        emit_key("SEALED_DIRECTORY",final_root);
        need(split_context(5)&&split_headroom(),"Seal final current owner or memory admission refused");ok=true;
    }catch(const std::exception&e){(void)split_report_line((std::string("REFUSED ")+e.what()).c_str());}
    if(fd>=0&&close(fd))retain();
    if(mapped){if(sceKernelMunmap(window,window_bytes)||sceKernelReleaseDirectMemory(physical,window_bytes))retain();
        if(!split_report_line("DIRECT known_completion_cleanup_returned=1 fully_released=1"))retain();}
    else if(physical>=0)retain();
    char end[256];std::snprintf(end,sizeof(end),"END success=%u elapsed_ns=%llu active_calls=0 source_writes=0 GPU_calls=0 title_launches=0 retry=0",unsigned(ok),static_cast<unsigned long long>(split_now_ns()-begun));
    if(!split_report_line(end)||!split_close_journal())return 2;return ok?0:1;
}
