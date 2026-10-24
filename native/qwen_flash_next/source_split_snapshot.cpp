// SPDX-License-Identifier: MIT
// Read-only sealing of already hashed physical parts. No model payload or GPU.
#include <array>
#include <cerrno>
#include <cstdio>
#include <cstdint>
#include "source_split_context.h"
#include <cstring>
#include <stdexcept>
#include <string>
#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>
struct SplitSnapshotFile {const char *path;std::uint64_t identity[10];};
#include "source_split_snapshot_context.h"
extern "C" {
int split_report_line(const char *);
int split_open_journal(void);
int split_context(unsigned);
int split_headroom(void);
std::uint64_t split_now_ns(void);
int split_close_journal(void);
}
namespace {
using Key=std::array<std::uint64_t,10>;
void line(const std::string &text){if(text.size()>1000||!split_report_line(text.c_str()))throw std::runtime_error("Durable snapshot journal failed");}
Key key(const struct stat&s,bool directory){
    if(!s.st_dev||!s.st_ino||s.st_size<=0||s.st_uid||s.st_gid||
       s.st_mode!=(directory?0040755u:0100644u))throw std::runtime_error("Snapshot ownership or sealed mode differs");
    return{std::uint64_t(s.st_dev),std::uint64_t(s.st_ino),std::uint64_t(s.st_mode),std::uint64_t(s.st_uid),std::uint64_t(s.st_gid),
        std::uint64_t(s.st_size),std::uint64_t(s.st_mtim.tv_sec),std::uint64_t(s.st_mtim.tv_nsec),
        std::uint64_t(s.st_ctim.tv_sec),std::uint64_t(s.st_ctim.tv_nsec)};
}
Key named(const char*path,bool directory){struct stat s{};if(lstat(path,&s))throw std::runtime_error("Snapshot pathname is unavailable");return key(s,directory);}
[[noreturn]]void retain(){(void)split_report_line("UNCERTAIN snapshot_descriptor_retained=1 retry=0 GPU_calls=0");for(;;)sleep(1);}
Key observed(const SplitSnapshotFile&file){
    const int fd=open(file.path,O_RDONLY|O_NOFOLLOW|O_NONBLOCK);
    if(fd<0)throw std::runtime_error("A pinned physical source is missing");
    struct stat s{};const int rc=fstat(fd,&s);
    const int closed=close(fd);if(closed)retain();
    if(rc)throw std::runtime_error("Snapshot descriptor identity query failed");
    const auto current=key(s,false);
    if(current!=named(file.path,false))throw std::runtime_error("Snapshot source pathname changed");
    for(unsigned i=0;i<10;++i)if(current[i]!=file.identity[i])throw std::runtime_error("A source changed after complete native hashing");
    struct stat pending{};errno=0;
    if(lstat((std::string(file.path)+".pending").c_str(),&pending)==0||errno!=ENOENT)
        throw std::runtime_error("A pending operation remains in the sealed source layout");
    return current;
}
void record(const std::string &label,const Key&value){std::string text=label;for(auto x:value)text+=" "+std::to_string(x);line(text);}
}
int main(int argc,char**){
    if(!split_open_journal())return 2;
    bool ok=false;
    try{
        line("BEGIN nonce=" SPLIT_NONCE " CPU_only=1 model_payload_reads=0 GPU_calls=0 title_launches=0");
        if((argc!=0&&argc!=1)||!split_context(1)||!split_context(2)||!split_headroom())throw std::runtime_error("Fresh idle snapshot context refused");
        constexpr auto count=sizeof(split_snapshot_files)/sizeof(split_snapshot_files[0]);
        static_assert(count==712,"The complete 711-part model and original receipt are required");
        const auto started=split_now_ns();const auto root=named(SPLIT_PART_DIRECTORY,true);
        if(root[0]!=split_expected_directory[0]||root[1]!=split_expected_directory[1])throw std::runtime_error("Snapshot root escaped its original owned identity");
        record("SEALED_DIRECTORY",root);
        for(unsigned pass=0;pass<2;++pass)for(std::size_t i=0;i<count;++i){
            const auto now=split_now_ns();
            if(!started||now<started||now-started>45000000000ull||
               (i%16==0&&(!split_context(3)||!split_headroom())))throw std::runtime_error("Snapshot completed-boundary context or deadline refused");
            const auto current=observed(split_snapshot_files[i]);
            if(!pass)record("SEALED_FILE_"+std::to_string(i),current);
        }
        if(named(SPLIT_PART_DIRECTORY,true)!=root||!split_context(5)||!split_headroom())throw std::runtime_error("Snapshot directory or final idle ownership changed");
        line("FILES all_close_calls_returned=1 active_calls=0 model_payload_reads=0 mappings=0");ok=true;
    }catch(const std::exception&e){
        try{line(std::string("REFUSED reason=")+e.what()+" automatic_retries=0");}catch(...){retain();}
    }
    if(!split_report_line(ok?"END success=1 active_calls=0 GPU_calls=0 title_launches=0 retry=0":"END success=0 active_calls=0 GPU_calls=0 title_launches=0 retry=0"))return 2;
    if(!split_close_journal())return 2;
    return ok?0:1;
}
