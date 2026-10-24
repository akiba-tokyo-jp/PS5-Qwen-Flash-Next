// SPDX-License-Identifier: MIT
// Hold the original model spans concurrently using the unchanged provider.
#include "virtual_source.h"
#include <array>
#include <cstdint>
#include "virtual_charge_sizes.h"
extern "C" int virtual_charge_checkpoint(const char *,unsigned,std::uint64_t,unsigned);
extern "C" int virtual_charge_pause();
extern "C" int virtual_charge_run() {
    std::array<std::uintptr_t,80> owned{};unsigned count=0;
    try {
        for(unsigned i=0;i<sizeof(virtual_charge_sizes)/sizeof(virtual_charge_sizes[0]);++i) {
            const auto bytes=virtual_charge_sizes[i];
            if(!virtual_charge_checkpoint("before",i,bytes,1)) {
                if(!virtual_charge_checkpoint("stopped_capacity",i,bytes,0))return 0;
                break;
            }
            owned[count]=qwen_app::reserve_native_virtual_source(bytes);++count;
            if(!virtual_charge_checkpoint("reserved",i,bytes,0))return 0;
        }
        if(!virtual_charge_checkpoint("all_held",count,0,0))return 0;
        while(count) {
            const auto index=--count;
            qwen_app::release_native_virtual_source(owned[index],virtual_charge_sizes[index]);
            if(!virtual_charge_checkpoint("released",index,virtual_charge_sizes[index],0))return 0;
        }
        for(unsigned i=0;i<20;++i)
            if(!virtual_charge_pause()||!virtual_charge_checkpoint("settled",i,0,0))return 0;
        return 1;
    } catch(...) {
        // Retain provider ownership after any failed or unknown operation.
        return 0;
    }
}
