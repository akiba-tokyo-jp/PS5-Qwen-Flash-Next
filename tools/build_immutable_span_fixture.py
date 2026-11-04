#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build a finite CPU-only Direct byte-span qualification without model/GPU work."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess

from audit_expert_all_q2_safety import body
from build_performance_quantizer import record
from build_speculative_batch_probe import once
from start_success_route import load,need,save

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','base-entry','source-proof','out'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--source-namespace',choices=('physical','application'),default='application')
    p.add_argument('--descriptor-only',action='store_true')
    a=p.parse_args();base=load(a.base_entry);proof=load(a.source_proof);profile=load(base['application_policy']['path'])
    need(base['completed'] and base['CPU_minimum_plus_21_unchanged'] and proof['completed'] and
         proof['full_native_original_SHA256_and_EOF_preserved'] and proof['bytes']>=64<<20 and len(proof['identity'])==10,
         'Selected entry and prior whole-sealed immutable Direct source required')
    for row in (base['entry'],base['reader'],profile['source']):need(record(row['path'])==row,'Selected entry input changed')
    a.out.mkdir(parents=True,exist_ok=False)
    for header in Path(profile['source']['path']).parent.glob('*.h'):shutil.copyfile(header,a.out/header.name)
    names=('immutable_span_prefetch.h','immutable_span_fixture.h','immutable_span_fixture.cpp','expert_prefetch_io.h')
    for name in names:shutil.copyfile(ROOT/'native/app'/name,a.out/name)
    physical='/data/ai/native-moss-image-sft/PPSA99190';need(proof['path'].startswith(physical+'/'),'Exact owned backing required')
    header=a.out/'immutable_span_assets.h'
    source_path=proof['path'] if a.source_namespace=='physical' else '/app0'+proof['path'][len(physical):]
    header.write_text('#pragma once\n#include <cstdint>\nstatic const char*span_source_path='+json.dumps(source_path)+';\n'+
        'static const char*span_source_namespace='+json.dumps(a.source_namespace)+';\n'+
        'static constexpr bool span_descriptor_only='+('true' if a.descriptor_only else 'false')+';\n'+
        'static const char*span_source_sha256='+json.dumps(proof['sha256'])+';\n'+
        'static constexpr std::uint64_t span_source_alias_device=688193376ULL;\n'+
        'static constexpr std::uint64_t span_source_identity[]={'+','.join(str(v)+'ULL' for v in proof['identity'])+'};\n',encoding='utf-8',newline='\n')
    original=Path(profile['source']['path']).read_text(encoding='utf-8')
    scope=dict(schema='ps5-qwen-unloaded-CPU-span-audit-v1',kind='I1-span-fixture',requests=0,model_loads=0,GPU_calls=0,
        HTTP_requests=0,VideoOut_starts=0,span_bytes=[540672,557056,475136,491520],requests_per_geometry=8,
        maximum_predictions_per_request=6,source_SHA256=proof['sha256'],prior_whole_seal_with_fresh_descriptor_identity=True,
        source_namespace=a.source_namespace,descriptor_only=a.descriptor_only,known_returned_open_refusal_reported_after_positive_close=True,
        source_device_bound_to_same_launch_title_directory=True,source_link_count_zero_or_one_preserved=True,
        payload_writes=0,performance_timings_usable=False)
    text='#include "immutable_span_fixture.h"\n'+original
    marker='        const auto policy = Json::parse(policy_file);'
    text=once(text,marker,marker+'\n        if(policy.at("native_headless_model_audit")!=Json::parse('+json.dumps(json.dumps(scope,separators=(',',':')))+'))throw std::runtime_error("Exact unloaded CPU span scope required");')
    marker='\n        qwen_native_gpu_initialize((startup.admission_report+".driver.log").c_str());\n'
    need(text.count(marker)==1,'One actual measured GPU phase entry required')
    start=text.index(marker);end=text.index('    }catch(const std::exception &e){',start)
    text=text[:start]+'''
        qwen_app::enforce_native_model_compute_limits();
        if(qwen_app::native_model_device_stats().live)throw std::runtime_error("Empty CPU fixture ledger required");
        resident_worker_completion_unknown=true;
        auto audit=qwen_app::run_immutable_span_fixture(qwen_native_stage,
            policy.at("native_first_generation_validation").at("candidate_SELF_bytes").get<std::uint64_t>());
        resident_worker_completion_unknown=false;
        const auto source=qwen_app::native_model_source_stats();
        if(source.chunks!=source.completed_windows)throw std::runtime_error("CPU fixture original source windows remain incomplete");
        qwen_app::stop_native_model_sources();const auto ledger=qwen_app::native_model_device_stats();
        if(ledger.live)throw std::runtime_error("CPU fixture device ledger must remain empty");
        const auto run=policy.at("native_first_generation_validation").at("run_id").get<std::string>();
        audit.update({{"pid",getpid()},{"run_id",run},{"candidate_SELF_sha256",policy.at("native_first_generation_validation").at("candidate_SELF_sha256")}});
        write_fresh_report(startup.admission_report+".audit",audit);
        struct ps5_heap_stats heap{};ps5_heap_stats(&heap);
        write_fresh_report(startup.admission_report,{{"schema","ps5-qwen-unloaded-CPU-span-completion-v1"},{"kind","I1-span-fixture"},
            {"completed",true},{"pid",getpid()},{"run_id",run},{"candidate_SELF_sha256",policy.at("native_first_generation_validation").at("candidate_SELF_sha256")},
            {"model_receipt_sha256",policy.at("native_first_generation_validation").at("model_receipt_sha256")},
            {"requests",Json::array()},{"model_loads",0},{"HTTP_requests",0},{"VideoOut_starts",0},
            {"audit",audit},{"source_windows",source.chunks},{"source_completed_windows",source.completed_windows},
            {"all_model_source_device_owners_positively_retired",true},{"device_ledger_live_bytes",ledger.live},
            {"device_ledger_peak_bytes",ledger.peak},{"CPU_heap_peak_bytes",heap.peak_bytes},{"GPU_calls",0}});
        qwen_native_stage("resident_additional_completed_waiting_for_ordinary_close");
        for(;;)(void)usleep(1000000);
'''+text[end:]
    for name in ('observed_system_headroom','require_model_CPU_budget','wait_for_initial_model_CPU_budget','model_file_identity','model_directory_identity'):
        need(body(original,name)==body(text,name),'An original memory or identity guard changed')
    source=a.out/'entry.private.cpp';source.write_text(text,encoding='utf-8',newline='\n');obj=a.out/'entry.o'
    ec=base['commands'][1].copy();old_view=str(Path(profile['source']['path']).parent)
    overlay=load(ec[ec.index('-ivfsoverlay')+1])
    for root in overlay['roots']:root['external-contents']=(a.out/Path(root['external-contents']).name).resolve().as_posix()
    selected=a.out/'selected-view.private.json';save(selected,overlay)
    ec=[str(a.out) if x==old_view else x for x in ec];ec[ec.index('-ivfsoverlay')+1]=str(selected)
    ec[ec.index('-c')+1]=str(source);ec[ec.index('-o')+1]=str(obj)
    if '-MF'in ec:ec[ec.index('-MF')+1]=str(a.out/'entry.private.d')
    sdk=a.workspace/'toolchain/ps5-sdk-radv/ps5-payload-sdk/target/include'
    up=a.current.parent/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569'
    target=a.workspace/'toolchain/llvm-mingw-20261006-ucrt-x86_64/bin/clang++.exe';provider=a.out/'immutable-span.o'
    tc=[str(target),'--no-default-config','--target=x86_64-sie-ps5','-nostdinc++','-isystem',str(sdk/'c++/v1'),'-isystem',str(sdk),
        '-std=c++17','-fexceptions','-fcxx-exceptions','-femulated-tls','-fno-stack-protector','-fno-plt','-fPIC','-O2',
        '-ffunction-sections','-fdata-sections','-I',str(a.out),'-I',str(ROOT/'native/app'),'-I',str(up/'vendor'),
        '-c',str(a.out/'immutable_span_fixture.cpp'),'-o',str(provider)]
    for i,command in enumerate((tc,ec)):
        result=subprocess.run(command,capture_output=True,timeout=240,env=dict(os.environ,TMP=str(a.out),TEMP=str(a.out)))
        (a.out/(str(i)+'.private.log')).write_bytes(result.stdout+result.stderr)
        need(result.returncode==0,result.stderr.decode(errors='replace')[-4000:])
    application=dict(profile,kind='headless-model-audit',entry_artifact=record(obj),source=record(source),
        overrides=dict(profile['overrides'],native_headless_model_audit=scope),model_and_GPU_topology_unchanged=False,
        headless_model_audit=True,unloaded_CPU_fixture=True,model_and_GPU_guards_preserved=True,
        headless_audit_kind=scope['kind'],headless_requests=0,native_performance_qualified=False,production_adopted=False)
    policy=a.out/'application-policy.private.json';save(policy,application)
    save(a.out/'result.private.json',dict(completed=True,application_policy=record(policy),entry=record(obj),reader=base['reader'],
        provider=record(provider),source=record(source),inputs=[record(a.out/name) for name in names]+[record(header)],
        source_proof=record(a.source_proof),commands=[tc,ec],model_loads=0,GPU_calls=0,PS5_operations=0,production_adopted=False))
    print(json.dumps(dict(completed=True,target_compiled=True,model_loads=0,GPU_calls=0,PS5_operations=0)))


if __name__=='__main__':main()
