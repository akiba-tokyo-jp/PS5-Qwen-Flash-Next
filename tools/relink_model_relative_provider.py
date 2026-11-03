#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Relink only a corrected native source provider; reuse the exact controlled entry."""
import argparse
import copy
import json
import os
from pathlib import Path
import subprocess
from audit_native_imports import audit
from build_performance_quantizer import record
from start_success_route import load,need,save
ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','prior','provider','out'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--resume',action='store_true',help='Reuse only completed immutable SELF arms; never repeat their relink/formatting')
    a=p.parse_args();old=load(a.prior);provider=load(a.provider);original=load(old['provider']['path'])
    need(old['completed'] and old['new_scope_controls']==dict(positive=2,negative=12) and provider['completed'] and
        provider['new_global_constructors']==0 and provider['controls']==original['controls'] and
        all(record(old[k]['path'])==old[k] for k in ('source','entry','scope_header','scope_test')) and
        record(provider['artifact']['path'])==provider['artifact'],'Exact new provider and unchanged controlled entry required')
    previous={Path(r['path']).name:r for r in original['inputs']};current={Path(r['path']).name:r for r in provider['inputs']}
    for name in previous:
        if name!='model_relative_prefetch_runtime.cpp':need(previous[name]['sha256']==current[name]['sha256'],'An unchanged provider dependency differs')
    left=Path(previous['model_relative_prefetch_runtime.cpp']['path']).read_text()
    right=Path(current['model_relative_prefetch_runtime.cpp']['path']).read_text()
    before='#include "system_memory.h"'
    after='''// Keep this stricter read-only helper separate from the selected frontend's
// phase-aware inline function; never contribute a conflicting definition.
#define qualified_system_headroom relative_prefetch_qualified_system_headroom
#include "system_memory.h"
#undef qualified_system_headroom'''
    need(left.replace(before,after,1).replace('qualified_system_headroom(observe_native_system_memory())',
        'relative_prefetch_qualified_system_headroom(observe_native_system_memory())',1)==right,
        'Only the uniquely named stricter read-only helper may change')
    if a.resume:need(a.out.is_dir() and not(a.out/'result.private.json').exists(),'Only an incomplete host build may resume')
    else:a.out.mkdir(parents=True,exist_ok=False)
    packages={};commands=[];old_root=Path(a.prior).parent;reused=0
    def run(job,label):
        commands.append(job);result=subprocess.run(job,capture_output=True,timeout=240,env=dict(os.environ,TMP=str(a.out),TEMP=str(a.out)))
        (a.out/(label+'.private.log')).write_bytes(result.stdout+result.stderr)
        need(not result.returncode,(result.stdout+result.stderr).decode(errors='replace')[-4000:])
    for arm in ('control','candidate'):
        profile=load(old_root/(arm+'-policy.private.json'));profile['I1_relative_provider']=record(a.provider)
        policy=a.out/(arm+'-policy.private.json')
        if policy.exists():need(a.resume and load(policy)==profile,'The previous controlled policy changed')
        else:save(policy,profile)
        expected=str(old_root/(arm+'-link'))
        job=next(job for job in old['commands'] if any(str(value).endswith('relink_retained_current.py') for value in job) and expected in job).copy()
        job=[str(policy) if value==str(old_root/(arm+'-policy.private.json')) else
             str(a.out/(arm+'-link')) if value==expected else
             provider['artifact']['path'] if value==original['artifact']['path'] else value for value in job]
        completed_arm=a.resume and (a.out/(arm+'-SELF/result.private.json')).exists()
        if not completed_arm:run(job,arm+'-link')
        package_job=next(job for job in old['commands'] if any(str(value).endswith('package_retained_current.py') for value in job) and str(old_root/(arm+'-SELF')) in job).copy()
        package_job=[str(a.out/(arm+'-SELF')) if value==str(old_root/(arm+'-SELF')) else
            str(a.out/(arm+'-link/result.private.json')) if value==str(old_root/(arm+'-link/result.private.json')) else value for value in package_job]
        if not completed_arm:run(package_job,arm+'-SELF')
        else:
            done=load(a.out/(arm+'-SELF/result.private.json'))
            need(done['completed'] and done['normalized_SELF_roundtrip_equal'] and record(done['SELF']['path'])==done['SELF'] and
                done['effective_application_policy']['profile']==record(policy),'Exact completed controlled arm required')
            reused+=1
        linked=load(a.out/(arm+'-link/result.private.json'));native_inputs=linked['inputs']+linked['new_inputs']
        full=load(a.current/'provenance/native-link.receipt.private.json')
        for stub in full['formatter_stubs']:
            if stub['path'].endswith('.so') and not Path(stub['path']).name.endswith('_stub_weak.so'):
                need(record(stub['path'])==stub,'Actual real-module formatter provider changed');native_inputs.append(stub)
        check=a.out/(arm+'-imports-with-real-providers');check.mkdir()
        save(check/'receipt.private.json',dict(artifact=linked['artifact'],inputs_before=native_inputs,runtime_providers=full['runtime_providers']))
        imported=audit(a.workspace,a.current.parent,check)
        need(not imported['missing'],'Every actual newly linked source/thread/native import must resolve: '+str(imported['missing']))
        packages[arm]=record(a.out/(arm+'-SELF/result.private.json'))
    save(a.out/'result.private.json',dict(completed=True,prior=record(a.prior),provider=record(a.provider),packages=packages,
        entry=old['entry'],source=old['source'],scope_header=old['scope_header'],scope_test=old['scope_test'],
        new_scope_controls=old['new_scope_controls'],commands=commands,F32_qualification=old['F32_qualification'],
        source_guard_unique_namespace=True,original_frontend_guard_not_redefined=True,
        old_entry_and_host_controls_reused_without_replay=True,actual_imports_resolved_both_arms=True,
        completed_host_SELF_arms_reused_without_relink=reused,
        original_native_guards_unchanged=True,PS5_operations=0,native_qualified=False,production_adopted=False))
    print(dict(completed=True,packages=2,entry_recompilations=0,old_host_tests_replayed=0,PS5_operations=0))


if __name__=='__main__':main()
