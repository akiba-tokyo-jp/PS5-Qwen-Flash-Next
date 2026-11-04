#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Connect the qualified bounded source runtime to the unchanged three-request model."""
import argparse
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from audit_expert_all_q2_safety import body
from build_performance_quantizer import record
from build_speculative_batch_probe import once
from headless_current_entry import headless_entry
from start_success_route import load,need,save
ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','provider','out'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--F32-observer',type=Path)
    p.add_argument('--reuse-scope-controls',type=Path,help='Reuse the exact already completed scope body and controls')
    p.add_argument('--resume-precompile',action='store_true',help='Resume only a host failure before any entry source/object was produced')
    a=p.parse_args();provider=load(a.provider)
    need(provider['completed'] and provider['new_global_constructors']==0 and provider['actual_native_pread_offset_bytes']==8 and
        record(provider['artifact']['path'])==provider['artifact'] and all(record(r['path'])==r for r in provider['inputs']),
        'Actual native source ABI and frozen concurrent runtime required')
    controls=load(provider['controls']['path']);need(record(provider['controls']['path'])==provider['controls'] and controls['new_concurrent_controls']==9,
        'All actual concurrency and read-only worker-admission controls must be bound')
    selected=load(a.current/'provenance/selected-entry-build.private.json');original=load(selected['application_policy']['path'])
    need(record(original['source']['path'])==original['source'],'The selected original source changed')
    a.out.mkdir(parents=True,exist_ok=a.resume_precompile);old_dir=Path(original['source']['path']).parent
    if a.resume_precompile:need(not(a.out/'entry.private.cpp').exists() and not(a.out/'entry.o').exists() and
        not(a.out/'result.private.json').exists(),'A completed entry compilation must not be replayed')
    for header in old_dir.glob('*.h'):shutil.copyfile(header,a.out/header.name)
    for name in ('model_relative_prefetch_runtime.h','model_relative_prefetch_scope.h'):
        shutil.copyfile(ROOT/'native/app'/name,a.out/name)
    host=a.workspace/'toolchain/msys-clang64/clang64/bin';up=a.current.parent/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569'
    exe=a.out/'scope-check.exe';test=ROOT/'tests/model_relative_prefetch_scope_test.cpp'
    env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''),TMP=str(a.out),TEMP=str(a.out));commands=[]
    def run(job,label):
        job=list(map(str,job));commands.append(job);result=subprocess.run(job,capture_output=True,timeout=240,env=env)
        (a.out/(label+'.private.log')).write_bytes(result.stdout+result.stderr)
        need(not result.returncode,(result.stdout+result.stderr).decode(errors='replace')[-4000:]);return result.stdout
    if a.reuse_scope_controls:
        prior=load(a.reuse_scope_controls)
        need(prior['completed'] and prior['new_scope_controls']==dict(positive=2,negative=12) and
             record(prior['scope_header']['path'])==prior['scope_header'] and
             record(prior['scope_test']['path'])==prior['scope_test'] and
             record(test)==prior['scope_test'] and
             record(a.out/'model_relative_prefetch_scope.h')['sha256']==prior['scope_header']['sha256'],
             'Only the identical completed scope body and controls may be reused')
        origin=a.reuse_scope_controls;seen=set()
        while not(origin.parent/'scope-controls.private.log').exists():
            need(str(origin) not in seen and len(seen)<8,'One finite immutable scope-control ancestry required');seen.add(str(origin))
            ancestor=load(origin)['completed_scope_controls_reused']
            need(record(ancestor['path'])==ancestor,'The actual completed original controls changed');origin=Path(ancestor['path'])
        scopes=load(origin.parent/'scope-controls.private.log')
    else:
        run([host/'clang++.exe','-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',a.out,'-I',up/'vendor',test,'-o',exe],'scope-compile')
        scopes=json.loads(run([exe],'scope-controls'))
    need(scopes['positive_controls']==2 and scopes['negative_controls']==12,'All exact scope controls required')
    baseline=Path(original['source']['path']).read_text(encoding='utf-8')
    text='#include "model_relative_prefetch_runtime.h"\n#include "model_relative_prefetch_scope.h"\n'+baseline
    marker='        const auto policy = Json::parse(policy_file);'
    text=once(text,marker,marker+'\n        const bool relative_prefetch_enabled=qwen_app::require_model_relative_prefetch_scope(policy.at("native_headless_model_audit"));')
    marker='            const auto &result=trial.run(request,'
    prepare='''            const auto relative_request_started=qwen_app::ProfileClock::now();
            if(!ordinal)qwen_app::prepare_model_relative_prefetch(relative_prefetch_enabled,[](std::size_t bytes){
                if(bytes>(2u<<20))return false;
                try {
                    require_model_CPU_budget();
                    struct ps5_heap_stats heap{};ps5_heap_stats(&heap);
                    const auto pool=sceKernelGetDirectMemorySize();std::int64_t start=-1;std::size_t available=0;
                    if(pool<=0||sceKernelAvailableDirectMemorySize(0,pool,65536,&start,&available)||start<0||
                       heap.mapped_bytes>qwen_app::maximum_model_CPU_heap_bytes||
                       available<qwen_app::maximum_model_CPU_heap_bytes-heap.mapped_bytes+(256ull<<20))return false;
                    return observed_system_headroom()>=qwen_app::model_read_system_reserve+qwen_app::model_read_flexible_metadata_margin;
                }catch(...){return false;}
            },qwen_app::maximum_model_CPU_heap_bytes,qwen_app::model_read_system_reserve+qwen_app::model_read_flexible_metadata_margin);
            qwen_app::begin_model_relative_prefetch_request();
'''
    text=once(text,marker,prepare+marker)
    marker='            engine->set_work_guard({});engine->set_logits_observer({});qwen_app_complete_predictive_expert();'
    text=once(text,marker,marker+'\n            const auto relative_prefetch_request=qwen_app::finish_model_relative_prefetch_request();\n            const double relative_complete_span_ms=double(qwen_app::profile_elapsed_ns(relative_request_started))/1e6;')
    text=headless_entry(text,'I1-relative-model-prefetch',3,'qwen_app::retire_model_relative_prefetch_after_original_owners()')
    marker='            completed.push_back(row);write_fresh_report(report_prefix+".result",row);'
    text=once(text,marker,'            row["relative_prefetch"]=relative_prefetch_request;\n            row["complete_request_including_relative_setup_and_drain_ms"]=relative_complete_span_ms;\n'+marker)
    need(text.index('row["relative_prefetch"]=')<text.index('completed.push_back(row);') and
         text.index('row["complete_request_including_relative_setup_and_drain_ms"]=')<text.index('completed.push_back(row);'),
         'Actual request counters must enter the durable result and terminal snapshot')
    if not a.F32_observer:text=once(text,'{"timings_usable_for_performance",false}','{"timings_usable_for_performance",true}')
    for name in ('observed_system_headroom','require_model_CPU_budget','wait_for_initial_model_CPU_budget',
        'model_file_identity','model_directory_identity','resident_reset_empty_context','bind_resident_main_SELF'):
        need(body(baseline,name)==body(text,name),'An original physical, CPU, identity, reset or SELF guard changed')
    source=a.out/'entry.private.cpp';source.write_text(text,encoding='utf-8',newline='\n');entry=a.out/'entry.o'
    ec=next(job for job in selected['commands'] if '-c' in job and job[job.index('-c')+1].endswith('entry.private.cpp')).copy()
    overlay=load(ec[ec.index('-ivfsoverlay')+1])
    for root in overlay['roots']:
        candidate=a.out/Path(root['external-contents']).name
        if candidate.exists():root['external-contents']=candidate.resolve().as_posix()
    view=a.out/'selected-view.private.json';save(view,overlay)
    ec=[str(a.out) if value==str(old_dir) else value for value in ec];ec[1:1]=['-I',str(a.out)]
    ec[ec.index('-ivfsoverlay')+1]=str(view);ec[ec.index('-c')+1]=str(source);ec[ec.index('-o')+1]=str(entry)
    if '-MF' in ec:ec[ec.index('-MF')+1]=str(a.out/'entry.private.d')
    run(ec,'entry-compile');observer=load(a.F32_observer) if a.F32_observer else None
    if observer:need(observer['completed'] and observer['qualification_only'] and record(observer['artifact']['path'])==observer['artifact'],'The unchanged full F32 observer is required')
    identity=load(a.current/'provenance/current-package.private.json')['required_bundle_identity_audit']['provider']
    packages={}
    for arm in ('control','candidate'):
        scope=scopes[arm];profile=copy.deepcopy(original)
        profile.update(kind='headless-model-audit',entry_artifact=record(entry),source=record(source),
            headless_model_audit=True,headless_audit_kind=scope['kind'],headless_requests=3,
            model_and_GPU_topology_unchanged=False,model_and_GPU_guards_preserved=True,
            overrides=dict(original['overrides'],native_headless_model_audit=scope),I1_arm=arm,
            I1_relative_provider=record(a.provider),performance_timings_usable=not bool(observer),
            native_performance_qualified=False,production_adopted=False)
        policy=a.out/(arm+'-policy.private.json');save(policy,profile)
        flags=provider['required_link_flags']+(observer['link_flags'] if observer else [])
        job=[sys.executable,'-B',ROOT/'tools/relink_retained_current.py','--current',a.current,'--out',a.out/(arm+'-link'),
            '--replace','entry.o='+str(entry),'--replace','early-SELF.o='+original['CPU_SELF_provider']['artifact']['path'],
            '--add-object',provider['artifact']['path'],'--application-policy',policy]+['--link-flag='+flag for flag in flags]
        if observer:job+=['--add-object',observer['artifact']['path']]
        run(job,arm+'-link')
        run([sys.executable,'-B',ROOT/'tools/package_retained_current.py','--workspace',a.workspace,'--current',a.current,
            '--relink',a.out/(arm+'-link/result.private.json'),'--out',a.out/(arm+'-SELF'),
            '--formatter-from',a.current/'provenance/current-package.private.json','--identity-provider',identity['path']],arm+'-SELF')
        packages[arm]=record(a.out/(arm+'-SELF/result.private.json'))
    save(a.out/'result.private.json',dict(completed=True,entry=record(entry),source=record(source),provider=record(a.provider),
        new_scope_controls=dict(positive=2,negative=12),scope_header=record(a.out/'model_relative_prefetch_scope.h'),
        scope_test=record(test),packages=packages,commands=commands,original_native_guards_unchanged=True,
        unchanged_legacy_policy_header_view_reused=True,F32_qualification=bool(observer),
        completed_scope_controls_reused=record(a.reuse_scope_controls) if a.reuse_scope_controls else None,
        old_predictor_IO_and_model_tests_replayed=0,native_qualified=False,production_adopted=False,PS5_operations=0))
    print(dict(completed=True,model_packages=2,F32_qualification=bool(observer),new_scope_controls=0 if a.reuse_scope_controls else 14,PS5_operations=0))


if __name__=='__main__':main()
