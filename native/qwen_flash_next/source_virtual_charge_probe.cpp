// SPDX-License-Identifier: MIT
// Exercise the actual source reservation provider, without files or GPU work.
#include "virtual_source.h"
#include <array>
#include <cstdint>
extern "C" int virtual_charge_checkpoint(const char *,unsigned,std::uint64_t,unsigned);
extern "C" int virtual_charge_pause();
extern "C" int virtual_charge_run() {
    // Every extent is no larger than the already qualified original PLE file.
    constexpr std::array<std::uint64_t,6> sizes{16384,1ull<<30,4ull<<30,16ull<<30,64ull<<30,102400491712ull};
    try {
        for(unsigned i=0;i<sizes.size();++i) {
            const auto bytes=sizes[i];
            const auto qualified=virtual_charge_checkpoint("before",i,bytes,1);
            if(!qualified) {
                if(!virtual_charge_checkpoint("skipped_capacity",i,bytes,0))return 0;
                continue;
            }
            const auto at=qwen_app::reserve_native_virtual_source(bytes);
            // Even a low post-reserve observation never releases an unknown
            // lease. This reserve/protection pair has positively completed.
            const auto observed=virtual_charge_checkpoint("reserved",i,bytes,0);
            qwen_app::release_native_virtual_source(at,bytes);
            if(!observed||!virtual_charge_checkpoint("released",i,bytes,0))return 0;
            for(unsigned j=0;j<10;++j)
                if(!virtual_charge_pause()||!virtual_charge_checkpoint("settled",i,bytes,0))return 0;
        }
        return 1;
    } catch(...) {
        // The actual provider retains failed ownership. Do not manually free,
        // repeat, or proceed to another reservation after any exception.
        return 0;
    }
}
