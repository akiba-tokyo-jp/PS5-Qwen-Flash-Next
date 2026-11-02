#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build a finite persistent MTP request using the qualified target completion hook."""
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
from mtp_shadow_host_check import require_target_capture_profile
from start_success_route import load,need,save

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','parent','capture-proof','out'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--force-one-wrong-draft',action='store_true');a=p.parse_args()
    parent=load(a.parent);profile=load(parent['application_policy']['path']);require_target_capture_profile(profile)
    proof=load(a.capture_proof);need(proof['completed'] and proof['accepted']==proof['rejected']==1 and
        proof['compact_rejection_first_hidden_retained'] and proof['queued_bonus_without_new_process'] and proof['native_owners']==0,
        'The actual completed target acceptance/rejection capture must be qualified first')
    for row in (parent['source'],parent['entry'],parent['provider'],parent['graph'],*parent['required_replacements'].values()):
        need(record(row['path'])==row,'A qualified support provider changed')
    case_root=Path(proof['case']['path']).parent;native_case=load(case_root/'case/plan.private.json')
    package=load(native_case['package']['path']);linked=load(package['relink']['path'])
    need(any(row==parent['provider'] for row in linked['new_inputs']) and parent['entry'] in linked['new_inputs'],
         'The actual qualified native capture must use this exact parent entry and provider')
    a.out.mkdir(parents=True,exist_ok=False);old_dir=Path(parent['source']['path']).parent
    for header in old_dir.glob('*.h'):shutil.copyfile(header,a.out/header.name)
    names=('persistent_mtp_online.h','persistent_mtp_online.cpp','persistent_mtp_cursor.h')
    for name in names:shutil.copyfile(ROOT/'native/app'/name,a.out/name)
    original=Path(parent['source']['path']).read_text(encoding='utf-8')
    text=once(original,'#include "target_verification_capture_audit.h"','#include "persistent_mtp_online.h"')
    old_scope=profile['overrides']['native_headless_model_audit']
    scope=dict(schema='ps5-qwen-persistent-MTP-online-v1',kind='S1-persistent-MTP-online',requests=1,model_loads=1,
        HTTP_requests=0,VideoOut_starts=0,maximum_target_verifications=6,maximum_auxiliary_steps=32,
        persistent_auxiliary_KV_clear_once=True,maximum_simultaneous_auxiliary_contexts=1,
        accepted_drafts_consumed_with_first_target_hidden=True,queued_bonus_sampled_only_by_original_target=True,
        target_hidden_captured_inside_original_epoch=True,auxiliary_rollback_snapshots=0,target_rollback_snapshots=1,
        model_MTP_weights_loaded=True,MTP_layer=48,CPU_heap_quota_bytes=672<<20,CPU_heap_check_provider_count=3,
        legacy_initial_policy_CPU_budget_bytes=512<<20,force_one_wrong_draft=a.force_one_wrong_draft,
        original_physical_OS_Flexible_Direct_and_completion_guards_preserved=True,performance_timings_usable=False)
    text=once(text,json.dumps(json.dumps(old_scope,separators=(',',':'))),json.dumps(json.dumps(scope,separators=(',',':'))))
    text=once(text,json.dumps(old_scope['kind']),json.dumps(scope['kind']))
    start=text.index('            qwen_app::TargetVerificationCaptureHooks capture_hooks;')
    end=text.index('            qwen_app::FirstGeneration trial(shadow);',start)
    text=text[:start]+'''            qwen_app::MtpOnlineHooks MTP_hooks;
            MTP_hooks.begin=qwen_native_driver_begin;MTP_hooks.complete=qwen_native_driver_complete;
            MTP_hooks.checkpoint=qwen_native_driver_checkpoint;MTP_hooks.stage=qwen_native_stage;
            MTP_hooks.guard=[]{require_model_CPU_budget();};
            MTP_hooks.verify=[&](std::int32_t draft){qwen_app_routing_event_begin();return engine->next_with_one_draft(draft);};
            MTP_hooks.decision=[&]{const auto s=engine->speculative_step_stats();return qwen_app::MtpOnlineDecision{s.attempts,s.accepted,s.rejected,s.queued_bonus_samples};};
            qwen_app::PersistentMtpOnline shadow(consumer,model,context,std::move(MTP_hooks),6,FORCE);
'''.replace('FORCE','true' if a.force_one_wrong_draft else 'false')+text[end:]
    text=text.replace('target_capture_audit','online_MTP_audit')
    for name in ('observed_system_headroom','require_model_CPU_budget','wait_for_initial_model_CPU_budget',
                 'model_file_identity','model_directory_identity','resident_reset_empty_context'):
        need(body(original,name)==body(text,name),'A physical, CPU, identity or reset guard changed')
    source=a.out/'entry.private.cpp';source.write_text(text,encoding='utf-8',newline='\n');entry=a.out/'entry.o'
    ec=parent['commands'][6].copy();overlay=load(ec[ec.index('-ivfsoverlay')+1])
    for root in overlay['roots']:root['external-contents']=(a.out/Path(root['external-contents']).name).resolve().as_posix()
    view=a.out/'selected-view.private.json';save(view,overlay)
    ec=[str(a.out) if x==str(old_dir) else x for x in ec];ec[ec.index('-ivfsoverlay')+1]=str(view)
    ec[ec.index('-c')+1]=str(source);ec[ec.index('-o')+1]=str(entry)
    if '-MF'in ec:ec[ec.index('-MF')+1]=str(a.out/'entry.private.d')
    legacy=check_legacy_policy(a.workspace,a.current,view,a.out/'legacy-policy-host-check')
    provider=a.out/'persistent-mtp-online.o';tc=parent['commands'][5].copy()
    tc=[str(a.out) if x==str(old_dir) else x for x in tc]
    tc[tc.index('-c')+1]=str(a.out/'persistent_mtp_online.cpp');tc[tc.index('-o')+1]=str(provider)
    up=a.current.parent/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569';host=a.workspace/'toolchain/msys-clang64/clang64/bin'
    sha=up/'vendor/hash/sha256/sha256.c';sha_object=a.out/'host-sha256.o';test=a.out/'actual-first-generation-online-test.exe'
    hc=[str(host/'clang++.exe'),'-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(a.out),'-I',str(ROOT/'native/app')]
    for include in ('include','src','ggml/include','vendor'):hc+=['-I',str(up/include)]
    commands=[[str(host/'clang.exe'),'-O2','-I',str(up/'vendor/hash'),'-c',str(sha),'-o',str(sha_object)],
        hc+[str(ROOT/'tests/persistent_mtp_online_test.cpp'),str(a.out/'persistent_mtp_online.cpp'),str(sha_object),'-o',str(test)],
        [str(test)],tc,ec]
    inputs=[record(a.out/name) for name in (*names,'mtp_target_hidden_capture.h','mtp_target_hidden_capture_runtime.h')]+[
        record(ROOT/'tests/persistent_mtp_online_test.cpp'),record(ROOT/'native/app/first_generation.h'),record(ROOT/'native/app/session.h'),
        record(up/'include/llama.h'),record(up/'src/llama-ext.h'),record(sha),record(up/'vendor/hash/sha256/sha256.h'),record(up/'vendor/hash/rotate-bits/rotate-bits.h')]
    env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''),TMP=str(a.out),TEMP=str(a.out))
    for i,command in enumerate(commands):
        run=subprocess.run(command,capture_output=True,timeout=240,env=env);(a.out/(str(i)+'.private.log')).write_bytes(run.stdout+run.stderr)
        need(run.returncode==0,run.stderr.decode(errors='replace')[-3500:])
    need(all(record(row['path'])==row for row in inputs),'A checked online MTP source changed')
    host_receipt=a.out/'host-controls.private.json';save(host_receipt,dict(completed=True,
        actual_FirstGeneration_accept_reject_catchup_bonus_EOG_and_attempt_bound_controls_passed=True,inputs=inputs,
        commands=commands[:3],target_provider=record(provider),PS5_operations=0))
    application=dict(profile,entry_artifact=record(entry),source=record(source),headless_audit_kind=scope['kind'],
        overrides=dict(profile['overrides'],native_headless_model_audit=scope),legacy_policy_host_check=record(a.out/'legacy-policy-host-check/result.private.json'),
        actual_FirstGeneration_online_MTP_host_controls_passed=True,online_MTP_host_check=record(host_receipt),
        native_target_capture_proof=record(a.capture_proof),native_target_capture_provider=parent['provider'],
        native_performance_qualified=False,production_adopted=False)
    for key in ('actual_FirstGeneration_target_capture_host_controls_passed','target_capture_host_check'):application.pop(key,None)
    policy=a.out/'application-policy.private.json';save(policy,application)
    save(a.out/'result.private.json',dict(completed=True,application_policy=record(policy),entry=record(entry),reader=parent['reader'],
        provider=record(provider),graph=parent['graph'],source=record(source),inputs=inputs,commands=commands,
        required_replacements=parent['required_replacements'],required_link_flags=parent['required_link_flags'],
        required_additional_objects=[parent['provider']],host_controls=record(host_receipt),capture_proof=record(a.capture_proof),
        PS5_operations=0,native_online_MTP_qualified=False,production_adopted=False))
    print(json.dumps(dict(completed=True,actual_FirstGeneration_host_controls_passed=True,target_compiled=True,PS5_operations=0)))


if __name__=='__main__':main()
