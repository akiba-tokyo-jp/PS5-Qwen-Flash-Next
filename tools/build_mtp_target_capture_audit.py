#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build a finite real target accept/reject audit of synchronized NextN retention."""
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
from mtp_shadow_host_check import require_profile
from start_success_route import load,need,save

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','parent','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();parent=load(a.parent);profile=load(parent['application_policy']['path']);require_profile(profile)
    for row in (parent['source'],parent['entry'],parent['provider'],parent['graph'],*parent['required_replacements'].values()):
        need(record(row['path'])==row,'A successful MTP support input changed')
    a.out.mkdir(parents=True,exist_ok=False)
    old_dir=Path(parent['source']['path']).parent
    for header in old_dir.glob('*.h'):shutil.copyfile(header,a.out/header.name)
    names=('mtp_target_hidden_capture.h','mtp_target_hidden_capture_runtime.h','mtp_target_hidden_capture_runtime.cpp','target_verification_capture_audit.h')
    for name in names:shutil.copyfile(ROOT/'native/app'/name,a.out/name)
    original=Path(parent['source']['path']).read_text(encoding='utf-8')
    text=once(original,'#include "persistent_mtp_shadow.h"','#include "mtp_target_hidden_capture_runtime.h"\n#include "target_verification_capture_audit.h"')
    old_scope=profile['overrides']['native_headless_model_audit']
    scope=dict(schema='ps5-qwen-target-NextN-retention-audit-v1',kind='S1-target-hidden-capture-audit',requests=1,model_loads=1,
        HTTP_requests=0,VideoOut_starts=0,controlled_target_drafts=[11,42],maximum_target_verifications=2,
        controlled_drafts_are_not_MTP_proposals=True,only_original_target_verified_tokens_emitted=True,
        retain_hidden_rows_inside_original_target_epoch=True,additional_target_process_calls=0,
        auxiliary_contexts=0,model_MTP_weights_loaded=True,MTP_layer=48,trunk_CPU_Expert_placement_unchanged=True,
        CPU_heap_quota_bytes=672<<20,legacy_initial_policy_CPU_budget_bytes=512<<20,CPU_heap_check_provider_count=3,
        original_physical_OS_Flexible_Direct_and_completion_guards_preserved=True,performance_timings_usable=False)
    text=once(text,json.dumps(json.dumps(old_scope,separators=(',',':'))),json.dumps(json.dumps(scope,separators=(',',':'))))
    text=once(text,json.dumps(old_scope['kind']),json.dumps(scope['kind']))
    start=text.index('            qwen_app::MtpShadowBoundaries MTP_boundaries;')
    end=text.index('            qwen_app::FirstGeneration trial(shadow);',start)+len('            qwen_app::FirstGeneration trial(shadow);')
    text=text[:start]+'''            qwen_app::bind_mtp_target_hidden_capture(context);
            engine->enable_speculative_step_prototype(admit_checkpoint);
            qwen_app::TargetVerificationCaptureHooks capture_hooks;
            capture_hooks.verify=[&](std::int32_t draft){qwen_app_routing_event_begin();return engine->next_with_one_draft(draft);};
            capture_hooks.decision=[&]{const auto s=engine->speculative_step_stats();return qwen_app::TargetVerificationDecision{s.attempts,s.accepted,s.rejected,s.queued_bonus_samples};};
            capture_hooks.capture=qwen_app::mtp_target_hidden_capture;
            qwen_app::TargetVerificationCaptureAudit shadow(consumer,std::move(capture_hooks));
            qwen_app::FirstGeneration trial(shadow);'''+text[end:]
    text=text.replace('MTP_shadow_audit','target_capture_audit')
    marker='        auto audit=target_capture_audit;'
    text=once(text,marker,'        qwen_app::retire_mtp_target_hidden_capture_after_all_owners();\n'+marker)
    for name in ('observed_system_headroom','require_model_CPU_budget','wait_for_initial_model_CPU_budget',
                 'model_file_identity','model_directory_identity','resident_reset_empty_context'):
        need(body(original,name)==body(text,name),'An original physical, CPU, identity or reset guard changed')
    source=a.out/'entry.private.cpp';source.write_text(text,encoding='utf-8',newline='\n');entry=a.out/'entry.o'
    ec=parent['commands'][2].copy();overlay=load(ec[ec.index('-ivfsoverlay')+1])
    for root in overlay['roots']:root['external-contents']=(a.out/Path(root['external-contents']).name).resolve().as_posix()
    view=a.out/'selected-view.private.json';save(view,overlay)
    ec=[str(a.out) if x==str(old_dir) else x for x in ec];ec[ec.index('-ivfsoverlay')+1]=str(view)
    ec[ec.index('-c')+1]=str(source);ec[ec.index('-o')+1]=str(entry)
    if '-MF'in ec:ec[ec.index('-MF')+1]=str(a.out/'entry.private.d')
    legacy=check_legacy_policy(a.workspace,a.current,view,a.out/'legacy-policy-host-check')
    provider=a.out/'target-hidden-capture.o';tc=parent['commands'][0].copy()
    tc=[str(a.out) if x==str(old_dir) else x for x in tc]
    tc[tc.index('-c')+1]=str(a.out/'mtp_target_hidden_capture_runtime.cpp');tc[tc.index('-o')+1]=str(provider)
    tc[1:1]=['-Wall','-Wextra','-Werror']
    up=a.current.parent/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569';host=a.workspace/'toolchain/msys-clang64/clang64/bin'
    sha_source=up/'vendor/hash/sha256/sha256.c';sha_object=a.out/'host-sha256.o'
    core_test=a.out/'capture-core-test.exe';caller_test=a.out/'actual-caller-capture-test.exe'
    hc=[str(host/'clang++.exe'),'-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(a.out),'-I',str(ROOT/'native/app'),'-I',str(up/'vendor')]
    commands=[[str(host/'clang.exe'),'-O2','-I',str(up/'vendor/hash'),'-c',str(sha_source),'-o',str(sha_object)],
        hc+[str(ROOT/'tests/mtp_target_hidden_capture_test.cpp'),'-o',str(core_test)],[str(core_test)],
        hc+[str(ROOT/'tests/target_verification_capture_audit_test.cpp'),str(sha_object),'-o',str(caller_test)],
        [str(caller_test)],tc,ec]
    inputs=[record(a.out/name) for name in names]+[record(ROOT/'tests'/name) for name in
        ('mtp_target_hidden_capture_test.cpp','target_verification_capture_audit_test.cpp')]+[
        record(ROOT/'native/app'/name) for name in ('first_generation.h','session.h')]+[
        record(sha_source),record(up/'vendor/hash/sha256/sha256.h'),record(up/'vendor/hash/rotate-bits/rotate-bits.h')]
    env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''),TMP=str(a.out),TEMP=str(a.out))
    for i,command in enumerate(commands):
        run=subprocess.run(command,capture_output=True,timeout=240,env=env);(a.out/(str(i)+'.private.log')).write_bytes(run.stdout+run.stderr)
        need(run.returncode==0,run.stderr.decode(errors='replace')[-3500:])
    need(all(record(row['path'])==row for row in inputs),'A tested target-capture input changed')
    host_receipt=a.out/'host-controls.private.json';save(host_receipt,dict(completed=True,
        actual_FirstGeneration_accept_reject_bonus_and_hidden_retention_controls_passed=True,inputs=inputs,commands=commands[:5],
        target_provider=record(provider),PS5_operations=0))
    application=dict(profile,entry_artifact=record(entry),source=record(source),
        overrides=dict(profile['overrides'],native_headless_model_audit=scope),headless_audit_kind=scope['kind'],headless_requests=1,
        legacy_policy_host_check=record(a.out/'legacy-policy-host-check/result.private.json'),
        actual_FirstGeneration_target_capture_host_controls_passed=True,target_capture_host_check=record(host_receipt),
        native_performance_qualified=False,production_adopted=False)
    for key in ('actual_FirstGeneration_host_controls_passed','actual_FirstGeneration_host_check','actual_FirstGeneration_provider_inputs'):application.pop(key,None)
    policy=a.out/'application-policy.private.json';save(policy,application)
    save(a.out/'result.private.json',dict(completed=True,application_policy=record(policy),entry=record(entry),reader=parent['reader'],
        provider=record(provider),graph=parent['graph'],source=record(source),inputs=inputs,commands=commands,
        required_replacements=parent['required_replacements'],required_link_flags=['--wrap='+name for name in
            ('llama_batch_ext_init','llama_batch_ext_free','llama_batch_ext_clear','llama_batch_ext_add_token','llama_process','llama_synchronize')],
        host_controls=record(host_receipt),PS5_operations=0,native_capture_or_target_decisions_qualified=False,production_adopted=False))
    print(json.dumps(dict(completed=True,actual_FirstGeneration_host_controls_passed=True,target_compiled=True,PS5_operations=0)))


if __name__=='__main__':main()
