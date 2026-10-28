// SPDX-License-Identifier: MIT
#pragma once
#include <cstdint>
#include <stdexcept>
namespace qwen_app {
// The pinned ON_DEVICE writer retains mem_storage[seq0] on its context and
// reuses its buffers when the complete snapshot payload size is unchanged.
// Credit only a snapshot whose capture and complete request reset returned.
class ResidentCheckpointCapacity {
    const void *owner_=nullptr;
    std::uint64_t payload_=0;
public:
    static std::uint64_t rounded(std::uint64_t bytes) {
        if(!bytes||bytes>(136ull<<20))throw std::runtime_error("Checkpoint payload exceeds the original complete-state scope");
        return (bytes+(2ull<<20)-1)&~((2ull<<20)-1);
    }
    std::uint64_t new_allocation(const void *owner,std::uint64_t bytes)const {
        const auto full=rounded(bytes);
        if(!owner||(owner_&&owner_!=owner))throw std::runtime_error("Checkpoint capacity belongs to another original context");
        return owner_&&payload_==bytes?0:full;
    }
    void completed(const void *owner,std::uint64_t bytes,bool positively_reset) {
        (void)new_allocation(owner,bytes);
        if(!positively_reset)throw std::runtime_error("Checkpoint capacity requires positive complete capture and request reset");
        owner_=owner;payload_=bytes;
    }
};
}
