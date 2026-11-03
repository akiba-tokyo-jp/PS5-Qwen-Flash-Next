// SPDX-License-Identifier: MIT
#pragma once
#include "early_CPU_tables.h"
#include <cstdint>
#include <stdexcept>
namespace qwen_app {
inline void require_early_CPU_table_backing(const qwen_early_CPU_tables*r,
    std::uintptr_t begin,std::uintptr_t end,std::uint64_t allocated){
    if(!r||!begin||begin%65536||end<=begin||end-begin!=9486336||allocated!=9502720||
       r->begin!=begin||r->end!=begin+allocated||r->mapped_bytes!=allocated||r->allocated_bytes!=allocated||
       r->physical<0||std::uint64_t(r->physical)%65536||r->status||r->allocated!=1||r->mapped!=1||
       r->zeroed!=1||r->checksum_passed!=1||r->all_CPU_operations_returned!=1||
       r->checksum!=UINT64_C(17437583033832448805)||r->minimum_free<919||
       r->available_before<allocated+(256ull<<20))
        throw std::runtime_error("The exact completed early CPU table backing is required; retain existing ownership");
}
}
