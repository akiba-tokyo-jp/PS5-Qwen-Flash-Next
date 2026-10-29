// SPDX-License-Identifier: MIT
#pragma once
#include "direct_metadata.h"
#include <optional>

namespace qwen_app {
// A composite GGUF retains its full logical tensor span, while only its
// complete header prefix is physically contiguous in the first packed part.
// Ordinary sources keep their qualified DirectMetadataWindow unchanged.
class ExpertQ2MetadataWindow {
    MetadataReadOps &ops_;
    unsigned char *window_;
    std::uint64_t physical_,prefix_,started_,base_=0,valid_=0;
    bool failed_=false;
    std::optional<DirectMetadataWindow> ordinary_;
    void deadline(){
        const auto now=ops_.now_ns();
        if(!started_||now<started_||now-started_>20000000000ull)
            throw std::runtime_error("Composite metadata exceeded its finite read deadline");
    }
public:
    std::uint64_t physical_bytes=0,physical_reads=0,logical_end=0;
    ExpertQ2MetadataWindow(MetadataReadOps &ops,void *window,std::uint64_t logical,
                          std::uint64_t physical,std::uint64_t prefix)
        :ops_(ops),window_(static_cast<unsigned char*>(window)),physical_(physical),prefix_(prefix),started_(ops.now_ns()){
        if(!prefix){ordinary_.emplace(ops,window,logical);return;}
        if(!window_||reinterpret_cast<std::uintptr_t>(window_)%metadata_direct_alignment||!started_||
           !physical||physical>logical||logical>(512ull<<30)||prefix>metadata_direct_limit||
           prefix>physical||prefix>=logical)
            throw std::invalid_argument("A complete physically present composite header is required");
    }
    std::size_t read(void *target,std::uint64_t offset,std::size_t bytes){
        if(ordinary_){const auto n=ordinary_->read(target,offset,bytes);
            physical_bytes=ordinary_->physical_bytes;physical_reads=ordinary_->physical_reads;
            logical_end=ordinary_->logical_end;return n;}
        if(failed_)throw std::runtime_error("Failed composite metadata reads are quarantined");
        try{
            if(!target||!bytes||bytes>metadata_direct_window||offset>=prefix_||bytes>prefix_-offset)
                throw std::runtime_error("Composite metadata escaped its verified contiguous header");
            std::size_t done=0;
            while(done<bytes){
                const auto at=offset+done;
                if(!valid_||at<base_||at-base_>=valid_){
                    deadline();base_=at&~std::uint64_t(metadata_direct_window-1);
                    const auto actual=std::min<std::uint64_t>(metadata_direct_window,physical_-base_);
                    const auto requested=std::size_t((actual+metadata_direct_alignment-1)&~std::uint64_t(metadata_direct_alignment-1));
                    const auto got=ops_.read_at(window_,requested,base_);
                    if(got!=std::int64_t(actual))throw std::runtime_error("Composite metadata physical read was incomplete");
                    deadline();valid_=actual;physical_bytes+=actual;++physical_reads;
                }
                const auto n=std::min<std::size_t>(bytes-done,std::size_t(valid_-(at-base_)));
                std::memcpy(static_cast<unsigned char*>(target)+done,window_+(at-base_),n);done+=n;
            }
            logical_end=std::max(logical_end,offset+bytes);return bytes;
        }catch(...){failed_=true;throw;}
    }
    void completed(){if(ordinary_){ordinary_->completed();return;}
        if(failed_)throw std::runtime_error("Composite metadata completion is not qualified");deadline();}
};
void register_expert_q2_composite_metadata(const std::string &,
    const std::array<std::uint64_t,10>&,std::uint64_t logical,std::uint64_t header);
}
