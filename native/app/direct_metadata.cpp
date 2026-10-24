// SPDX-License-Identifier: MIT
#include "direct_metadata.h"
#include "mapped_source.h"
#include "system_memory.h"
#include "gguf.h"
#include <ps5platform/heap.h>
#include <atomic>
#include <cstdlib>
#include <exception>
#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>
extern "C" bool qwen_app_model_reads_enabled();
extern "C" gguf_context *__real_gguf_init_from_file(const char *,gguf_init_params);
namespace {
std::atomic<bool> enabled{false},busy{false};
std::vector<qwen_app::SourceFile> accepted;
qwen_app::DirectMetadataStats totals;
qwen_app::SourceIdentity identity(int fd) {
    struct stat s{};
    if(fstat(fd,&s)||!S_ISREG(s.st_mode)||!s.st_ino||s.st_size<=0||(s.st_mode&0022))
        throw std::runtime_error("Direct metadata requires an unchanged sealed original descriptor");
    return {std::uint64_t(s.st_dev),std::uint64_t(s.st_ino),std::uint64_t(s.st_mode),
        std::uint64_t(s.st_uid),std::uint64_t(s.st_gid),std::uint64_t(s.st_size),
        std::uint64_t(s.st_mtim.tv_sec),std::uint64_t(s.st_mtim.tv_nsec),
        std::uint64_t(s.st_ctim.tv_sec),std::uint64_t(s.st_ctim.tv_nsec)};
}
struct NativeMetadata final:qwen_app::MetadataReadOps {
    int fd;explicit NativeMetadata(int value):fd(value){}
    std::int64_t read_at(void *at,std::size_t bytes,std::uint64_t offset)override {
        if(qwen_app::qualified_system_headroom(qwen_app::admit_native_system_memory())<
           qwen_app::model_read_system_reserve+qwen_app::model_read_flexible_metadata_margin)
            throw std::runtime_error("Direct metadata must retain the existing Flexible/kernel reserves");
        return pread(fd,at,bytes,static_cast<off_t>(offset));
    }
    std::uint64_t now_ns()override{return std::chrono::duration_cast<std::chrono::nanoseconds>(qwen_app::ProfileClock::now().time_since_epoch()).count();}
};
struct Callback {
    qwen_app::DirectMetadataWindow &window;std::exception_ptr failure;
    static std::size_t read(void *userdata,void *output,std::uint64_t offset,std::size_t bytes) {
        auto &self=*static_cast<Callback*>(userdata);if(self.failure)return 0;
        try{return self.window.read(output,offset,bytes);}
        catch(...){self.failure=std::current_exception();return 0;}
    }
};
}
namespace qwen_app {
void enable_native_direct_metadata(){if(enabled.exchange(true)||busy.load()||!accepted.empty())throw std::runtime_error("Direct metadata may only be admitted once");}
void register_native_direct_metadata(const std::string &path,const std::array<std::uint64_t,10>&key) {
    if(!enabled.load()||busy.load()||accepted.size()>=256||path.empty()||path.size()>1024||path.find('\0')!=std::string::npos||!key[5])
        throw std::runtime_error("Direct metadata requires its complete sealed source admission");
    for(const auto &item:accepted)if(item.path==path||item.identity==key)throw std::runtime_error("Duplicate metadata source admission");
    accepted.push_back({path,key[5],key});
}
DirectMetadataStats native_direct_metadata_stats(){if(busy.load())throw std::runtime_error("Metadata completion remains unknown");return totals;}
}
extern "C" gguf_context *__wrap_gguf_init_from_file(const char *path,gguf_init_params params) {
    if(!enabled.load(std::memory_order_acquire))return __real_gguf_init_from_file(path,params);
    if(!path||!params.no_alloc||busy.exchange(true))throw std::runtime_error("Direct GGUF metadata requires one exclusive no-allocation parser");
    const auto file=std::find_if(accepted.begin(),accepted.end(),[&](const auto &item){return item.path==path;});
    if(file==accepted.end())throw std::runtime_error("GGUF metadata path is outside the admitted original model");
    const bool borrowed=qwen_app_model_reads_enabled();void *buffer=nullptr;int fd=-1;
    if(borrowed) {
        const auto lease=qwen_app::begin_native_metadata_window(path);buffer=lease.target;fd=lease.fd;
        if(lease.bytes<qwen_app::metadata_direct_window)throw std::runtime_error("Metadata cannot exceed the existing source lease");
    }else {
        fd=open(path,O_RDONLY|O_NOFOLLOW|O_DIRECT);
        if(fd<0||posix_memalign(&buffer,qwen_app::metadata_direct_alignment,qwen_app::metadata_direct_window)||!buffer||!ps5_heap_owns(buffer))
            throw std::runtime_error("Direct metadata requires its bounded tracked startup buffer");
    }
    if(identity(fd)!=file->identity)throw std::runtime_error("Direct metadata source identity changed before reading");
    NativeMetadata ops(fd);qwen_app::DirectMetadataWindow window(ops,buffer,file->bytes);Callback callback{window,{}};
    auto *context=gguf_init_from_callback(Callback::read,&callback,qwen_app::metadata_direct_window,file->bytes,params);
    // Any failed/unknown read or parse retains its window and descriptor/lease.
    // There is no destructor cleanup, fallback, retry, or speculative release.
    if(callback.failure)std::rethrow_exception(callback.failure);
    if(!context)throw std::runtime_error("Original GGUF metadata parsing did not complete");
    window.completed();
    if(identity(fd)!=file->identity||window.logical_end>gguf_get_data_offset(context))
        throw std::runtime_error("Direct metadata identity or prefix completion changed");
    if(borrowed)qwen_app::end_native_metadata_window();
    else {if(close(fd))throw std::runtime_error("Direct metadata descriptor close is uncertain");free(buffer);}
    ++totals.completed_files;if(borrowed)++totals.borrowed_files;
    totals.physical_bytes+=window.physical_bytes;totals.physical_reads+=window.physical_reads;
    totals.maximum_prefix=std::max(totals.maximum_prefix,window.logical_end);
    busy.store(false,std::memory_order_release);return context;
}
