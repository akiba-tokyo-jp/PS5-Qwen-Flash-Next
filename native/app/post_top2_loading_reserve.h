// SPDX-License-Identifier: MIT
#pragma once
#include <algorithm>
#include <array>
#include <cstdint>
#include <stdexcept>
namespace qwen_app {
// An explicit, once-only model-loading experiment. Preserve the observed OS
// minimum and reservation; alter only the legacy256-page application padding.
class PostTop2LoadingReserve {
    bool active_=false,consumed_=false;
    std::uint64_t calls_=0,changed_=0,legacy_refusals_=0,minimum_free_=UINT64_MAX;
public:
    void select(bool v){
        if(v?(active_||consumed_):!active_)throw std::logic_error("Loading reserve scope must enter and retire once");
        active_=v;if(!v)consumed_=true;
    }
    std::uint64_t extra(std::uint64_t free,std::uint64_t minimum,std::uint64_t reserved,std::uint64_t legacy){
        if(!active_)return legacy;
        if(minimum!=898||reserved!=206)throw std::runtime_error("Observed loading OS minimum and reservation changed");
        if(legacy!=256)return legacy;
        ++calls_;++changed_;legacy_refusals_+=free<minimum+legacy;minimum_free_=std::min(minimum_free_,free);
        return reserved;
    }
    std::array<std::uint64_t,6>stats()const{return {active_,consumed_,calls_,changed_,legacy_refusals_,minimum_free_};}
};
}
