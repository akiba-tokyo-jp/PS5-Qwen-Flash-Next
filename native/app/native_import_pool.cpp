// SPDX-License-Identifier: MIT
#include "native_import_pool.h"
static_assert(sizeof(ps5_ai_flex_stats)==72,"Preserved native import-pool metadata ABI");
// The native RADV compatibility code appends its extra heap only for a real
// owned pool. Returning zero keeps the original Direct heaps intact, refuses
// host-pointer imports and never invents capacity or borrows MOSS allocations.
extern "C" uint64_t ps5_ai_flex_pool_bytes(void) {return 0;}
extern "C" void ps5_ai_flex_snapshot(ps5_ai_flex_stats * out) {if(out)*out={};}
extern "C" bool ps5_ai_flex_grant_gpu(void *,uint64_t) {return false;}
