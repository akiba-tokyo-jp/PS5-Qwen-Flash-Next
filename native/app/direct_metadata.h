// SPDX-License-Identifier: MIT
#pragma once
#include <algorithm>
#include <array>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <stdexcept>
#include <string>
namespace qwen_app {
inline constexpr std::size_t metadata_direct_alignment=16384,metadata_direct_window=1u<<20;
inline constexpr std::uint64_t metadata_direct_limit=64ull<<20;
struct MetadataReadOps {
    virtual ~MetadataReadOps()=default;
    virtual std::int64_t read_at(void *,std::size_t,std::uint64_t)=0;
    virtual std::uint64_t now_ns()=0;
};
// The parser receives original bytes from a fixed aligned cache. Only the
// metadata prefix is addressable; the complete original file size still reaches
// GGUF's tensor-span validation. Unknown reads retain the caller-owned window.
class DirectMetadataWindow {
    MetadataReadOps &ops_;unsigned char *window_;std::uint64_t file_bytes_,started_,base_=0,valid_=0;
    bool failed_=false;
    void deadline() {
        const auto now=ops_.now_ns();
        if(!started_||now<started_||now-started_>20000000000ull)
            throw std::runtime_error("Direct metadata exceeded its finite read deadline");
    }
public:
    std::uint64_t physical_bytes=0,physical_reads=0,logical_end=0;
    DirectMetadataWindow(MetadataReadOps &ops,void *window,std::uint64_t bytes):ops_(ops),window_(static_cast<unsigned char*>(window)),file_bytes_(bytes),started_(ops.now_ns()) {
        if(!window_||reinterpret_cast<std::uintptr_t>(window_)%metadata_direct_alignment||!bytes||bytes>(512ull<<30)||!started_)
            throw std::invalid_argument("Direct metadata needs an aligned fixed window and original size");
    }
    std::size_t read(void *target,std::uint64_t offset,std::size_t bytes) {
        if(failed_)throw std::runtime_error("Failed metadata reads are quarantined; no retry");
        try {
            if(!target||!bytes||bytes>metadata_direct_window||offset>=file_bytes_||bytes>file_bytes_-offset||
               offset>=metadata_direct_limit||bytes>metadata_direct_limit-offset)
                throw std::runtime_error("GGUF metadata escaped its original bounded prefix");
            std::size_t done=0;
            while(done<bytes) {
                const auto at=offset+done;
                if(!valid_||at<base_||at-base_>=valid_) {
                    deadline();base_=at&~std::uint64_t(metadata_direct_window-1);
                    const auto logical=std::min<std::uint64_t>(metadata_direct_window,file_bytes_-base_);
                    const auto requested=std::size_t((logical+metadata_direct_alignment-1)&~std::uint64_t(metadata_direct_alignment-1));
                    const auto got=ops_.read_at(window_,requested,base_);
                    if(got!=std::int64_t(logical))throw std::runtime_error("Direct metadata read did not return exact original bytes");
                    deadline();valid_=logical;physical_bytes+=logical;++physical_reads;
                }
                const auto count=std::min<std::size_t>(bytes-done,std::size_t(valid_-(at-base_)));
                std::memcpy(static_cast<unsigned char*>(target)+done,window_+(at-base_),count);done+=count;
            }
            logical_end=std::max(logical_end,offset+bytes);return bytes;
        }catch(...){failed_=true;throw;}
    }
    void completed(){if(failed_)throw std::runtime_error("Metadata completion is not qualified");deadline();}
};
struct DirectMetadataStats {
    std::uint64_t completed_files=0,borrowed_files=0,physical_bytes=0,physical_reads=0,maximum_prefix=0;
};
void enable_native_direct_metadata();
void register_native_direct_metadata(const std::string &,const std::array<std::uint64_t,10> &,
                                    std::uint64_t logical_bytes=0);
std::uint64_t native_metadata_logical_bytes(int fd,std::uint64_t physical_bytes);
DirectMetadataStats native_direct_metadata_stats();
}
