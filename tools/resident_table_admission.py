#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Apply the existing CPU metadata price to exact table restoration, with causes."""
import json

SCOPE=dict(schema='ps5-qwen-CPU-table-metadata-v1',enabled=True,CPU_base_extra_pages=21,
    output_extra_pages=20,new_scratch_extra_pages=19,original_GPU_floor_changes=0,
    all_original_tables_and_SHA256_required=True,original_readonly_protection_required=True,
    backing_retained_until_ordinary_OS_close=True,automatic_retries=0)


def incremental_header(text):
    old='std::max<std::uint64_t>(m.kernel_reserved,256)+additional'
    if text.count(old)!=1:raise ValueError('One original incremental-table price required')
    text=text.replace(old,'(qwen_app_resident_CPU_metadata_scope_active()?21ull:std::max<std::uint64_t>(m.kernel_reserved,256))+additional')
    text=text.replace('#include "driver_table_restore.h"','#include "driver_table_restore.h"\n#include "system_memory.h"\n#include <cerrno>')
    old='    bool fault=false,memory_refused=false,completed=false;'
    if text.count(old)!=1:raise ValueError('Original exact table result required')
    text=text.replace(old,old+'\n    bool protection_attempted=false;int protection_rc=INT32_MIN,protection_errno=0;')
    old='    if(ok)ok=result.permit()&&mprotect(p.begin,end-begin,PROT_READ)==0;'
    if text.count(old)!=1:raise ValueError('Original readonly protection call required')
    text=text.replace(old,'''    if(ok){
        if(!result.permit())ok=false;
        else{result.protection_attempted=true;errno=0;result.protection_rc=mprotect(p.begin,end-begin,PROT_READ);
            result.protection_errno=errno;ok=result.protection_rc==0;}
    }''')
    return text


def direct_header(text):
    old='std::uint64_t free_before=0,free_after=0;'
    if text.count(old)!=1:raise ValueError('Original Direct table owner required')
    text=text.replace(old,'std::uint64_t free_before=0,free_after_map=0,free_after=0;')
    old='    owner.mapped=true;'
    if text.count(old)!=1:raise ValueError('One exact returned mapping frontier required')
    text=text.replace(old,old+'\n    owner.free_after_map=observe_native_system_memory().kernel_free;')
    old='    const auto after=admit_native_system_memory();require_resident_existing_source_VM(after);owner.free_after=after.kernel_free;'
    if text.count(old)!=1:raise ValueError('One exact first-touch frontier required')
    text=text.replace(old,'    owner.free_after=observe_native_system_memory().kernel_free;\n'+old)
    return text


def entry(text):
    main=text.index('int main(int argc, char ** argv)')
    helper='''static qwen_app::ResidentTableMemory resident_tables_attempt;
static bool resident_tables_attempted=false;
static Json resident_tables_diagnostic(){
    const auto &r=resident_tables_attempt;const auto &owner=qwen_app::resident_direct_table_owner();
    return {{"attempted",resident_tables_attempted},{"completed",r.completed},{"memory_refused",r.memory_refused},
        {"scratch_fault",r.fault},{"scratch_live_bytes",r.live},{"tables_completed",r.tables},{"bytes_completed",r.bytes},{"chunks",r.chunks},
        {"free_before_restoration",r.before},{"minimum_during_restoration",r.minimum==UINT64_MAX?Json(nullptr):Json(r.minimum)},
        {"free_after_last_restore_check",r.after},{"protection_attempted",r.protection_attempted},
        {"protection_return_code",r.protection_attempted?Json(r.protection_rc):Json(nullptr)},
        {"protection_errno",r.protection_attempted?Json(r.protection_errno):Json(nullptr)},
        {"free_before_Direct_map",owner.free_before},{"free_after_Direct_map_before_touch",owner.free_after_map},
        {"free_after_first_touch",owner.free_after},{"Direct_allocated",owner.allocated},{"Direct_mapped",owner.mapped},
        {"Direct_zeroed",owner.zeroed},{"CPU_metadata_scope_active",qwen_app_resident_CPU_metadata_scope_active()},
        {"CPU_selected_base_extra_pages",21},{"output_extra_pages",20},{"new_scratch_extra_pages",19},
        {"global_VM_not_exclusive_attribution",true},{"GPU_calls",0}};
}
'''
    text=text[:main]+helper+text[main:]
    old='        const auto restored=qwen_app::restore_resident_tables_incrementally();'
    if text.count(old)!=1:raise ValueError('One actual owned Direct table restoration required')
    scope=json.dumps(SCOPE,separators=(',',':'))
    new='        if(policy.at("native_resident_CPU_table_pricing")!=Json::parse(R"table('+scope+')table"))throw std::runtime_error("Exact CPU table metadata scope required");\n'
    new+='''        resident_tables_attempted=true;
        const auto restored=(resident_tables_attempt=qwen_app::restore_resident_tables_incrementally());
        write_fresh_report(startup.admission_report+".resident.tables-attempt",resident_tables_diagnostic());
        if(!restored.completed&&restored.memory_refused)throw qwen_app::KernelMemoryPressure();'''
    text=text.replace(old,new)
    old='{"last_model_load_error",qwen_app::resident_last_model_error()},'
    if text.count(old)!=1:raise ValueError('One bounded native failure diagnostic required')
    return text.replace(old,old+'{"resident_tables",resident_tables_diagnostic()},')
