// SPDX-License-Identifier: MIT
// One fixed CPU-only copy/verify/publish/truncate transaction. No GPU or mmap.
#include "split_migration.h"
#include "source_split_context.h"
#include <ps5platform/kernel.h>
#include <array>
#include <cerrno>
#include <cstdio>
#include <cstring>
#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>
#ifndef SPLIT_BATCH_MODEL
#define SPLIT_BATCH_MODEL 0
#endif
#ifndef SPLIT_PART_PREFIX
#define SPLIT_PART_PREFIX SPLIT_PART
#endif
#ifndef SPLIT_ORIGINAL_SHA256
#define SPLIT_ORIGINAL_SHA256 ""
#endif
#ifndef SPLIT_ORIGINAL_BYTES
#define SPLIT_ORIGINAL_BYTES split_expected_source[5]
#endif
#ifndef SPLIT_VERIFY_ONLY
#define SPLIT_VERIFY_ONLY 0
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
void line(const std::string &value){if(value.size()>1000||!split_report_line(value.c_str()))throw std::runtime_error("Durable migration journal failed");}
Key stat_key(const struct stat&s){
    if(!S_ISREG(s.st_mode)||!s.st_ino||s.st_size<=0||(s.st_mode&0022)||s.st_uid||s.st_gid)
        throw std::runtime_error("Migration file is not an exact root-owned sealed source");
    return{std::uint64_t(s.st_dev),std::uint64_t(s.st_ino),std::uint64_t(s.st_mode),std::uint64_t(s.st_uid),std::uint64_t(s.st_gid),
        std::uint64_t(s.st_size),std::uint64_t(s.st_mtim.tv_sec),std::uint64_t(s.st_mtim.tv_nsec),
        std::uint64_t(s.st_ctim.tv_sec),std::uint64_t(s.st_ctim.tv_nsec)};
}
Key fd_key(int fd){struct stat s{};if(fstat(fd,&s))throw std::runtime_error("Migration descriptor identity query failed");return stat_key(s);}
Key path_key(const char*p){struct stat s{};if(lstat(p,&s))throw std::runtime_error("Migration pathname identity query failed");return stat_key(s);}
void record_key(const char*label,const Key&key){std::string text=label;for(auto value:key)text+=" "+std::to_string(value);line(text);}
bool absent(const char*p){struct stat s{};errno=0;return lstat(p,&s)<0&&errno==ENOENT;}
Key initial_source_key(){Key key{};for(unsigned i=0;i<10;++i)key[i]=split_expected_source[i];return key;}
class NativeMigration final:public qwen_app::SplitMigrationOps {
public:
    int source=-1,write_fd=-1,read_fd=-1;
    bool published=false,uncertain=false;
    Key original{},pending{},result{};
    std::uint64_t started=0,pending_bytes=0;
    std::string part_path,pending_path;
    NativeMigration(Key expected=initial_source_key(),std::string part=SPLIT_PART):original(expected),part_path(std::move(part)),pending_path(part_path+".pending"){
        const auto root=std::string(SPLIT_PART_DIRECTORY)+"/";
        if(part_path.size()>1024||part_path.compare(0,root.size(),root)||part_path.size()==root.size()||
           part_path.substr(root.size()).find_first_not_of("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._-")!=std::string::npos)
            throw std::runtime_error("Migration part escaped its fixed owned directory");
        source=open(SPLIT_SOURCE,O_RDWR|O_NOFOLLOW|O_DIRECT);
        if(source<0||fd_key(source)!=original||path_key(SPLIT_SOURCE)!=original)
            throw std::runtime_error("Current source differs from its completed lineage");
        struct stat dir{};
        if(lstat(SPLIT_PART_DIRECTORY,&dir)||!S_ISDIR(dir.st_mode)||(dir.st_mode&07777)!=0755||dir.st_uid||dir.st_gid||
           std::uint64_t(dir.st_dev)!=split_expected_directory[0]||std::uint64_t(dir.st_ino)!=split_expected_directory[1])
            throw std::runtime_error("Migration destination directory is outside its owned identity");
        started=split_now_ns();if(!started)throw std::runtime_error("Migration clock was not admitted");
        record_key("SOURCE_BEFORE",original);
    }
    bool source_unchanged()override{return fd_key(source)==original&&path_key(SPLIT_SOURCE)==original;}
    void guard(const char*stage,std::uint64_t offset,std::size_t bytes)override{
        const auto now=split_now_ns();
        if(!now||now<started||now-started>UINT64_C(45000000000)||!split_headroom())
            throw std::runtime_error("Migration completed-boundary deadline or unchanged reserves refused new work");
        line(std::string("BEFORE stage=")+stage+" offset="+std::to_string(offset)+" bytes="+std::to_string(bytes));
    }
    std::int64_t read_source(void*target,std::size_t bytes,std::uint64_t offset)override{
        const auto got=pread(source,target,bytes,static_cast<off_t>(offset));
        line("RETURN stage=read_source got="+std::to_string(got));return got;
    }
    bool create_pending(std::uint64_t bytes)override{
        if(!absent(part_path.c_str())||!absent(pending_path.c_str()))return false;
        pending_bytes=bytes;
        write_fd=open(pending_path.c_str(),O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW|O_DIRECT,0600);
        line("RETURN stage=create_pending rc="+std::to_string(write_fd>=0?0:-1)+" bytes="+std::to_string(bytes));return write_fd>=0;
    }
    std::int64_t write_pending(void*target,std::size_t bytes,std::uint64_t offset)override{
        const auto requested=(bytes+16383)&~std::size_t(16383);
        if(!bytes||requested>qwen_app::split_migration_window_bytes||offset%16384)return -1;
        if(requested>bytes)std::memset(static_cast<unsigned char*>(target)+bytes,0,requested-bytes);
        const auto got=pwrite(write_fd,target,requested,static_cast<off_t>(offset));
        line("RETURN stage=write_pending got="+std::to_string(got)+" logical_bytes="+std::to_string(bytes));
        return got==std::int64_t(requested)?std::int64_t(bytes):-1;
    }
    bool flush_and_open_readback()override{
        int rc=ftruncate(write_fd,static_cast<off_t>(pending_bytes));
        line("RETURN stage=pending_exact_length rc="+std::to_string(rc));if(rc){uncertain=true;return false;}
        rc=fchmod(write_fd,0644);line("RETURN stage=pending_mode rc="+std::to_string(rc));if(rc)return false;
        rc=fsync(write_fd);line("RETURN stage=pending_fsync rc="+std::to_string(rc));if(rc)return false;
        pending=fd_key(write_fd);const int fd=write_fd;write_fd=-1;
        rc=close(fd);line("RETURN stage=pending_close rc="+std::to_string(rc));if(rc){uncertain=true;return false;}
        read_fd=open(pending_path.c_str(),O_RDONLY|O_NOFOLLOW|O_DIRECT);
        if(read_fd<0||fd_key(read_fd)!=pending||path_key(pending_path.c_str())!=pending)return false;
        line("RETURN stage=pending_readback_open rc=0");return true;
    }
    std::int64_t read_pending(void*target,std::size_t bytes,std::uint64_t offset)override{
        const auto got=pread(read_fd,target,bytes,static_cast<off_t>(offset));
        line("RETURN stage=read_pending got="+std::to_string(got));return got;
    }
    bool pending_unchanged()override{return read_fd>=0&&fd_key(read_fd)==pending&&path_key(published?part_path.c_str():pending_path.c_str())==pending;}
    bool publish_verified_pending(const std::string&digest)override{
        if(!split_context(3)||!source_unchanged()||!pending_unchanged()||!absent(part_path.c_str()))return false;
        line("VERIFIED_PENDING SHA256="+digest+" bytes="+std::to_string(pending[5]));
        const int rc=rename(pending_path.c_str(),part_path.c_str());line("RETURN stage=publish_rename rc="+std::to_string(rc));
        if(rc){uncertain=true;return false;}published=true;
        const auto renamed=fd_key(read_fd);const auto named=path_key(part_path.c_str());
        if(renamed!=named)return false;
        for(unsigned i=0;i<8;++i)if(renamed[i]!=pending[i])return false;
        pending=renamed;
        const int directory=open(SPLIT_PART_DIRECTORY,O_RDONLY|O_NOFOLLOW|O_DIRECTORY);
        if(directory<0)return false;
        const int sync=fsync(directory),closed=close(directory);
        line("RETURN stage=published_directory_fsync rc="+std::to_string(sync)+" close_rc="+std::to_string(closed));
        if(closed)uncertain=true;
        if(sync||closed)return false;
        record_key("PUBLISHED_PART",pending);return true;
    }
    bool truncate_source_once(std::uint64_t bytes)override{
        if(!split_context(4)||!source_unchanged()||!pending_unchanged())return false;
        const int rc=ftruncate(source,static_cast<off_t>(bytes));
        line("RETURN stage=source_ftruncate rc="+std::to_string(rc)+" bytes="+std::to_string(bytes));
        if(rc)uncertain=true;return rc==0;
    }
    bool flush_and_record_source(std::uint64_t bytes)override{
        const int rc=fsync(source);line("RETURN stage=source_fsync rc="+std::to_string(rc));if(rc)return false;
        result=fd_key(source);if(result!=path_key(SPLIT_SOURCE)||result[5]!=bytes)return false;
        for(unsigned i=0;i<5;++i)if(result[i]!=original[i])return false;
        record_key("SOURCE_AFTER",result);return true;
    }
    bool close_completed(){
        for(auto*member:{&source,&write_fd,&read_fd})if(*member>=0){const int fd=*member;*member=-1;if(close(fd)){uncertain=true;return false;}}
        line("FILES all_close_calls_returned=1 active_calls=0");return true;
    }
};
[[noreturn]]void retain(){(void)split_report_line("UNCERTAIN backing_retained=1 retry=0 GPU_calls=0");for(;;)sleep(1);}
std::string digest_hex(const unsigned char*data){std::string text;for(unsigned i=0;i<32;++i){text.push_back("0123456789abcdef"[data[i]>>4]);text.push_back("0123456789abcdef"[data[i]&15]);}return text;}
void verify_reassembled(void*buffer,std::uint64_t original_bytes,std::uint64_t process_started){
    const auto verification_started=split_now_ns();
    if(!verification_started)throw std::runtime_error("Reassembled integrity clock is unavailable");
    sha256_t whole;sha256_init(&whole);
    const auto count=(original_bytes+qwen_app::split_migration_part_bytes-1)/qwen_app::split_migration_part_bytes;
    for(std::uint64_t index=0;index<count;++index){
        if(!split_context(6))throw std::runtime_error("Reassembled integrity lost its idle source context");
        const auto path=index?std::string(SPLIT_PART_PREFIX)+std::to_string(index):std::string(SPLIT_SOURCE);
        const int fd=open(path.c_str(),O_RDONLY|O_NOFOLLOW|O_DIRECT);
        if(fd<0)throw std::runtime_error("A completed physical part is missing from reassembled verification");
        const auto before=fd_key(fd);const auto wanted=std::min<std::uint64_t>(qwen_app::split_migration_part_bytes,
            original_bytes-index*qwen_app::split_migration_part_bytes);
        if(before[5]!=wanted||path_key(path.c_str())!=before)throw std::runtime_error("Physical reassembly identity or exact size differs");
        sha256_t part;sha256_init(&part);
        for(std::uint64_t offset=0;offset<wanted;){
            const auto now=split_now_ns();
            if(!now||now<process_started||now-process_started>7200000000000ull||!split_headroom())
                throw std::runtime_error("Reassembled integrity exceeded its bounded process/reserve admission");
            const auto logical=std::size_t(std::min<std::uint64_t>(qwen_app::split_migration_window_bytes,wanted-offset));
            const auto requested=(logical+16383)&~std::size_t(16383);
            line("BEFORE stage=reassembled_read index="+std::to_string(index)+" offset="+std::to_string(offset)+" bytes="+std::to_string(requested));
            const auto got=pread(fd,buffer,requested,static_cast<off_t>(offset));line("RETURN stage=reassembled_read got="+std::to_string(got));
            if(got!=std::int64_t(logical))throw std::runtime_error("Reassembled physical read did not complete exactly");
            sha256_update(&whole,static_cast<const unsigned char*>(buffer),logical);sha256_update(&part,static_cast<const unsigned char*>(buffer),logical);offset+=logical;
        }
        if(fd_key(fd)!=before||path_key(path.c_str())!=before)throw std::runtime_error("A reassembled source changed during whole-file hashing");
        if(close(fd))retain();unsigned char digest[32];sha256_final(&part,digest);
        line("VERIFIED_PART index="+std::to_string(index)+" bytes="+std::to_string(wanted)+" SHA256="+digest_hex(digest));
        record_key(("PART_ID_"+std::to_string(index)).c_str(),before);
    }
    unsigned char digest[32];sha256_final(&whole,digest);const auto actual=digest_hex(digest);
    if(actual!=SPLIT_ORIGINAL_SHA256)throw std::runtime_error("Reassembled complete original SHA256 did not match its pinned receipt");
    const auto verification_finished=split_now_ns();
    if(verification_finished<verification_started)throw std::runtime_error("Reassembled integrity clock moved backwards");
    line("LOGICAL_COMPLETE bytes="+std::to_string(original_bytes)+" physical_parts="+std::to_string(count)+" SHA256="+actual+
        " verification_elapsed_ms="+std::to_string((verification_finished-verification_started+999999)/1000000));
}
}
int main(int argc,char**){
    static_assert(sizeof(off_t)==8,"Migration requires 64-bit offsets");
    if(!split_open_journal())return 2;
    void*window=nullptr;std::int64_t physical=-1;bool mapped=false,ok=false;NativeMigration*ops=nullptr;
    try{
        line("BEGIN nonce=" SPLIT_NONCE " CPU_only=1 window_bytes=8388608 GPU_calls=0 title_launches=0");
        if((argc!=0&&argc!=1)||!split_context(1)||!split_context(2)||!split_headroom())throw std::runtime_error("Fresh idle migration context refused");
        int rc=sceKernelAllocateDirectMemory(0,sceKernelGetDirectMemorySize(),qwen_app::split_migration_window_bytes,16384,PS5_KERNEL_DIRECT_TYPE_CPU,&physical);
        line("DIRECT allocation_returned=1 rc="+std::to_string(rc));if(rc||physical<0)throw std::runtime_error("Bounded migration allocation failed");
        rc=sceKernelMapDirectMemory(&window,qwen_app::split_migration_window_bytes,3,0,physical,16384);
        line("DIRECT mapping_returned=1 rc="+std::to_string(rc));if(rc||!window||reinterpret_cast<std::uintptr_t>(window)%16384)retain();mapped=true;
        const auto process_started=split_now_ns();Key current=initial_source_key();
        const auto original_bytes=std::uint64_t(SPLIT_ORIGINAL_BYTES);
        if((SPLIT_VERIFY_ONLY&&!SPLIT_BATCH_MODEL)||original_bytes<current[5]||original_bytes>(512ull<<30)||
           path_key(SPLIT_SOURCE)!=current)
            throw std::runtime_error("Original logical size and current prefix lineage differ");
        if(!SPLIT_VERIFY_ONLY)for(;;){
            const auto now=split_now_ns();
            if(!now||now<process_started||now-process_started>7200000000000ull)
                throw std::runtime_error("Fixed-source migration exceeded its bounded process deadline");
            const auto index=(current[5]-1)/qwen_app::split_migration_part_bytes;
            ops=new NativeMigration(current,SPLIT_BATCH_MODEL?std::string(SPLIT_PART_PREFIX)+std::to_string(index):std::string(SPLIT_PART));
            const auto result=qwen_app::migrate_verified_tail(*ops,window,current[5]);
            line("COMPLETE part_index="+std::to_string(result.part_index)+" part_bytes="+std::to_string(result.part_bytes)+
                " source_bytes="+std::to_string(result.new_source_bytes)+" SHA256="+result.part_sha256);
            current=ops->result;
            if(!ops->close_completed()||ops->uncertain)retain();delete ops;ops=nullptr;
            if(!SPLIT_BATCH_MODEL||current[5]<=qwen_app::split_migration_part_bytes)break;
        }
        if(SPLIT_BATCH_MODEL)verify_reassembled(window,original_bytes,process_started);
        ok=true;
    }catch(const std::exception&e){
        try{line(std::string("REFUSED reason=")+e.what()+" automatic_retries=0 files_retained=1");}catch(...){retain();}
    }
    if(ops&&(!ops->close_completed()||ops->uncertain))retain();
    if(mapped){const int rc=sceKernelMunmap(window,qwen_app::split_migration_window_bytes);if(rc)retain();
        if(sceKernelReleaseDirectMemory(physical,qwen_app::split_migration_window_bytes))retain();
        if(!split_report_line("DIRECT known_completion_cleanup_returned=1 fully_released=1"))retain();}
    else if(physical>=0)retain();
    if(!split_context(5)||!split_headroom())ok=false;
    if(!split_report_line(ok?"END success=1 active_calls=0 GPU_calls=0 title_launches=0 retry=0":"END success=0 active_calls=0 GPU_calls=0 title_launches=0 retry=0"))return 2;
    if(!split_close_journal())return 2;return ok?0:1;
}
