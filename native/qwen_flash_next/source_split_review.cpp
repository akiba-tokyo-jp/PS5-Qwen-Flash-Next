// SPDX-License-Identifier: MIT
// Reconcile a positively retired CPU refusal; optionally retain one pending file
// outside the model namespace. Never truncate or read model payload bytes.
#include <array>
#include <cerrno>
#include <cstdint>
#include <cstdio>
#include <stdexcept>
#include <string>
#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>
#include "source_split_context.h"
struct SplitReviewFile {const char *path;std::uint64_t identity[10];bool pinned;};
#include "source_split_review_context.h"
#ifndef SPLIT_REVIEW_QUARANTINE
#define SPLIT_REVIEW_QUARANTINE 0
#endif
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
void line(const std::string&s){if(s.size()>1000||!split_report_line(s.c_str()))throw std::runtime_error("Review journal failed");}
Key stat_key(const struct stat&s,bool directory){
    if(!s.st_dev||!s.st_ino||s.st_size<=0||s.st_uid||s.st_gid||s.st_mode!=(directory?0040755u:0100644u))
        throw std::runtime_error("Review source ownership or mode differs");
    return{std::uint64_t(s.st_dev),std::uint64_t(s.st_ino),std::uint64_t(s.st_mode),std::uint64_t(s.st_uid),std::uint64_t(s.st_gid),
        std::uint64_t(s.st_size),std::uint64_t(s.st_mtim.tv_sec),std::uint64_t(s.st_mtim.tv_nsec),std::uint64_t(s.st_ctim.tv_sec),std::uint64_t(s.st_ctim.tv_nsec)};
}
Key named(const char*p,bool directory=false){struct stat s{};if(lstat(p,&s))throw std::runtime_error("Review pathname unavailable");return stat_key(s,directory);}
[[maybe_unused]]bool absent(const char*p){struct stat s{};errno=0;return lstat(p,&s)<0&&errno==ENOENT;}
void record(const std::string&label,const Key&key){std::string s=label;for(auto value:key)s+=" "+std::to_string(value);line(s);}
[[noreturn]]void retain(){(void)split_report_line("UNCERTAIN review_backing_retained=1 retry=0 GPU_calls=0");for(;;)sleep(1);}
Key observe(const SplitReviewFile&file){
    const int fd=open(file.path,O_RDONLY|O_NOFOLLOW|O_NONBLOCK);if(fd<0)throw std::runtime_error("Review file open failed");
    struct stat s{};const int rc=fstat(fd,&s);const int closed=close(fd);if(closed)retain();
    if(rc)throw std::runtime_error("Review descriptor query failed");
    const auto key=stat_key(s,false);if(key!=named(file.path))throw std::runtime_error("Review source changed during observation");
    if(file.pinned){for(unsigned i=0;i<10;++i)if(key[i]!=file.identity[i])throw std::runtime_error("Completed source lineage changed after refusal");}
    else if(std::string(file.path)!=SPLIT_PENDING||key[5]!=file.identity[5]||SPLIT_REVIEW_QUARANTINE)
        throw std::runtime_error("Only the exact retained pending tail may have a newly observed identity");
    return key;
}
}
int main(int argc,char**){
    if(!split_open_journal())return 2;bool ok=false;
    try{
        line("BEGIN nonce=" SPLIT_NONCE " CPU_only=1 model_payload_reads=0 GPU_calls=0 title_launches=0");
        if((argc!=0&&argc!=1)||!split_context(1)||!split_context(2)||!split_headroom())throw std::runtime_error("Review idle context refused");
        constexpr auto count=sizeof(split_review_files)/sizeof(split_review_files[0]);
        static_assert(count>1&&count<=1024,"Bounded explicit review sources are required");
        const auto started=split_now_ns();const auto root=named(SPLIT_PART_DIRECTORY,true);
        if(root[0]!=split_expected_directory[0]||root[1]!=split_expected_directory[1])throw std::runtime_error("Review root differs");
        std::array<Key,count> observed{};unsigned new_identities=0;
        record("REVIEW_DIRECTORY",root);
        for(std::size_t i=0;i<count;++i){
            if(!split_review_files[i].pinned)++new_identities;
            observed[i]=observe(split_review_files[i]);record("REVIEW_FILE_"+std::to_string(i),observed[i]);
        }
        if(new_identities!=(SPLIT_REVIEW_QUARANTINE?0u:1u))throw std::runtime_error("Unpinned review identity count differs");
        for(std::size_t i=0;i<count;++i)if(observe(split_review_files[i])!=observed[i])throw std::runtime_error("Review second snapshot changed");
        const auto now=split_now_ns();
        if(!started||now<started||now-started>45000000000ull||named(SPLIT_PART_DIRECTORY,true)!=root||!split_context(4)||!split_headroom())
            throw std::runtime_error("Review stable context or completed-boundary deadline refused");
#if SPLIT_REVIEW_QUARANTINE
        const std::string destination=SPLIT_QUARANTINE;
        const std::string prefix="/data/ai/moss-qwen-split-held-";
        if(destination.compare(0,prefix.size(),prefix)||destination.size()!=prefix.size()+32+4||destination.substr(destination.size()-4)!=".bin"||
           destination.substr(prefix.size(),32).find_first_not_of("0123456789abcdef")!=std::string::npos||!absent(destination.c_str()))
            throw std::runtime_error("Retained pending destination is not a fresh fixed owned namespace");
        const auto source_before=named(SPLIT_SOURCE),pending_before=named(SPLIT_PENDING);
        if(SPLIT_REVIEW_PENDING_INDEX>=count||std::string(split_review_files[0].path)!=SPLIT_SOURCE||
           std::string(split_review_files[SPLIT_REVIEW_PENDING_INDEX].path)!=SPLIT_PENDING||
           source_before!=observed[0]||pending_before!=observed[SPLIT_REVIEW_PENDING_INDEX])
            throw std::runtime_error("Retention source changed after its pinned observation");
        line("BEFORE stage=retain_pending_rename source_mutations=0");
        const int rc=rename(SPLIT_PENDING,SPLIT_QUARANTINE);line("RETURN stage=retain_pending_rename rc="+std::to_string(rc));
        if(rc)throw std::runtime_error("Retained pending rename did not return success; no retry");
        const auto kept=named(SPLIT_QUARANTINE);
        for(unsigned i=0;i<8;++i)if(kept[i]!=pending_before[i])throw std::runtime_error("Retained pending identity changed");
        if(!absent(SPLIT_PENDING)||named(SPLIT_SOURCE)!=source_before)throw std::runtime_error("Source changed during pending retention");
        for(const char*path:{SPLIT_PART_DIRECTORY,"/data/ai"}){
            const int fd=open(path,O_RDONLY|O_DIRECTORY|O_NOFOLLOW);if(fd<0)throw std::runtime_error("Retention parent open failed");
            const int synced=fsync(fd),closed=close(fd);if(closed)retain();
            line("RETURN stage=retain_parent_fsync rc="+std::to_string(synced)+" close_rc="+std::to_string(closed));
            if(synced)throw std::runtime_error("Retained namespace durability is not known");
        }
        for(std::size_t i=0;i<count;++i)if(i!=SPLIT_REVIEW_PENDING_INDEX&&observe(split_review_files[i])!=observed[i])
            throw std::runtime_error("A completed source changed during pending retention");
        record("RETAINED_PENDING",kept);record("REVIEW_DIRECTORY_AFTER_RETENTION",named(SPLIT_PART_DIRECTORY,true));
#endif
        if(!split_context(5)||!split_headroom())throw std::runtime_error("Final review idle context refused");
        line("FILES all_close_calls_returned=1 active_calls=0 model_payload_reads=0 source_truncations=0");ok=true;
    }catch(const std::exception&e){try{line(std::string("REFUSED reason=")+e.what()+" automatic_retries=0 files_retained=1");}catch(...){retain();}}
    if(!split_report_line(ok?"END success=1 active_calls=0 GPU_calls=0 title_launches=0 retry=0":"END success=0 active_calls=0 GPU_calls=0 title_launches=0 retry=0"))return 2;
    if(!split_close_journal())return 2;return ok?0:1;
}
