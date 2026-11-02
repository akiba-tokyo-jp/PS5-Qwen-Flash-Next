#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build matched controls for deferring only completed inference journal syncs."""
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
PREFIX='''#include "completed_stage_sync.h"
namespace {
std::atomic<bool> completed_stage_request{false},completed_stage_deferral{false};
std::atomic<std::uint64_t> completed_stage_totals[4]{};
}
extern "C" void qwen_native_begin_completed_stage_sync(bool enabled) {
    if(completed_stage_request.exchange(true))stop_bootstrap("nested_completed_stage_request");
    completed_stage_deferral.store(enabled,std::memory_order_release);
}
extern "C" void qwen_native_finish_completed_stage_sync() {
    if(!completed_stage_request.load())stop_bootstrap("missing_completed_stage_request");
    if(completed_stage_deferral.exchange(false)) {
        if(journal<0||fsync(journal))stop_bootstrap("completed_request_stage_sync_failed");
        completed_stage_totals[3].fetch_add(1);
    }
    completed_stage_request.store(false);
}
extern "C" void qwen_native_completed_stage_sync_stats(std::uint64_t *out) {
    for(unsigned i=0;i<4;++i)out[i]=completed_stage_totals[i].load();
}
'''
DECLARATIONS='''#include <cstdint>
extern "C" void qwen_native_begin_completed_stage_sync(bool);
extern "C" void qwen_native_finish_completed_stage_sync();
extern "C" void qwen_native_completed_stage_sync_stats(std::uint64_t*);
'''


def transform_bootstrap(text):
    marker='extern "C" void qwen_native_stage(const char * stage) {'
    text=once(text,marker,PREFIX+'\n'+marker)
    old='    if(fsync(journal))stop_bootstrap("bootstrap_stage_persist_failed");'
    replacement='''    const bool deferred=completed_stage_deferral.load(std::memory_order_acquire)&&
        !probe_enabled.load(std::memory_order_acquire)&&qwen_app::completed_inference_stage(stage);
    completed_stage_totals[0].fetch_add(1);
    if(deferred)completed_stage_totals[2].fetch_add(1);
    else {
        if(fsync(journal))stop_bootstrap("bootstrap_stage_persist_failed");
        completed_stage_totals[1].fetch_add(1);
    }'''
    return once(text,old,replacement)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','base-entry','bootstrap','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();base=load(a.base_entry);boot=load(a.bootstrap)
    need(base['completed'] and base['CPU_minimum_plus_21_unchanged'] and boot['completed'],'Exact admitted inputs required')
    profile=load(base['application_policy']['path'])
    need('completed_stage_deferral_enabled' not in profile,'Completed-stage sync is already selected; do not apply the transformation twice')
    for row in (profile['source'],boot['source'],boot['exact_object']['artifact']):need(record(row['path'])==row,'Selected source or object changed')
    a.out.mkdir(parents=True,exist_ok=False)
    env=dict(os.environ,TMP=str(a.out),TEMP=str(a.out))
    host=a.workspace/'toolchain/msys-clang64/clang64/bin';test=a.out/'completed-stage-test.exe'
    command=[str(host/'clang++.exe'),'-std=c++17','-O2','-I',str(ROOT/'native/app'),
        str(ROOT/'tests/completed_stage_sync_test.cpp'),'-o',str(test)]
    result=subprocess.run(command,capture_output=True,timeout=120,env=env)
    (a.out/'host-compile.private.log').write_bytes(result.stdout+result.stderr);need(result.returncode==0,result.stderr.decode(errors='replace')[-2500:])
    need(subprocess.run([str(test)],env=dict(env,PATH=str(host)+os.pathsep+os.environ.get('PATH','')),timeout=30).returncode==0,'Durable-boundary refusal controls failed')
    text=Path(boot['source']['path']).read_text(encoding='utf-8')
    text=transform_bootstrap(text)
    boot_source=a.out/'native-bootstrap-completed-stage.private.cpp';boot_source.write_text(text,encoding='utf-8',newline='\n')
    bc=boot['exact_object']['command'].copy();bo=a.out/'native-bootstrap-completed-stage.o'
    bc[bc.index('-c')+1]=str(boot_source);bc[bc.index('-o')+1]=str(bo)
    result=subprocess.run(bc,capture_output=True,timeout=120,env=env)
    (a.out/'bootstrap-compile.private.log').write_bytes(result.stdout+result.stderr);need(result.returncode==0,result.stderr.decode(errors='replace')[-2500:])
    original=Path(profile['source']['path']).read_text(encoding='utf-8');scope=profile['overrides']['native_next_five_normal']
    literal=lambda value:json.dumps(json.dumps(value,separators=(',',':')))
    need(original.count(literal(scope))==3,'All three selected scope reports required')
    variants={}
    for label,enabled in (('control',False),('candidate',True)):
        folder=a.out/label;folder.mkdir()
        for header in Path(profile['source']['path']).parent.glob('*.h'):shutil.copyfile(header,folder/header.name)
        changed=dict(scope,completed_stage_deferral_enabled=enabled,all_before_operation_stages_synced=True,
            completed_request_stage_journal_synced_before_result=True,interrupted_request_may_lose_completed_stage_tail=enabled)
        entry=DECLARATIONS+original.replace(literal(scope),literal(changed))
        entry=once(entry,'            qwen_load::CpuSpan measured_run(qwen_load::request_run);',
            '            std::uint64_t journal_before[4]{};qwen_native_completed_stage_sync_stats(journal_before);\n'
            '            qwen_native_begin_completed_stage_sync('+str(enabled).lower()+');\n'
            '            qwen_load::CpuSpan measured_run(qwen_load::request_run);')
        entry=once(entry,'token_ledger.close();}measured_run.end();',
            'token_ledger.close();}qwen_native_finish_completed_stage_sync();measured_run.end();')
        entry=once(entry,'            row["complete_request_span_ms"]=complete_request_span_ms;',
            '            std::uint64_t journal_after[4]{};qwen_native_completed_stage_sync_stats(journal_after);\n'
            '            for(unsigned j=0;j<4;++j)journal_after[j]-=journal_before[j];\n'
            '            row["stage_journal_write_sync_deferred_request_flush_calls"]=std::vector<std::uint64_t>(journal_after,journal_after+4);\n'
            '            row["complete_request_span_ms"]=complete_request_span_ms;')
        for name in ('observed_system_headroom','require_model_CPU_budget','wait_for_initial_model_CPU_budget',
                     'model_file_identity','model_directory_identity','resident_reset_empty_context'):
            need(body(original,name)==body(entry,name),'An unrelated memory, identity or reset guard changed')
        source=folder/'entry.private.cpp';source.write_text(entry,encoding='utf-8',newline='\n');obj=folder/'entry.o'
        command=base['commands'][1].copy();view=load(command[command.index('-ivfsoverlay')+1])
        for root in view['roots']:root['external-contents']=(folder/Path(root['external-contents']).name).resolve().as_posix()
        selected=folder/'selected-view.private.json';save(selected,view)
        command=[str(folder) if x==str(Path(profile['source']['path']).parent) else x for x in command]
        command[command.index('-ivfsoverlay')+1]=str(selected);command[command.index('-c')+1]=str(source);command[command.index('-o')+1]=str(obj)
        if '-MF'in command:command[command.index('-MF')+1]=str(folder/'entry.private.d')
        result=subprocess.run(command,capture_output=True,timeout=240,env=env)
        (folder/'compile.private.log').write_bytes(result.stdout+result.stderr);need(result.returncode==0,result.stderr.decode(errors='replace')[-2500:])
        current=dict(profile,entry_artifact=record(obj),source=record(source),
            overrides=dict(profile['overrides'],native_next_five_normal=changed),native_performance_qualified=False)
        current['stage_sync_provider']=record(bo);current['completed_stage_deferral_enabled']=enabled
        path=folder/'application-policy.private.json';save(path,current)
        variants[label]=dict(entry=record(obj),source=record(source),profile=record(path),command=command)
    save(a.out/'result.private.json',dict(completed=True,variants=variants,bootstrap=record(bo),bootstrap_source=record(boot_source),
        bootstrap_command=bc,classifier=record(ROOT/'native/app/completed_stage_sync.h'),
        exact_parent_bootstrap=record(a.bootstrap),host_durable_boundary_controls_passed=True,
        before_unknown_fatal_and_probe_stages_always_synced=True,final_request_flush_in_complete_span=True,
        PS5_operations=0,native_speed_or_quality_qualified=False,production_adopted=False))
    print(json.dumps(dict(completed=True,paired_target_entry_and_bootstrap_compiled=True,PS5_operations=0)))


if __name__=='__main__':main()
