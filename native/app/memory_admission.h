// SPDX-License-Identifier: MIT
#pragma once
#include <cstdint>
#include <limits>
#include <initializer_list>
#include <stdexcept>
#include <string>
namespace qwen_app {
inline std::uint64_t checked_memory_sum(std::uint64_t a, std::uint64_t b) {
    if (b > std::numeric_limits<std::uint64_t>::max()-a) throw std::overflow_error("Memory accounting overflow");
    return a+b;
}
struct ModelFootprint {
    std::uint64_t device_weights = 0, mapped_experts = 0, lazy_ple = 0, mapped_embeddings = 0;
    std::uint64_t skipped_mtp = 0, mapped_files = 0, largest_device_tensor = 0, tensors = 0;
    unsigned trunk_layers = 0;
    void tensor(const std::string & name, std::uint64_t bytes) {
        if (name.empty() || !bytes || !trunk_layers) throw std::invalid_argument("Invalid model footprint entry");
        ++tensors;
        if (name.rfind("blk.",0)==0) {
            const auto end=name.find('.',4); const auto text=name.substr(4,end-4);
            if(end==std::string::npos||text.empty()||text.find_first_not_of("0123456789")!=std::string::npos)
                throw std::invalid_argument("Invalid model layer name");
            if(std::stoull(text)>=trunk_layers) { skipped_mtp=checked_memory_sum(skipped_mtp,bytes);return; }
        }
        if(name=="per_layer_token_embd.weight") lazy_ple=checked_memory_sum(lazy_ple,bytes);
        else if(name=="token_embd.weight") mapped_embeddings=checked_memory_sum(mapped_embeddings,bytes);
        else if(name.find(".ffn_")!=std::string::npos && name.find("_exps.weight")!=std::string::npos)
            mapped_experts=checked_memory_sum(mapped_experts,bytes);
        else {
            device_weights=checked_memory_sum(device_weights,bytes);
            if(bytes>largest_device_tensor) largest_device_tensor=bytes;
        }
    }
};
struct MemoryObservation { std::uint64_t driver_free=0, direct_largest=0, os_free=0, device_max_buffer=0; };
struct MemoryBudget {
    std::uint64_t expert_cache=512ull<<20, context=1024ull<<20, workspace=512ull<<20;
    std::uint64_t staging=128ull<<20, cpu_working=128ull<<20, os_reserve=256ull<<20, direct_reserve=512ull<<20;
    std::uint64_t device_requirement(const ModelFootprint & model) const {
        auto bytes=model.device_weights;
        for(auto value:{expert_cache,context,workspace,staging,cpu_working,os_reserve,direct_reserve}) bytes=checked_memory_sum(bytes,value);
        return bytes;
    }
    void admit(const ModelFootprint & model,const MemoryObservation & observed) const {
        if(!model.device_weights||!model.mapped_experts||!model.lazy_ple||!model.mapped_embeddings||
           !model.mapped_files||model.mapped_files>(512ull<<30))
            throw std::runtime_error("Complete original model footprint is required before loading");
        if(!observed.driver_free||!observed.direct_largest||!observed.os_free||!observed.device_max_buffer)
            throw std::runtime_error("Fresh driver, Direct and OS memory observations are required");
        if(model.largest_device_tensor>observed.device_max_buffer)
            throw std::runtime_error("A resident model tensor exceeds the device buffer limit");
        const auto needed=device_requirement(model);
        if(needed>observed.driver_free||needed>observed.direct_largest||
           checked_memory_sum(cpu_working,os_reserve)>observed.os_free)
            throw std::runtime_error("Observed shared-memory headroom cannot admit the original model");
    }
};
}
