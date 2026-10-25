// SPDX-License-Identifier: MIT
#pragma once
#include "direct_bmp.h"
#include <cerrno>
#include <cstdio>
#include <fcntl.h>
#include <string>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>

namespace qwen_app {
enum class FrameMetadataABI { full_posix, native_descriptor };
// Only a new process-owned evidence file is writable. Errors deliberately do
// not close its descriptor or release the caller's window; OS close owns them.
class NativeFrameSink {
    std::string path_;
    int fd_=-1;
    struct stat created_{};
    bool direct_;
    FrameMetadataABI metadata_;
    std::uint64_t expected_bytes_;
    void (*stage_)(const char *);
    void (*guard_)();
    void stage(const char *text){if(stage_)stage_(text);}
    static bool owner(const struct stat &a,const struct stat &b){
        return a.st_dev==b.st_dev&&a.st_ino==b.st_ino&&a.st_mode==b.st_mode&&
            a.st_uid==b.st_uid&&a.st_gid==b.st_gid&&a.st_nlink==b.st_nlink;
    }
public:
    NativeFrameSink(const std::string &path,bool direct,void (*stage)(const char *),void (*guard)(),
                    FrameMetadataABI metadata=FrameMetadataABI::full_posix,
                    std::uint64_t expected_bytes=frame_bmp_bytes)
        :path_(path),direct_(direct),metadata_(metadata),expected_bytes_(expected_bytes),stage_(stage),guard_(guard) {
        if(!expected_bytes_||(expected_bytes_!=frame_bmp_bytes&&expected_bytes_>frame_write_window))
            throw std::invalid_argument("Evidence length escaped the fixed frame or bounded metadata profile");
        if(path.empty()||path.size()>1024)throw std::invalid_argument("Invalid evidence pathname");
        if(metadata_==FrameMetadataABI::native_descriptor) {
            const std::string prefix="/app0/qwen-runtime/";
            const auto name=path.substr(std::min(path.size(),prefix.size()));
            if(getuid()!=1||geteuid()!=1||path.compare(0,prefix.size(),prefix)!=0||name.empty()||
               name.find('/')!=std::string::npos||name.find('\\')!=std::string::npos||name.find("..")!=std::string::npos)
                throw std::runtime_error("Native frame creation requires its UID1 owner and exact application namespace");
        }
        if(guard_)guard_();
        stage("frame_capture_prepare_before_native_call");
        fd_=open(path_.c_str(),O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW|(direct_?O_DIRECT:0),0644);
        if(fd_<0)throw std::runtime_error("Fresh frame evidence open refused: errno="+std::to_string(errno));
        const int descriptor_result=fstat(fd_,&created_);const int descriptor_errno=errno;
        char detail[400];
        std::snprintf(detail,sizeof(detail),"frame_capture_descriptor_returned rc=%d errno=%d uid=%u euid=%u real_uid=%u mode=%o links=%u bytes=%lld device=%llu inode=%llu",
            descriptor_result,descriptor_errno,unsigned(created_.st_uid),unsigned(geteuid()),unsigned(getuid()),unsigned(created_.st_mode),
            unsigned(created_.st_nlink),static_cast<long long>(created_.st_size),
            static_cast<unsigned long long>(created_.st_dev),static_cast<unsigned long long>(created_.st_ino));stage(detail);
        if(descriptor_result||!S_ISREG(created_.st_mode)||!created_.st_ino||created_.st_size||
           (metadata_==FrameMetadataABI::full_posix&&(created_.st_uid!=geteuid()||created_.st_nlink!=1)))
            throw std::runtime_error(std::string("Fresh frame evidence owner refused: ")+detail);
        if(fchmod(fd_,0644)||fstat(fd_,&created_))throw std::runtime_error("Fresh frame evidence mode refused: errno="+std::to_string(errno));
        struct stat named{};
        const int flags=fcntl(fd_,F_GETFL);
        // Native libkernel omits UID/link metadata and can reject path stat.
        // Ownership here is the UID1 process's O_EXCL creation, not those zero
        // fields. Keep its private descriptor and stable device/inode/mode.
        // The CPU qualification independently verifies physical UID/link count.
        const int named_result=metadata_==FrameMetadataABI::full_posix?lstat(path_.c_str(),&named):fstat(fd_,&named);
        const int named_errno=errno;
        std::snprintf(detail,sizeof(detail),"frame_capture_named_identity_returned rc=%d errno=%d flags=%d direct_flag=%d uid=%u euid=%u mode=%o links=%u bytes=%lld device=%llu inode=%llu",
            named_result,named_errno,flags,flags>=0&&bool(flags&O_DIRECT),unsigned(named.st_uid),unsigned(geteuid()),unsigned(named.st_mode),
            unsigned(named.st_nlink),static_cast<long long>(named.st_size),static_cast<unsigned long long>(named.st_dev),static_cast<unsigned long long>(named.st_ino));stage(detail);
        if(flags<0 || (flags&O_ACCMODE)!=O_WRONLY || (direct_&&!(flags&O_DIRECT)) || named_result||!owner(created_,named))
            throw std::runtime_error(std::string("Frame evidence identity or Direct flag refused: ")+detail);
        stage("frame_capture_prepare_native_call_returned");
    }
    ~NativeFrameSink()=default;
    std::uint64_t now_ns(){
        struct timespec t{};if(clock_gettime(CLOCK_MONOTONIC,&t)||t.tv_sec<0||t.tv_nsec<0||t.tv_nsec>=1000000000)return 0;
        return std::uint64_t(t.tv_sec)*1000000000ull+std::uint64_t(t.tv_nsec);
    }
    std::int64_t write(void *data,std::size_t bytes){
        if(fd_<0||!data||!bytes||bytes>frame_write_window ||
           (direct_&&(reinterpret_cast<std::uintptr_t>(data)%frame_write_alignment||bytes%frame_write_alignment)))
            throw std::runtime_error("Frame evidence write escaped its owned window");
        if(metadata_==FrameMetadataABI::native_descriptor&&(getuid()!=1||geteuid()!=1))
            throw std::runtime_error("Native frame creator identity changed");
        if(guard_)guard_();
        stage("frame_capture_write_before_native_call");
        const auto n=::write(fd_,data,bytes);
        stage("frame_capture_write_native_call_returned");return n;
    }
    void finish(std::uint64_t bytes){
        if(bytes!=expected_bytes_||fd_<0||
           (metadata_==FrameMetadataABI::native_descriptor&&(getuid()!=1||geteuid()!=1)))
            throw std::runtime_error("Frame evidence size or creator identity refused");
        stage("frame_capture_fsync_before_native_call");const int synced=fsync(fd_);
        stage("frame_capture_fsync_native_call_returned");if(synced)throw std::runtime_error("Frame evidence sync refused");
        stage("frame_capture_trim_before_native_call");const int trimmed=ftruncate(fd_,static_cast<off_t>(bytes));
        stage("frame_capture_trim_native_call_returned");if(trimmed)throw std::runtime_error("Owned frame evidence trim refused");
        stage("frame_capture_final_identity_before_native_call");struct stat file_info{},named{};
        if(fsync(fd_)||fstat(fd_,&file_info)||
           (metadata_==FrameMetadataABI::full_posix?lstat(path_.c_str(),&named):fstat(fd_,&named))||!owner(created_,file_info)||
           !owner(file_info,named)||file_info.st_size!=static_cast<off_t>(bytes)||named.st_size!=file_info.st_size)
            throw std::runtime_error("Frame evidence final identity refused");
        stage("frame_capture_final_identity_native_call_returned");
        stage("frame_capture_close_before_native_call");const int closed=close(fd_);
        stage("frame_capture_close_native_call_returned");if(closed)throw std::runtime_error("Frame evidence close refused");
        fd_=-1;
    }
};
}
