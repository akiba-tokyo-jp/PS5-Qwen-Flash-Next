#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build an early title-context Direct query with no model/source/backend initialization."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess

from build_performance_quantizer import record
from build_speculative_batch_probe import once
from check_headless_legacy_policy import check as check_legacy_policy
from start_success_route import load,need,save

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','base-entry','prior-close','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();base=load(a.base_entry);prior=load(a.prior_close);profile=load(base['application_policy']['path'])
    need(base['completed'] and base['CPU_minimum_plus_21_unchanged'] and prior['completed'] and prior['ordinary_exit_observed'] and
        prior['current_seven_restored_and_native_hashed'] and prior['GPU_work_completion_known'] and prior['Direct_retirement_readmission_pending'],
        'Exact known-completed GPU work, ordinary exit and restored deployment required')
    for row in (base['entry'],base['reader'],profile['source']):need(record(row['path'])==row,'Selected entry input changed')
    a.out.mkdir(parents=True,exist_ok=False)
    for header in Path(profile['source']['path']).parent.glob('*.h'):shutil.copyfile(header,a.out/header.name)
    minimum=prior['required_title_context_Direct_baseline']
    scope=dict(schema='ps5-qwen-early-CPU-Direct-readmission-v1',kind='CPU-Direct-readmission',requests=0,model_loads=0,GPU_calls=0,
        HTTP_requests=0,VideoOut_starts=0,early_return_before_model_source_initialization=True,
        source_workers_created=0,source_payload_reads=0,required_Direct_available=minimum,prior_close=record(a.prior_close)['sha256'])
    original=Path(profile['source']['path']).read_text(encoding='utf-8')
    text='#include "early_direct_readmission.h"\n'+original
    marker='        const auto policy = Json::parse(policy_file);'
    text=once(text,marker,marker+'\n        if(policy.at("native_headless_model_audit")!=Json::parse('+json.dumps(json.dumps(scope,separators=(',',':')))+'))throw std::runtime_error("Exact early CPU Direct readmission scope required");')
    marker='        qwen_app::require_first_generation_policy(policy,false);'
    need(text.count(marker)==1,'One actual legacy policy boundary required')
    start=text.index(marker)+len(marker);end=text.index('    }catch(const std::exception &e){',start)
    text=text[:start]+'''
        const auto run=policy.at("native_first_generation_validation").at("run_id").get<std::string>();
        write_fresh_report(startup.admission_report+".first.start",{{"schema","ps5-qwen-first-generation-start-v1"},
            {"pid",getpid()},{"run_id",run},{"candidate_SELF_sha256",policy.at("native_first_generation_validation").at("candidate_SELF_sha256")},
            {"model_receipt_sha256",policy.at("native_first_generation_validation").at("model_receipt_sha256")},
            {"model_loaded",false},{"Vulkan_initialized",false}});
        qwen_native_stage("early_CPU_Direct_query_before_model_sources_or_backend");
        auto audit=qwen_app::early_Direct_readmission(MINIMUM);
        audit.update({{"pid",getpid()},{"run_id",run},{"candidate_SELF_sha256",policy.at("native_first_generation_validation").at("candidate_SELF_sha256")}});
        write_fresh_report(startup.admission_report+".audit",audit);
        struct ps5_heap_stats heap{};ps5_heap_stats(&heap);
        write_fresh_report(startup.admission_report,{{"schema","ps5-qwen-early-CPU-Direct-completion-v1"},{"kind","CPU-Direct-readmission"},
            {"completed",true},{"pid",getpid()},{"run_id",run},{"candidate_SELF_sha256",policy.at("native_first_generation_validation").at("candidate_SELF_sha256")},
            {"model_receipt_sha256",policy.at("native_first_generation_validation").at("model_receipt_sha256")},
            {"requests",Json::array()},{"model_loads",0},{"HTTP_requests",0},{"VideoOut_starts",0},{"GPU_calls",0},
            {"audit",audit},{"source_windows",0},{"source_completed_windows",0},{"model_sources_initialized",false},
            {"all_model_source_device_owners_positively_retired",true},{"device_ledger_live_bytes",0},
            {"device_ledger_initialized",false},{"application_GPU_buffers_created",0},
            {"device_ledger_peak_bytes",0},{"CPU_heap_peak_bytes",heap.peak_bytes}});
        qwen_native_stage("resident_additional_completed_waiting_for_ordinary_close");
        for(;;)(void)usleep(1000000);
'''.replace('MINIMUM',str(minimum)+'ULL')+text[end:]
    source=a.out/'entry.private.cpp';source.write_text(text,encoding='utf-8',newline='\n');entry=a.out/'entry.o'
    header=a.out/'early_direct_readmission.h';header.write_text('#pragma once\n#include <cstdint>\n#include <nlohmann/json.hpp>\nnamespace qwen_app {nlohmann::json early_Direct_readmission(std::uint64_t);}\n',encoding='utf-8',newline='\n')
    runtime=a.out/'early_direct_readmission.cpp';runtime.write_text('''#include "early_direct_readmission.h"
#include "system_memory.h"
#include <ps5platform/kernel.h>
#include <ps5platform/heap.h>
namespace qwen_app {
nlohmann::json early_Direct_readmission(std::uint64_t minimum){
    const auto memory=observe_native_system_memory();
    struct ps5_heap_stats heap{};ps5_heap_stats(&heap);
    const auto total=sceKernelGetDirectMemorySize();std::int64_t start=-1;std::size_t available=0;
    const int rc=total>0?sceKernelAvailableDirectMemorySize(0,total,65536,&start,&available):-1;
    const bool valid=total>0&&rc==0&&start>=0&&std::uint64_t(start)<=std::uint64_t(total)&&available>0&&available<=std::uint64_t(total)-std::uint64_t(start);
    return {{"completed",true},{"model_loads",0},{"GPU_calls",0},{"model_sources_initialized",false},{"source_workers_created",0},
        {"source_descriptor_worker_and_scratch_retired",true},{"source_payload_reads",0},{"device_ledger_initialized",false},
        {"Direct_pool_bytes",total},{"query_rc",rc},{"largest_start",start},{"largest_Direct_available",available},
        {"Direct_query_valid",valid},{"required_pre_model_available",minimum},{"Direct_readmission_passed",valid&&available>=minimum},
        {"CPU_heap_mapped_bytes",heap.mapped_bytes},{"CPU_heap_peak_bytes",heap.peak_bytes},{"CPU_libc_fallbacks",heap.libc_fallbacks},
        {"kernel_free_pages",memory.kernel_free},{"kernel_minimum_pages",memory.kernel_minimum},{"kernel_reserved_pages",memory.kernel_reserved}};
}
}
''',encoding='utf-8',newline='\n')
    ec=base['commands'][1].copy();old_view=str(Path(profile['source']['path']).parent);overlay=load(ec[ec.index('-ivfsoverlay')+1])
    for root in overlay['roots']:root['external-contents']=(a.out/Path(root['external-contents']).name).resolve().as_posix()
    view=a.out/'selected-view.private.json';save(view,overlay)
    legacy=check_legacy_policy(a.workspace,a.current,view,a.out/'legacy-policy-host-check')
    ec=[str(a.out) if x==old_view else x for x in ec];ec[ec.index('-ivfsoverlay')+1]=str(view)
    ec[ec.index('-c')+1]=str(source);ec[ec.index('-o')+1]=str(entry)
    if '-MF'in ec:ec[ec.index('-MF')+1]=str(a.out/'entry.private.d')
    sdk=a.workspace/'toolchain/ps5-sdk-radv/ps5-payload-sdk/target/include';up=a.current.parent/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569'
    provider=a.out/'early-Direct.o';target=a.workspace/'toolchain/llvm-mingw-20261006-ucrt-x86_64/bin/clang++.exe'
    tc=[str(target),'--no-default-config','--target=x86_64-sie-ps5','-nostdinc++','-isystem',str(sdk/'c++/v1'),'-isystem',str(sdk),
        '-std=c++17','-fexceptions','-fcxx-exceptions','-femulated-tls','-fno-stack-protector','-fno-plt','-fPIC','-O2',
        '-ffunction-sections','-fdata-sections','-I',str(a.out),'-I',str(ROOT/'native/app'),'-I',str(up/'vendor'),
        '-c',str(runtime),'-o',str(provider)]
    for i,command in enumerate((tc,ec)):
        result=subprocess.run(command,capture_output=True,timeout=240,env=dict(os.environ,TMP=str(a.out),TEMP=str(a.out)))
        (a.out/(str(i)+'.private.log')).write_bytes(result.stdout+result.stderr)
        need(result.returncode==0,result.stderr.decode(errors='replace')[-3500:])
    application=dict(profile,kind='headless-model-audit',entry_artifact=record(entry),source=record(source),
        overrides=dict(profile['overrides'],native_headless_model_audit=scope),model_and_GPU_topology_unchanged=False,
        headless_model_audit=True,unloaded_CPU_fixture=True,model_and_GPU_guards_preserved=True,
        headless_audit_kind=scope['kind'],headless_requests=0,actual_legacy_policy_validator_passed=True,
        native_performance_qualified=False,production_adopted=False)
    policy=a.out/'application-policy.private.json';save(policy,application)
    save(a.out/'result.private.json',dict(completed=True,application_policy=record(policy),entry=record(entry),reader=base['reader'],provider=record(provider),
        source=record(source),inputs=[record(header),record(runtime)],commands=[tc,ec],prior_close=record(a.prior_close),
        required_link_flags=['--undefined='+name for name in ('qwen_driver_table_storage','Q2_bundle_expected_identity','Q2_extra_expected_identity','Q2_current_expected_identity')],
        model_loads=0,GPU_calls=0,source_workers_created=0,PS5_operations=0,production_adopted=False))
    print(json.dumps(dict(completed=True,target_compiled=True,early_CPU_Direct_query=True,model_loads=0,GPU_calls=0,PS5_operations=0)))


if __name__=='__main__':main()
