// SPDX-License-Identifier: MIT
#pragma once
#include "driver_tables.h"
#include "resident_phase_vm.h"
#include <ps5platform/kernel.h>
#include <cstring>
namespace qwen_app {
struct ResidentDirectTables {
    std::int64_t physical=-1;
    std::uint64_t mapped_bytes=0,allocated_bytes=0,available_before=0;
    std::uint64_t free_before=0,free_after=0;
    bool allocated=false,mapped=false,zeroed=false;
};
inline ResidentDirectTables &resident_direct_table_owner(){static ResidentDirectTables owner;return owner;}
inline void require_resident_direct_table_policy(const nlohmann::json &policy){
    const nlohmann::json expected={{"schema","ps5-qwen-resident-Direct-tables-v1"},{"enabled",true},
        {"CPU_Direct_type",12},{"virtual_alignment_bytes",16384},{"physical_alignment_bytes",65536},
        {"maximum_mapping_bytes",9486336},{"original_tables",673},{"original_table_bytes",9471408},
        {"same_virtual_addresses",true},{"exclusive_NOBITS_audits_required",true},
        {"all_original_SHA256_and_readonly_protection_required",true},
        {"physical_backing_retained_until_ordinary_OS_close",true},{"automatic_retries",0}};
    const auto &scope=policy.at("native_resident_Direct_tables");
    if(!scope.is_object()||scope.size()!=expected.size())throw std::runtime_error("Exact owned Direct table policy required");
    for(auto i=expected.begin();i!=expected.end();++i){const auto &v=scope.at(i.key());
        if((i.value().is_number_integer()?!v.is_number_integer():v.type()!=i.value().type())||v!=i.value())
            throw std::runtime_error("Owned Direct table policy differs");}
}
inline void map_resident_driver_tables_to_Direct(){
    static bool attempted=false;auto &owner=resident_direct_table_owner();
    if(attempted||!&qwen_driver_table_storage)throw std::runtime_error("Fresh original table owner required");attempted=true;
    const auto &plan=qwen_driver_table_storage;const auto begin=reinterpret_cast<std::uintptr_t>(plan.begin),end=reinterpret_cast<std::uintptr_t>(plan.end);
    if(!plan.tables||!plan.packed||plan.count!=673||!begin||end<=begin||begin%16384||end%16384||end-begin!=9486336)
        throw std::runtime_error("Audited exclusive original table range differs");
    std::uint64_t sum=0;
    for(std::size_t i=0;i<plan.count;++i){const auto &table=plan.tables[i];const auto at=reinterpret_cast<std::uintptr_t>(table.target);
        if(at<begin||at>=end||!table.bytes||table.bytes>end-at)throw std::runtime_error("A table escapes its exact owned NOBITS range");
        for(std::size_t j=0;j<i;++j){const auto other=reinterpret_cast<std::uintptr_t>(plan.tables[j].target);
            if(at<other+plan.tables[j].bytes&&other<at+table.bytes)throw std::runtime_error("Original table ranges overlap");}
        sum+=table.bytes;}
    if(sum!=9471408)throw std::runtime_error("Original complete table bytes differ");
    const auto before=admit_native_system_memory();require_resident_source_VM(before);owner.free_before=before.kernel_free;
    void *region_begin=nullptr,*region_end=nullptr;std::uint32_t protection=0;
    if(sceKernelQueryMemoryProtection(plan.begin,&region_begin,&region_end,&protection)||
       reinterpret_cast<std::uintptr_t>(region_begin)>begin||reinterpret_cast<std::uintptr_t>(region_end)<end||
       (protection&3)!=3||(protection&4))throw std::runtime_error("Original CPU writable non-executable table ownership differs");
    owner.mapped_bytes=end-begin;owner.allocated_bytes=(owner.mapped_bytes+65535)&~std::uint64_t(65535);
    const auto pool=sceKernelGetDirectMemorySize();std::int64_t available_start=-1;std::size_t available=0;
    if(pool<=0||sceKernelAvailableDirectMemorySize(0,pool,65536,&available_start,&available)||available_start<0||
       available<owner.allocated_bytes+(256ull<<20))throw std::runtime_error("Direct table allocation cannot retain the original reserve");
    owner.available_before=available;
    if(sceKernelAllocateDirectMemory(0,pool,owner.allocated_bytes,65536,PS5_KERNEL_DIRECT_TYPE_CPU,&owner.physical)||owner.physical<0)
        throw std::runtime_error("CPU Direct table allocation returned failure");
    owner.allocated=true;void *actual=plan.begin;
    if(sceKernelMapDirectMemory(&actual,owner.mapped_bytes,3,PS5_KERNEL_MAP_FIXED,owner.physical,16384)||actual!=plan.begin)
        throw std::runtime_error("CPU Direct table mapping did not return the exact owned address; backing retained");
    owner.mapped=true;
    if(sceKernelQueryMemoryProtection(plan.begin,&region_begin,&region_end,&protection)||
       reinterpret_cast<std::uintptr_t>(region_begin)>begin||reinterpret_cast<std::uintptr_t>(region_end)<end||(protection&3)!=3)
        throw std::runtime_error("CPU Direct table mapping protection differs; backing retained");
    std::memset(plan.begin,0,owner.mapped_bytes);owner.zeroed=true;
    const auto after=admit_native_system_memory();require_resident_existing_source_VM(after);owner.free_after=after.kernel_free;
    // The original restorer now writes all tables, checks all 673 hashes and
    // protects the same addresses read-only before any Vulkan initialization.
    // This process-lifetime CPU backing is not a GPU retirement-ledger entry.
}
}
