// SPDX-License-Identifier: MIT
// CPU-only original-to-Q4 copy into a new directory. Original sources are
// opened read-only; every output part receives a complete Direct readback.
#include "expert_q4_local_plan.h"
#include <ps5platform/kernel.h>
#include <algorithm>
#include <array>
#include <cerrno>
#include <cstdio>
#include <cstring>
#include <cpuid.h>
#include <fcntl.h>
#include <stdexcept>
#include <string>
#include <sys/mount.h>
#include <sys/stat.h>
#include <unistd.h>
#ifndef Q4_LOCAL_RESUME
#define Q4_LOCAL_RESUME 0
#endif
extern "C" {
#include "hash/sha256/sha256.h"
int split_report_line(const char*);
int split_open_journal(void);
int split_context(unsigned);
int split_headroom(void);
std::uint64_t split_now_ns(void);
int split_close_journal(void);
int qwen_quantize_bf16_q4_0(const std::uint16_t*,std::uint8_t*,std::size_t);
#if defined(Q4_LOCAL_ACCELERATED_HASH)
unsigned qwen_sha256_acceleration_available();
#endif
}
namespace {
using Key=std::array<std::uint64_t,10>;
constexpr std::size_t io_bytes=8u<<20,owned_bytes=32u<<20;
constexpr std::uint64_t part_bytes=512ull<<20;
std::uint64_t started=0,completed_files=0,encoded_matrices=0;
unsigned char *input=nullptr,*matrix=nullptr,*encoded=nullptr,*output=nullptr,*readback=nullptr;
void need(bool ok,const char*message){if(!ok)throw std::runtime_error(message);}
void line(const std::string&text){need(text.size()<1000&&split_report_line(text.c_str()),"Durable CPU conversion journal failed");}
[[noreturn]] void retain(){(void)split_report_line("UNCERTAIN CPU_owners_retained=1 automatic_retry=0");for(;;)sleep(1);}
Key key(const struct stat&s) {
    return {std::uint64_t(s.st_dev),std::uint64_t(s.st_ino),std::uint64_t(s.st_mode),std::uint64_t(s.st_uid),std::uint64_t(s.st_gid),
        std::uint64_t(s.st_size),std::uint64_t(s.st_mtim.tv_sec),std::uint64_t(s.st_mtim.tv_nsec),std::uint64_t(s.st_ctim.tv_sec),std::uint64_t(s.st_ctim.tv_nsec)};
}
Key fd_key(int fd){struct stat s{};need(!fstat(fd,&s)&&S_ISREG(s.st_mode)&&s.st_size>0,"Regular conversion descriptor required");return key(s);}
Key path_key(const char*path,bool directory=false){struct stat s{};need(!lstat(path,&s)&&(directory?S_ISDIR(s.st_mode):S_ISREG(s.st_mode)),"Conversion path identity failed");return key(s);}
std::string hex(sha256_t*h){unsigned char d[32];sha256_final(h,d);std::string text;for(auto v:d){text+="0123456789abcdef"[v>>4];text+="0123456789abcdef"[v&15];}return text;}
void record_key(const std::string&label,const Key&value){std::string text=label;for(auto v:value)text+=" "+std::to_string(v);line(text);}
void boundary(){const auto now=split_now_ns();need(now>=started&&now-started<=UINT64_C(7200000000000)&&split_headroom(),"CPU conversion deadline or memory admission refused");}
void close_fd(int&fd){if(fd>=0){const int old=fd;fd=-1;if(close(old))retain();}}
void roots(){
    need(path_key(q4_original_root,true)==q4_original_root_identity&&path_key(q4_original_parts_root,true)==q4_original_parts_identity,
        "Sealed original directories changed; no new conversion work");
}
#if Q4_LOCAL_RESUME
void completed_prefix_intact(bool initial){
    if(initial)need(path_key(q4_destination,true)==q4_resume_root_identity,"Owned Q4 continuation directory changed");
    for(const auto&part:q4_completed_parts)need(path_key(part.path)==part.identity,"A completed Q4 part changed before continuation");
}
#endif
void capacity(std::uint64_t needed){
    struct statfs s{};need(!statfs(q4_destination_parent,&s)&&s.f_bsize>0&&s.f_bavail>0,
        "Fresh destination storage observation required");
    const auto available=std::uint64_t(s.f_bavail)*std::uint64_t(s.f_bsize);
    need(needed<=UINT64_MAX-(1ull<<30)&&available>=needed+(1ull<<30),"Candidate output cannot retain one GiB of disk headroom");
}
struct Source {
    const Q4LocalFile&file;int fd=-1;unsigned part=UINT32_MAX;std::uint64_t cursor=0,cache_start=0;
    std::size_t cached=0;sha256_t hash;sha256_t*tensor_hash=nullptr;
    explicit Source(const Q4LocalFile&f):file(f){sha256_init(&hash);}
    void load(){
        boundary();const auto wanted=unsigned(cursor/part_bytes);
        need(wanted<file.part_count,"Original logical source exceeded its physical parts");
        if(part!=wanted){close_fd(fd);part=wanted;const auto&p=q4_original_parts[file.first_part+part];
            fd=open(p.path,O_RDONLY|O_NOFOLLOW|O_DIRECT);need(fd>=0&&(fcntl(fd,F_GETFL)&O_DIRECT)&&fd_key(fd)==p.identity&&path_key(p.path)==p.identity,"Original part identity or Direct descriptor differs");}
        const auto&p=q4_original_parts[file.first_part+part];const auto offset=cursor%part_bytes;
        need(offset%16384==0&&offset<p.identity[5],"Original source read lost its aligned sequential boundary");
        const auto logical=std::size_t(std::min<std::uint64_t>(io_bytes,p.identity[5]-offset));
        const auto requested=(logical+16383)&~std::size_t(16383);
        line("BEFORE source_read file="+std::to_string(file.index)+" offset="+std::to_string(cursor)+" bytes="+std::to_string(requested));
        const auto got=pread(fd,input,requested,static_cast<off_t>(offset));line("RETURN source_read bytes="+std::to_string(got));
        need(got==static_cast<ssize_t>(logical)&&fd_key(fd)==p.identity&&path_key(p.path)==p.identity,"Original part read or stable identity failed");
        cache_start=cursor;cached=logical;
    }
    template<class Consumer>void consume(std::uint64_t count,Consumer consumer){
        need(count<=file.original_bytes-cursor,"Original logical source range differs");
        while(count){if(!cached||cursor>=cache_start+cached)load();
            const auto n=std::size_t(std::min<std::uint64_t>(count,cache_start+cached-cursor));const auto*at=input+(cursor-cache_start);
            sha256_update(&hash,at,n);if(tensor_hash)sha256_update(tensor_hash,at,n);consumer(at,n);cursor+=n;count-=n;}
    }
    void skip(std::uint64_t count){consume(count,[](const unsigned char*,std::size_t){});}
    void copy(void*target,std::size_t count){auto*out=static_cast<unsigned char*>(target);consume(count,[&](const unsigned char*at,std::size_t n){std::memcpy(out,at,n);out+=n;});}
    void finish(){skip(file.original_bytes-cursor);need(hex(&hash)==file.original_sha256,"Complete original logical SHA256 differs");close_fd(fd);}
};
struct Writer {
    const Q4LocalFile&file;int fd=-1;unsigned part=0;std::uint64_t cursor=0,part_written=0;std::size_t buffered=0;
    std::string target,pending;sha256_t whole,part_hash;sha256_t*tensor_hash=nullptr;
    explicit Writer(const Q4LocalFile&f):file(f){sha256_init(&whole);}
    void open_part(){
        capacity(std::min<std::uint64_t>(part_bytes,file.output_bytes-cursor));
        target=std::string(q4_destination)+"/"+file.name+(part?".part-"+std::to_string(part):"");pending=target+".pending";
        struct stat s{};errno=0;need(lstat(target.c_str(),&s)<0&&errno==ENOENT,"Candidate final path already exists");
        fd=open(pending.c_str(),O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW|O_DIRECT,0600);
        need(fd>=0&&(fcntl(fd,F_GETFL)&O_DIRECT),"New exclusive candidate Direct output required");part_written=0;sha256_init(&part_hash);
    }
    void flush(bool final){
        if(!buffered)return;if(fd<0)open_part();boundary();
        const auto physical=(buffered+16383)&~std::size_t(16383);
        need(final||physical==buffered,"Only final part may have padded Direct write");
        std::memset(output+buffered,0,physical-buffered);
        line("BEFORE output_write file="+std::to_string(file.index)+" part="+std::to_string(part)+" bytes="+std::to_string(physical));
        const auto got=pwrite(fd,output,physical,static_cast<off_t>(part_written));line("RETURN output_write bytes="+std::to_string(got));
        need(got==static_cast<ssize_t>(physical),"Candidate Direct output write was short");
        sha256_update(&part_hash,output,buffered);part_written+=buffered;buffered=0;
    }
    void finish_part(){
        flush(true);need(fd>=0&&part_written&&part_written<=part_bytes,"Candidate part byte accounting differs");
        need(!ftruncate(fd,static_cast<off_t>(part_written))&&!fsync(fd),"Candidate part truncate/fsync did not return successfully");close_fd(fd);
        fd=open(pending.c_str(),O_RDONLY|O_NOFOLLOW|O_DIRECT);need(fd>=0&&(fcntl(fd,F_GETFL)&O_DIRECT),"Candidate readback Direct descriptor required");
        const auto before=fd_key(fd);need(before[5]==part_written,"Candidate part size differs before readback");
        sha256_t verify;sha256_init(&verify);
        for(std::uint64_t offset=0;offset<part_written;){boundary();const auto n=std::size_t(std::min<std::uint64_t>(io_bytes,part_written-offset));
            line("BEFORE output_readback file="+std::to_string(file.index)+" part="+std::to_string(part)+" offset="+std::to_string(offset));
            const auto got=pread(fd,readback,(n+16383)&~std::size_t(16383),static_cast<off_t>(offset));line("RETURN output_readback bytes="+std::to_string(got));
            need(got==static_cast<ssize_t>(n),"Candidate full readback was short");sha256_update(&verify,readback,n);offset+=n;}
        const auto expected=hex(&part_hash);need(hex(&verify)==expected&&fd_key(fd)==before&&path_key(pending.c_str())==before,"Candidate complete part SHA256/identity failed");
        need(!fchmod(fd,0644)&&!fsync(fd),"Candidate readonly publication permissions failed");close_fd(fd);
        need(!rename(pending.c_str(),target.c_str()),"Candidate verified part rename failed");
        const auto published=path_key(target.c_str());need(published[5]==part_written&&(published[2]&07777)==0644&&!published[3]&&!published[4],"Candidate published part identity differs");
        line("Q4_PART file="+std::to_string(file.index)+" part="+std::to_string(part)+" bytes="+std::to_string(part_written)+" SHA256="+expected);
        record_key("Q4_PART_ID file="+std::to_string(file.index)+" part="+std::to_string(part),published);++part;part_written=0;
    }
    void put(const unsigned char*data,std::size_t bytes){
        need(bytes<=file.output_bytes-cursor,"Candidate tensor exceeds the planned output");sha256_update(&whole,data,bytes);if(tensor_hash)sha256_update(tensor_hash,data,bytes);
        while(bytes){const auto n=std::min(bytes,io_bytes-buffered);std::memcpy(output+buffered,data,n);buffered+=n;cursor+=n;data+=n;bytes-=n;
            if(buffered==io_bytes){flush(false);if(part_written==part_bytes)finish_part();}}
    }
    void zeros(std::uint64_t bytes){static const std::array<unsigned char,16384>zero{};while(bytes){const auto n=std::size_t(std::min<std::uint64_t>(bytes,zero.size()));put(zero.data(),n);bytes-=n;}}
    std::string finish(){need(cursor==file.output_bytes,"Candidate complete GGUF byte count differs");if(buffered||fd>=0)finish_part();
        const auto digest=hex(&whole);need(!*file.known_output_sha256||digest==file.known_output_sha256,"Candidate differs from independently host-converted whole GGUF");return digest;}
};
int header_fd=-1;Key header_identity{};
void header_into(const Q4LocalFile&file,Writer&writer){
    for(std::uint64_t offset=0;offset<file.header_bytes;){boundary();const auto count=std::size_t(std::min<std::uint64_t>(io_bytes,file.header_bytes-offset));
        const auto got=pread(header_fd,readback,(count+16383)&~std::size_t(16383),static_cast<off_t>(file.header_offset+offset));
        need(got==static_cast<ssize_t>((count+16383)&~std::size_t(16383))&&fd_key(header_fd)==header_identity,"Pinned new GGUF header read failed");
        writer.put(readback,count);offset+=count;}
}
}
int main(int argc,char**) {
    if(!split_open_journal())return 2;
    void*owned=nullptr;std::int64_t physical=-1;bool mapped=false,ok=false;Source*source=nullptr;Writer*writer=nullptr;
    started=split_now_ns();
    try {
        line("BEGIN nonce=" Q4_LOCAL_NONCE " CPU_only=1 source_writes=0 GPU_calls=0 title_launches=0 window_bytes=33554432");
        need((argc==0||argc==1)&&started&&split_context(1)&&split_context(2),"Fresh idle conversion context required");boundary();roots();
#if Q4_LOCAL_RESUME
        need(q4_prior_new_bytes<=q4_total_new_bytes,"Completed Q4 prefix exceeds its complete source plan");
        capacity(q4_total_new_bytes-q4_prior_new_bytes);completed_prefix_intact(true);
        completed_files=q4_prior_files;encoded_matrices=q4_prior_matrices;
#else
        capacity(q4_total_new_bytes);
#endif
#if defined(Q4_LOCAL_ACCELERATED_HASH)
        need(qwen_sha256_acceleration_available()==1,"The qualified hardware SHA path is unavailable");
        line("CPU SHA_extension_used=1 complete_native_part_readback_unchanged=1");
#endif
        unsigned a,b,c,d;need(__get_cpuid(1,&a,&b,&c,&d)&&(c&bit_F16C),"Qualified PS5 CPU encoder F16C capability required");
        need(!sceKernelAllocateDirectMemory(0,sceKernelGetDirectMemorySize(),owned_bytes,16384,PS5_KERNEL_DIRECT_TYPE_CPU,&physical)&&physical>=0,"Bounded CPU conversion Direct allocation failed");
        if(sceKernelMapDirectMemory(&owned,owned_bytes,3,0,physical,16384)||!owned||reinterpret_cast<std::uintptr_t>(owned)%16384)retain();mapped=true;
        input=static_cast<unsigned char*>(owned);matrix=input+(8u<<20);encoded=input+(12u<<20);output=input+(16u<<20);readback=input+(24u<<20);
        header_fd=open(q4_header_pack,O_RDONLY|O_NOFOLLOW|O_DIRECT);need(header_fd>=0&&(fcntl(header_fd,F_GETFL)&O_DIRECT),"Pinned new GGUF header pack unavailable");
        header_identity=fd_key(header_fd);need(header_identity[5]==q4_header_pack_bytes,"Pinned header pack size differs");
        sha256_t hash;sha256_init(&hash);
        for(std::uint64_t at=0;at<q4_header_pack_bytes;){boundary();const auto n=std::size_t(std::min<std::uint64_t>(io_bytes,q4_header_pack_bytes-at));
            need(pread(header_fd,readback,n,static_cast<off_t>(at))==static_cast<ssize_t>(n),"Header pack complete Direct read failed");sha256_update(&hash,readback,n);at+=n;}
        need(hex(&hash)==q4_header_pack_sha256&&fd_key(header_fd)==header_identity,"New GGUF header pack SHA256/identity differs");
#if !Q4_LOCAL_RESUME
        errno=0;const int created=mkdir(q4_destination,0755);const int create_error=errno;
        line("RETURN create_candidate_directory rc="+std::to_string(created)+" errno="+std::to_string(create_error));
        need(!created,"Fresh task data directory creation failed; existing paths remain untouched");
#endif
        for(unsigned ordinal=static_cast<unsigned>(completed_files);ordinal<sizeof(q4_local_files)/sizeof(q4_local_files[0]);++ordinal){
            const auto&file=q4_local_files[ordinal];
            boundary();roots();need(split_context(3),"CPU conversion idle owner context changed");
#if defined(Q4_LOCAL_STOP_PATH)
            struct stat stop{};errno=0;const int stopped=lstat(Q4_LOCAL_STOP_PATH,&stop);
            if(!stopped){line("REQUESTED_STOP complete_file_boundary=1 completed_files="+std::to_string(completed_files));
                throw std::runtime_error("Owned CPU conversion stop requested at a complete-file boundary");}
            need(errno==ENOENT,"Owned CPU stop metadata could not be observed");
#endif
            source=new Source(file);writer=new Writer(file);header_into(file,*writer);
            for(unsigned i=0;i<file.tensor_count;++i){const auto&t=q4_local_tensors[file.first_tensor+i];
                need(source->cursor<=t.source_offset&&writer->cursor<=t.output_offset,"Planned original/candidate tensor order differs");
                source->skip(t.source_offset-source->cursor);writer->zeros(t.output_offset-writer->cursor);
                sha256_t original_tensor,converted_tensor;sha256_init(&original_tensor);sha256_init(&converted_tensor);
                source->tensor_hash=&original_tensor;writer->tensor_hash=&converted_tensor;
                if(t.quantize){need(t.source_bytes==UINT64_C(1677721600)&&t.output_bytes==UINT64_C(471859200),"All 512 original Expert matrices required");
                    for(unsigned expert=0;expert<512;++expert){source->copy(matrix,3276800);boundary();
                        need(!qwen_quantize_bf16_q4_0(reinterpret_cast<const std::uint16_t*>(matrix),encoded,1638400),"Qualified CPU Q4 block conversion failed");
                        writer->put(encoded,921600);++encoded_matrices;}
                }else source->consume(t.source_bytes,[&](const unsigned char*at,std::size_t n){writer->put(at,n);});
                source->tensor_hash=nullptr;writer->tensor_hash=nullptr;
                const auto original_digest=hex(&original_tensor),converted_digest=hex(&converted_tensor);
                need(t.quantize||original_digest==converted_digest,"Non-Expert tensor bytes changed");
                line("Q4_TENSOR file="+std::to_string(file.index)+" tensor="+std::to_string(i)+" original_SHA256="+original_digest+" output_SHA256="+converted_digest);
                need(writer->cursor==t.output_offset+t.output_bytes,"Candidate tensor exact byte count differs");writer->zeros((-writer->cursor)&31);
            }
            source->finish();delete source;source=nullptr;
            need(writer->cursor<=file.output_bytes,"Candidate final GGUF bounds differ");writer->zeros(file.output_bytes-writer->cursor);
            const auto digest=writer->finish();delete writer;writer=nullptr;++completed_files;roots();
            line("Q4_FILE file="+std::to_string(file.index)+" bytes="+std::to_string(file.output_bytes)+" SHA256="+digest+" original_full_SHA256_matched=1");
        }
        need(completed_files==74&&encoded_matrices==75264,"Complete original 147-tensor Expert conversion required");
#if Q4_LOCAL_RESUME
        completed_prefix_intact(false);
#endif
        close_fd(header_fd);record_key("Q4_DIRECTORY",path_key(q4_destination,true));ok=true;
    }catch(const std::exception&e){try{line(std::string("REFUSED reason=")+e.what()+" partial_candidate_retained=1 original_sources_unchanged=1");}catch(...){retain();}}
    if(source)close_fd(source->fd);if(writer)close_fd(writer->fd);close_fd(header_fd);
    if(mapped){if(sceKernelMunmap(owned,owned_bytes)||sceKernelReleaseDirectMemory(physical,owned_bytes))retain();
        if(!split_report_line("DIRECT known_completion_cleanup_returned=1 fully_released=1"))retain();}else if(physical>=0)retain();
    if(!split_context(5)||!split_headroom())ok=false;
    try{line("END success="+std::to_string(ok)+" files="+std::to_string(completed_files)+" matrices="+std::to_string(encoded_matrices)+" active_calls=0 source_writes=0 GPU_calls=0 title_launches=0 retry=0");}catch(...){retain();}
    if(!split_close_journal())return 2;return ok?0:1;
}
