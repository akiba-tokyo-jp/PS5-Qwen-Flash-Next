// SPDX-License-Identifier: MIT
// Prepare or independently verify one synthetic migration fixture, never a model.
#include "split_migration.h"
#include "source_split_context.h"
#include <ps5platform/kernel.h>
#include <cerrno>
#include <cstdio>
#include <cstring>
#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>
extern "C" {
int split_report_line(const char *);
int split_open_journal(void);
int split_context(unsigned);
int split_headroom(void);
std::uint64_t split_now_ns(void);
int split_close_journal(void);
}
#ifndef SPLIT_VERIFY_FIXTURE
#define SPLIT_VERIFY_FIXTURE 0
#endif
#ifndef SPLIT_FIXTURE_PREFIX
#define SPLIT_FIXTURE_PREFIX (512ull<<20)
#endif
namespace {
void line(const std::string&s){if(!split_report_line(s.c_str()))throw std::runtime_error("Fixture journal failed");}
std::string hex(const unsigned char*d){std::string s;for(unsigned i=0;i<32;++i){s.push_back("0123456789abcdef"[d[i]>>4]);s.push_back("0123456789abcdef"[d[i]&15]);}return s;}
void key(const char*label,int fd){struct stat s{};if(fstat(fd,&s)||!S_ISREG(s.st_mode)||s.st_uid||s.st_gid||(s.st_mode&07777)!=0644)throw std::runtime_error("Fixture identity refused");
    line(std::string(label)+" "+std::to_string(s.st_dev)+" "+std::to_string(s.st_ino)+" "+std::to_string(s.st_mode)+" "+std::to_string(s.st_uid)+" "+std::to_string(s.st_gid)+" "+std::to_string(s.st_size)+" "+std::to_string(s.st_mtim.tv_sec)+" "+std::to_string(s.st_mtim.tv_nsec)+" "+std::to_string(s.st_ctim.tv_sec)+" "+std::to_string(s.st_ctim.tv_nsec));}
[[noreturn]]void retain(){(void)split_report_line("UNCERTAIN backing_retained=1 retry=0");for(;;)sleep(1);}
void guard(std::uint64_t started){const auto now=split_now_ns();if(!now||now<started||now-started>45000000000ull||!split_headroom())throw std::runtime_error("Fixture deadline or original reserves refused new work");}
}
int main(int argc,char**){
    if(!split_open_journal())return 2;
    void*buffer=nullptr;std::int64_t physical=-1;int fd=-1;bool mapped=false,ok=false;
    try{
        line("BEGIN nonce=" SPLIT_NONCE " synthetic_fixture_only=1 GPU_calls=0 title_launches=0");
        if((argc!=0&&argc!=1)||!split_context(1)||!split_context(2)||!split_headroom())throw std::runtime_error("Fixture idle admission refused");
        if(!SPLIT_VERIFY_FIXTURE){
            const int rc=mkdir(SPLIT_PART_DIRECTORY,0755);line("RETURN stage=fixture_directory_mkdir rc="+std::to_string(rc));
            struct stat directory{};
            if(rc||lstat(SPLIT_PART_DIRECTORY,&directory)||!S_ISDIR(directory.st_mode)||
               (directory.st_mode&07777)!=0755||directory.st_uid||directory.st_gid)
                throw std::runtime_error("Fresh fixture directory ownership was not admitted");
            line("DIRECTORY "+std::to_string(directory.st_dev)+" "+std::to_string(directory.st_ino));
        }
        const auto started=split_now_ns();
        int rc=sceKernelAllocateDirectMemory(0,sceKernelGetDirectMemorySize(),qwen_app::split_migration_window_bytes,16384,PS5_KERNEL_DIRECT_TYPE_CPU,&physical);
        if(rc||physical<0)throw std::runtime_error("Fixture Direct allocation failed");
        rc=sceKernelMapDirectMemory(&buffer,qwen_app::split_migration_window_bytes,3,0,physical,16384);
        if(rc||!buffer||reinterpret_cast<std::uintptr_t>(buffer)%16384)retain();mapped=true;
        constexpr std::uint64_t prefix=SPLIT_FIXTURE_PREFIX,tail=12345,total=prefix+tail;
        sha256_t complete,head,end;sha256_init(&complete);sha256_init(&head);sha256_init(&end);
        auto*bytes=static_cast<unsigned char*>(buffer);
        if(!SPLIT_VERIFY_FIXTURE){
            fd=open(SPLIT_SOURCE,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW|O_DIRECT,0600);if(fd<0)throw std::runtime_error("Fresh fixture already exists or could not be created");
            for(std::uint64_t offset=0;offset<total;){
                guard(started);const auto n=std::size_t(std::min<std::uint64_t>(qwen_app::split_migration_window_bytes,total-offset));
                for(std::size_t i=0;i<n;++i){const auto at=offset+i;bytes[i]=static_cast<unsigned char>((at*17+at/311)%251);}
                const auto requested=(n+16383)&~std::size_t(16383);
                if(requested>n)std::memset(bytes+n,0,requested-n);
                line("BEFORE stage=fixture_write offset="+std::to_string(offset)+" bytes="+std::to_string(n));
                const auto got=pwrite(fd,buffer,requested,static_cast<off_t>(offset));line("RETURN stage=fixture_write got="+std::to_string(got));
                if(got!=std::int64_t(requested))throw std::runtime_error("Fixture write did not complete exactly");
                sha256_update(&complete,bytes,n);sha256_update(offset<prefix?&head:&end,bytes,n);offset+=n;
            }
            if(ftruncate(fd,static_cast<off_t>(total))||fchmod(fd,0644)||fsync(fd))throw std::runtime_error("Fixture source durability refused");
            const int old=fd;fd=-1;if(close(old))retain();
            unsigned char a[32],b[32],c[32];sha256_final(&complete,a);sha256_final(&head,b);sha256_final(&end,c);
            line("PREPARED full_SHA256="+hex(a)+" prefix_SHA256="+hex(b)+" tail_SHA256="+hex(c));
            sha256_init(&head);
            fd=open(SPLIT_SOURCE,O_RDONLY|O_DIRECT|O_NOFOLLOW);if(fd<0)throw std::runtime_error("Fixture independent readback unavailable");
            key("SOURCE_FIXTURE",fd);
            for(std::uint64_t offset=0;offset<total;){
                guard(started);const auto n=std::size_t(std::min<std::uint64_t>(qwen_app::split_migration_window_bytes,total-offset));
                const auto requested=(n+16383)&~std::size_t(16383);
                line("BEFORE stage=fixture_readback offset="+std::to_string(offset)+" bytes="+std::to_string(requested));
                const auto got=pread(fd,buffer,requested,static_cast<off_t>(offset));line("RETURN stage=fixture_readback got="+std::to_string(got));
                if(got!=std::int64_t(n))throw std::runtime_error("Fixture full readback returned different bytes");
                sha256_update(&head,bytes,n);offset+=n;
            }
            unsigned char actual[32];sha256_final(&head,actual);for(unsigned i=0;i<32;++i)if(actual[i]!=a[i])throw std::runtime_error("Fixture full readback SHA256 differs");
        }else{
            for(unsigned part=0;part<2;++part){
                const auto nbytes=part?tail:prefix;const auto*path=part?SPLIT_PART:SPLIT_SOURCE;
                fd=open(path,O_RDONLY|O_DIRECT|O_NOFOLLOW);if(fd<0)throw std::runtime_error("Fixture reconstructed part is unavailable");
                key(part?"PART_FIXTURE":"SOURCE_FIXTURE",fd);struct stat s{};if(fstat(fd,&s)||std::uint64_t(s.st_size)!=nbytes)throw std::runtime_error("Fixture part size differs");
                for(std::uint64_t offset=0;offset<nbytes;){
                    guard(started);const auto n=std::size_t(std::min<std::uint64_t>(qwen_app::split_migration_window_bytes,nbytes-offset));
                    line("BEFORE stage=fixture_verify offset="+std::to_string(offset)+" bytes="+std::to_string(n));
                    const auto got=pread(fd,buffer,(n+16383)&~std::size_t(16383),static_cast<off_t>(offset));line("RETURN stage=fixture_verify got="+std::to_string(got));
                    if(got!=std::int64_t(n))throw std::runtime_error("Fixture reconstructed read is incomplete");
                    sha256_update(&complete,bytes,n);offset+=n;
                }
                const int old=fd;fd=-1;if(close(old))retain();
            }
            unsigned char actual[32];sha256_final(&complete,actual);
            if(hex(actual)!=SPLIT_FIXTURE_SHA256)throw std::runtime_error("Reconstructed fixture differs from its original full SHA256");
            line("RECONSTRUCTED full_SHA256="+hex(actual)+" exact_original_bytes=1");
        }
        ok=true;
    }catch(const std::exception&e){try{line(std::string("REFUSED reason=")+e.what()+" files_retained=1 retry=0");}catch(...){retain();}}
    if(fd>=0){const int old=fd;fd=-1;if(close(old))retain();}
    if(mapped){if(sceKernelMunmap(buffer,qwen_app::split_migration_window_bytes)||sceKernelReleaseDirectMemory(physical,qwen_app::split_migration_window_bytes))retain();
        if(!split_report_line("DIRECT known_completion_cleanup_returned=1 fully_released=1"))retain();}
    else if(physical>=0)retain();
    if(!split_context(5)||!split_headroom())ok=false;
    if(!split_report_line(ok?"END success=1 active_calls=0 GPU_calls=0 title_launches=0 retry=0":"END success=0 active_calls=0 GPU_calls=0 title_launches=0 retry=0"))return 2;
    if(!split_close_journal())return 2;return ok?0:1;
}
