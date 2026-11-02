#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Package one explicitly compiled finite audit against the selected current inputs."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

from build_performance_quantizer import record
from mtp_shadow_host_check import require_profile as require_shadow_host_check,require_target_capture_profile,require_online_profile
from start_success_route import load,need,save

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','build','identity-provider','out'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--full-F32-observer',type=Path)
    a=p.parse_args();compiled=load(a.build);policy=load(compiled['application_policy']['path'])
    need(compiled['completed'] and policy['completed'] and policy['kind']=='headless-model-audit' and
         policy['headless_model_audit'] and policy['model_and_GPU_guards_preserved'],'Exact guarded headless audit required')
    if policy['headless_audit_kind']=='S1-MTP-shadow':
        require_shadow_host_check(policy)
        need(policy.get('successful_MTP_contract_verified') is True and policy.get('actual_legacy_policy_validator_passed') is True,
             'Bind successful MTP providers and the actual legacy policy host check before packaging')
    if policy['headless_audit_kind']=='S1-target-hidden-capture-audit':require_target_capture_profile(policy)
    if policy['headless_audit_kind']=='S1-persistent-MTP-online':require_online_profile(policy)
    for key in ('entry','reader','provider','source','application_policy'):
        need(record(compiled[key]['path'])==compiled[key],'A compiled audit provider changed')
    a.out.mkdir(parents=True,exist_ok=False)
    arguments=['--current',a.current,'--out',a.out/'link','--replace','entry.o='+compiled['entry']['path'],
        '--replace','early-SELF.o='+compiled['reader']['path'],'--add-object',compiled['provider']['path'],
        '--application-policy',compiled['application_policy']['path']]
    if compiled.get('required_link_flags'):
        early=(policy['headless_audit_kind'] in ('CPU-Direct-readmission','CPU-startup-staging-memory') and policy.get('unloaded_CPU_fixture') and
             compiled['required_link_flags']==['--undefined='+name for name in ('qwen_driver_table_storage','Q2_bundle_expected_identity','Q2_extra_expected_identity','Q2_current_expected_identity')])
        original_reads=(policy['headless_audit_kind']=='I1-model-pread-observation' and
             compiled.get('host_multithread_errno_short_read_identity_and_overflow_controls_passed') is True and compiled['required_link_flags']==['--wrap=pread'])
        target_capture=(policy['headless_audit_kind'] in ('S1-target-hidden-capture-audit','S1-persistent-MTP-online') and compiled['required_link_flags']==
            ['--wrap='+name for name in ('llama_batch_ext_init','llama_batch_ext_free','llama_batch_ext_clear','llama_batch_ext_add_token','llama_process','llama_synchronize')])
        need(early or original_reads or target_capture,'Only explicitly bound data preservation or observation flags are admitted')
        arguments+=['--link-flag='+flag for flag in compiled['required_link_flags']]
    if compiled.get('required_additional_objects'):
        need(policy['headless_audit_kind']=='S1-persistent-MTP-online' and
             compiled['required_additional_objects']==[policy['native_target_capture_provider']],
             'Only the previously qualified original target capture provider may accompany online MTP')
        for row in compiled['required_additional_objects']:
            need(record(row['path'])==row,'Qualified target capture provider changed')
            arguments+=['--add-object',row['path']]
    if 'graph' in compiled:
        need(record(compiled['graph']['path'])==compiled['graph'],'Compiled graph changed')
        arguments+=['--replace','graph.o='+compiled['graph']['path']]
    for name,row in compiled.get('required_replacements',{}).items():
        need(record(row['path'])==row,'A required MTP support provider changed')
        arguments+=['--replace',name+'='+row['path']]
    if a.full_F32_observer:
        observer=load(a.full_F32_observer)
        need(observer['completed'] and observer['qualification_only'] and observer['extra_GPU_downloads']==0 and
             record(observer['artifact']['path'])==observer['artifact'],'Exact existing-row qualification observer required')
        arguments+=['--add-object',observer['artifact']['path']]+['--link-flag='+flag for flag in observer['link_flags']]
    jobs=[('link','relink_retained_current.py',arguments),('SELF','package_retained_current.py',[
        '--workspace',a.workspace,'--current',a.current,'--relink',a.out/'link/result.private.json','--out',a.out/'SELF',
        '--formatter-from',a.current/'provenance/current-package.private.json','--identity-provider',a.identity_provider])]
    for label,tool,args in jobs:
        with (a.out/(label+'.private.log')).open('xb') as stream:
            result=subprocess.run([sys.executable,'-B',str(ROOT/'tools'/tool),*map(str,args)],stdout=stream,stderr=subprocess.STDOUT,timeout=600)
        need(result.returncode==0,'Host '+label+' failed; inspect '+str(a.out/(label+'.private.log')))
        print(json.dumps(dict(phase=label,completed=True,PS5_operations=0)),flush=True)
    save(a.out/'result.private.json',dict(completed=True,build=record(a.build),package=record(a.out/'SELF/result.private.json'),
        full_F32_qualification=bool(a.full_F32_observer),PS5_operations=0,native_qualified=False,production_adopted=False))


if __name__=='__main__':main()
