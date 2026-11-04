#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Bind ordinary MTP entries to the actual selected compact engine, not a stock engine."""
import argparse
import copy
import os
from pathlib import Path
import shutil
import subprocess

from audit_expert_all_q2_safety import body
from build_performance_quantizer import record
from build_speculative_batch_probe import once
from native_dispatch import ELF
from start_success_route import load,need,save

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','fresh','retained','observed-case','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    engine=next(r for r in load(a.current/'provenance/retained-relink-inputs.private.json') if Path(r['original_path']).name=='engine.o')
    need(record(engine['path'])=={k:engine[k] for k in ('path','bytes','sha256')} and engine['sha256']=='63c42b7103629454b1e51274e3cea7e91c79a2eeec3ea58d9bd6f5b0f9c17891',
         'The actual selected compact engine object is required')
    function='_ZN8qwen_app11LlamaEngine19next_with_one_draftEi';native=ELF(Path(engine['path']))
    need(all(k in native.symbols for k in (function,'qwen_app_compact_rollback_select','qwen_app_compact_rollback_stats')),
         'Actual compiled compact selection and counter symbols required')
    objdump=a.workspace/'toolchain/llvm-mingw-20261006-ucrt-x86_64/bin/llvm-objdump.exe'
    disassembled=subprocess.run([str(objdump),'--disassemble-symbols='+function,'--reloc',engine['path']],capture_output=True,check=True)
    proof_text=disassembled.stdout.decode();need(all(s in proof_text for s in ('compact_rollback','compact_captures','compact_rejections','capture_checkpoint_in_active_epoch')),
         'The actual machine function must contain compact elision and its separate full-capture branch')
    (a.out/'selected-engine.private.asm').write_bytes(disassembled.stdout)
    failure=load(a.observed_case/'native.failure.private.json');stages=(a.observed_case/'native-stages.private.log').read_bytes()
    need(failure['four_next']['complete_captures_elided']==6 and failure['four_next']['all_memory_rollbacks']==1 and
         stages.endswith(b'F32_request_completed request=1 rows=23 failures=0\nresident_additional_exception_work_stopped\n'),
         'The completed first request must observe the selected compact path, despite its subsequent CPU certificate failure')
    helper=ROOT/'native/app/compact_mtp_request_scope.h';test=ROOT/'tests/compact_mtp_request_scope_test.cpp'
    host=a.workspace/'toolchain/msys-clang64/clang64/bin';exe=a.out/'compact-scope.exe';jobs=[]
    def run(job,label):
        jobs.append(job);done=subprocess.run(job,capture_output=True,timeout=180,env=dict(os.environ,
            PATH=str(host)+os.pathsep+os.environ.get('PATH',''),TMP=str(a.out),TEMP=str(a.out)))
        (a.out/(label+'.private.log')).write_bytes(done.stdout+done.stderr)
        need(done.returncode==0,(done.stdout+done.stderr).decode(errors='replace')[-3000:])
    run([str(host/'clang++.exe'),'-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'native/app'),str(test),'-o',str(exe)],'host-compile')
    run([str(exe)],'host-twelve-controls')
    proof=a.out/'compact-contract.private.json';save(proof,dict(completed=True,selected_engine={k:engine[k] for k in ('path','bytes','sha256')},
        actual_machine_function=function,disassembly=record(a.out/'selected-engine.private.asm'),observed_failure=record(a.observed_case/'native.failure.private.json'),
        helper=record(helper),test=record(test),positive_transitions=3,refusal_controls=9,allocation_credit_granted=False,
        full_capture_statistics_not_used_as_compact_ownership=True,engine_code_changed=False,PS5_operations=0))
    products={}
    for arm,path in (('fresh',a.fresh),('retained',a.retained)):
        old=load(path);profile=load(old['application_policy']['path']);need(old['completed'],'Completed original unlaunched ordinary entry required')
        for key in ('entry','source','provider','graph'):need(record(old[key]['path'])==old[key],'An unchanged provider changed')
        folder=a.out/arm;folder.mkdir();prior=Path(old['source']['path']).parent
        for header in prior.glob('*.h'):shutil.copyfile(header,folder/header.name)
        shutil.copyfile(helper,folder/helper.name)
        original=Path(old['source']['path']).read_text(encoding='utf-8')
        need(original.count('qwen_app_compact_rollback_select(true);')==1 and 'qwen_app_compact_rollback_select(false)' not in original,
             'The actual entry must select compact rollback before the cohort')
        text='#include "compact_mtp_request_scope.h"\n'+original
        text=once(text,'            const bool reuse=ordinal>0;','            const bool reuse=false; // No prefix consumer exists in this ordinary-only scope.\n            std::uint64_t compact_before[2]{};qwen_app_compact_rollback_stats(compact_before);')
        text=once(text,'            if(ordinal==1)qwen_app::final_prefix_handoff.certify(engine.get(),context,engine->checkpoint_validation_stats().maximum_payload_bytes,result.request_reset_completed);',
             '            // No final prefix certificate is created for ordinary requests.')
        marker='            std::uint64_t compact[2]{};qwen_app_compact_rollback_stats(compact);'
        text=once(text,marker,marker+'\n            qwen_app::require_compact_mtp_request(compact_before,compact,unsigned(speculative.attempts),unsigned(speculative.rejected));')
        marker='            row["checkpoint"]='
        text=once(text,marker,'            row["completed_checkpoint_admission_state"]={{"last_payload",last_payload},{"saved_payload",saved_payload},{"full_capture_count",checkpoints.captures},{"allocation_credit_added",false}};\n'+marker)
        for name in ('observed_system_headroom','require_model_CPU_budget','wait_for_initial_model_CPU_budget','model_file_identity',
                     'model_directory_identity','resident_reset_empty_context','bind_resident_main_SELF'):
            need(body(original,name)==body(text,name),'An original native physical, identity, reset or SELF guard changed')
        source=folder/'entry.private.cpp';source.write_text(text,encoding='utf-8',newline='\n');artifact=folder/'entry.o'
        job=next(c for c in old['commands'] if '-c' in c and c[c.index('-c')+1]==old['source']['path']).copy()
        overlay=load(job[job.index('-ivfsoverlay')+1])
        for root in overlay['roots']:
            candidate=folder/Path(root['external-contents']).name
            if candidate.exists():root['external-contents']=candidate.resolve().as_posix()
        view=folder/'selected-view.private.json';save(view,overlay);job=[str(folder) if x==str(prior) else x for x in job]
        job[1:1]=['-I',str(folder)];job[job.index('-ivfsoverlay')+1]=str(view);job[job.index('-c')+1]=str(source);job[job.index('-o')+1]=str(artifact)
        if '-MF' in job:job[job.index('-MF')+1]=str(folder/'entry.private.d')
        run(job,arm+'-native')
        revised=copy.deepcopy(profile);revised.update(entry_artifact=record(artifact),source=record(source),no_unused_prefix_checkpoint=True,
            ordinary_compact_engine_contract=record(proof),all_original_native_guards_unchanged=True)
        revised.pop('ordinary_checkpoint_backing_contract',None)
        policy=folder/'application-policy.private.json';save(policy,revised)
        result=copy.deepcopy(old);result.update(application_policy=record(policy),entry=record(artifact),source=record(source),
            ordinary_compact_engine_contract=record(proof),original_unlaunched_entry=record(path),old_MTP_cursor_controls_replayed=0,
            commands=old['commands']+[job]);save(folder/'result.private.json',result);products[arm]=record(folder/'result.private.json')
    save(a.out/'result.private.json',dict(completed=True,builds=products,compact_contract=record(proof),new_host_controls=12,
        old_MTP_cursor_controls_replayed=0,PS5_operations=0,native_qualified=False,production_adopted=False))
    print(dict(completed=True,actual_compact_engine_bound=True,new_host_controls=12,old_checks_replayed=0,PS5_operations=0))


if __name__=='__main__':main()
