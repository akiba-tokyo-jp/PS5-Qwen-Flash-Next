#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build one unchanged model request with bounded read-only original pread records."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess

from audit_expert_all_q2_safety import body
from build_performance_quantizer import record
from build_speculative_batch_probe import once
from check_headless_legacy_policy import check as check_legacy_policy
from headless_current_entry import headless_entry
from start_success_route import load,need,save

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','base-entry','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();base=load(a.base_entry);profile=load(base['application_policy']['path'])
    need(base['completed'] and base['CPU_minimum_plus_21_unchanged'],'Exact selected guarded entry required')
    for row in (base['entry'],base['reader'],profile['source']):need(record(row['path'])==row,'Selected input changed')
    a.out.mkdir(parents=True,exist_ok=False)
    for header in Path(profile['source']['path']).parent.glob('*.h'):shutil.copyfile(header,a.out/header.name)
    names=('model_pread_observation.h','model_pread_observation_runtime.h','model_pread_observation_runtime.cpp')
    for name in names:shutil.copyfile(ROOT/'native/app'/name,a.out/name)
    original=Path(profile['source']['path']).read_text(encoding='utf-8')
    scope=dict(schema='ps5-qwen-original-model-pread-observation-v1',kind='I1-model-pread-observation',requests=1,model_loads=1,
        HTTP_requests=0,VideoOut_starts=0,original_pread_forwarded_exactly_once=True,original_errno_preserved=True,
        source_payload_bytes_inspected=0,additional_workers=0,additional_source_opens=0,GPU_calls_added=0,
        candidate_minimum_bytes=256<<10,candidate_maximum_bytes=8<<20,candidate_alignment=16384,maximum_records=32768,
        full_descriptor_identity_before_and_after=True,record_bytes=288,maximum_CPU_trace_bytes=32768*288,
        predictions_submitted=0,performance_timings_usable=False)
    text='#include "model_pread_observation_runtime.h"\n'+original
    marker='        const auto policy = Json::parse(policy_file);'
    text=once(text,marker,marker+'\n        if(policy.at("native_headless_model_audit")!=Json::parse('+json.dumps(json.dumps(scope,separators=(',',':')))+'))throw std::runtime_error("Exact original model read observation scope required");')
    marker='            const auto &result=trial.run(request,'
    text=once(text,marker,'            qwen_app::begin_model_pread_observation();require_model_CPU_budget();\n'+marker)
    marker='            engine->set_work_guard({});engine->set_logits_observer({});qwen_app_complete_predictive_expert();'
    text=once(text,marker,marker+'\n            qwen_app::stop_model_pread_observation_after_request_completion();')
    export='qwen_app::export_model_pread_observation_after_owner_retirement(startup.admission_report+".pread-trace",{{"run_id",run},{"pid",getpid()},{"candidate_SELF_sha256",policy.at("native_first_generation_validation").at("candidate_SELF_sha256")},{"model_receipt_sha256",policy.at("native_first_generation_validation").at("model_receipt_sha256")}})'
    text=headless_entry(text,scope['kind'],1,export,retain_reference=False)
    for name in ('observed_system_headroom','require_model_CPU_budget','wait_for_initial_model_CPU_budget',
                 'model_file_identity','model_directory_identity','resident_reset_empty_context'):
        need(body(original,name)==body(text,name),'An original physical, CPU, identity or reset guard changed')
    source=a.out/'entry.private.cpp';source.write_text(text,encoding='utf-8',newline='\n');entry=a.out/'entry.o'
    ec=base['commands'][1].copy();old_view=str(Path(profile['source']['path']).parent);overlay=load(ec[ec.index('-ivfsoverlay')+1])
    for root in overlay['roots']:root['external-contents']=(a.out/Path(root['external-contents']).name).resolve().as_posix()
    view=a.out/'selected-view.private.json';save(view,overlay)
    legacy=check_legacy_policy(a.workspace,a.current,view,a.out/'legacy-policy-host-check')
    ec=[str(a.out) if x==old_view else x for x in ec];ec[ec.index('-ivfsoverlay')+1]=str(view)
    ec[ec.index('-c')+1]=str(source);ec[ec.index('-o')+1]=str(entry)
    if '-MF'in ec:ec[ec.index('-MF')+1]=str(a.out/'entry.private.d')
    up=a.current.parent/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569';sdk=a.workspace/'toolchain/ps5-sdk-radv/ps5-payload-sdk/target/include'
    host=a.workspace/'toolchain/msys-clang64/clang64/bin';target=a.workspace/'toolchain/llvm-mingw-20261006-ucrt-x86_64/bin/clang++.exe'
    provider=a.out/'model-pread-observation.o';test=a.out/'model-pread-test.exe'
    tc=[str(target),'--no-default-config','--target=x86_64-sie-ps5','-nostdinc++','-isystem',str(sdk/'c++/v1'),'-isystem',str(sdk),
        '-std=c++17','-fexceptions','-fcxx-exceptions','-femulated-tls','-fno-stack-protector','-fno-plt','-fPIC','-O2',
        '-ffunction-sections','-fdata-sections','-Wall','-Wextra','-Werror','-I',str(a.out),'-I',str(up/'vendor'),
        '-c',str(a.out/'model_pread_observation_runtime.cpp'),'-o',str(provider)]
    hc=[str(host/'clang++.exe'),'-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(a.out),
        str(ROOT/'tests/model_pread_observation_test.cpp'),'-o',str(test)]
    commands=[hc,[str(test)],tc,ec];env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''),TMP=str(a.out),TEMP=str(a.out))
    for i,command in enumerate(commands):
        result=subprocess.run(command,capture_output=True,timeout=240,env=env);(a.out/(str(i)+'.private.log')).write_bytes(result.stdout+result.stderr)
        need(result.returncode==0,result.stderr.decode(errors='replace')[-3500:])
    application=dict(profile,kind='headless-model-audit',entry_artifact=record(entry),source=record(source),
        overrides=dict(profile['overrides'],native_headless_model_audit=scope),model_and_GPU_topology_unchanged=False,
        headless_model_audit=True,model_and_GPU_guards_preserved=True,headless_audit_kind=scope['kind'],headless_requests=1,
        actual_legacy_policy_validator_passed=True,legacy_policy_host_check=record(a.out/'legacy-policy-host-check/result.private.json'),
        native_performance_qualified=False,production_adopted=False)
    policy=a.out/'application-policy.private.json';save(policy,application)
    save(a.out/'result.private.json',dict(completed=True,application_policy=record(policy),entry=record(entry),reader=base['reader'],
        provider=record(provider),source=record(source),inputs=[record(a.out/name) for name in names],commands=commands,
        required_link_flags=['--wrap=pread'],host_multithread_errno_short_read_identity_and_overflow_controls_passed=True,
        model_loads=0,GPU_calls=0,PS5_operations=0,native_model_trace_qualified=False,production_adopted=False))
    print(json.dumps(dict(completed=True,target_compiled=True,host_original_IO_controls_passed=True,PS5_operations=0)))


if __name__=='__main__':main()
