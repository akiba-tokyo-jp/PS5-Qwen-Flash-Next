#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Publish one new content-bound CPU prototype payload using qualified staging."""
import json
import secrets
from pathlib import Path
from build_performance_quantizer import record
from direct_self_staging import upload
from run_native_paired_down import completed_operation
from start_success_route import need,save
from success_case_control import ALIAS,PHYSICAL,build


def publish_payload(a,lan,cold,rows,out):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    local=cold['payload'];application=cold['application_path']
    need(record(local['path'])==local and local['bytes']==8<<20 and application==
        '/app0/qwen-runtime/cold-rodata-'+local['sha256'][:24]+'.bin','Exact deterministic prototype payload required')
    pending='/data/ai/moss-qwen-case-'+secrets.token_hex(16)+'-candidate-SELF.bin'
    target=PHYSICAL+application[5:];alias=ALIAS+application[5:]
    lan.absent(pending);lan.absent(target)
    context=''.join('#define '+key+' '+json.dumps(value)+'\n' for key,value in (
        ('CASE_COMPONENT_PENDING',pending),('CASE_COMPONENT_TARGET',target),('CASE_COMPONENT_ALIAS',alias),
        ('CASE_COMPONENT_SHA256',local['sha256'])))+'#define CASE_COMPONENT_BYTES '+str(local['bytes'])+'ULL\n'
    plan=build(a.workspace,a.mount_plan,rows,rows,[],'publish-component',out/'native',component_publish_context=context)
    save(out/'intent.private.json',dict(pack=local,pending=pending,target=target,alias=alias,maximum_publications=1))
    def verify(capture,remote):
        need(capture==local and remote==pending,'Exact CPU prototype staging path required')
        result=completed_operation(lan,plan,out/'native')
        need(result['operation_calls']==1,'One positively returned new-only publication required')
        return dict(whole_native_SHA256_identity_EOF_verified=True,all_reads_returned=True,
                    sha256=local['sha256'],bytes=local['bytes'])
    upload(local,pending,out/'Direct-transfer',lan,verify,current_rows=rows,workspace=a.workspace,
        mount_plan=a.mount_plan,qualified=a.direct_staging_proof)
    save(out/'result.private.json',dict(completed=True,pack=local,target=target,alias=alias,
        whole_SHA256_both_namespaces=True,immutable_mode=292,current_seven_unchanged=True,title_launches=0,GPU_calls=0))
