#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Integrate paired token durability directly into the byte-recovered current entry."""
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
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','recovered','out'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=False);recovered=load(args.recovered)
    need(recovered['completed'] and recovered['object_byte_exact'] and recovered['changed_common_text_sections']==0,
         'A byte-exact complete current entry reconstruction is required')
    for key in ('source','artifact'):need(record(recovered[key]['path'])==recovered[key],'Recovered entry changed')
    original=Path(recovered['source']['path']).read_text(encoding='utf-8')
    settings=load(args.current/'qwen-runtime/development.json');old_scope=settings['native_next_five_normal']
    literal=lambda value:json.dumps(json.dumps(value,separators=(',',':')))
    need(original.count(literal(old_scope))==3,'Exact input, positive and failure copies of the selected contract required')
    retained=load(args.current/'provenance/retained-relink-inputs.private.json')
    nm=args.workspace/'toolchain/llvm-mingw-20261006-ucrt-x86_64/bin/llvm-nm.exe'
    for row in retained:
        if Path(row['path']).suffix!='.o' or Path(row['original_path']).name=='entry.o':continue
        symbols=subprocess.check_output([str(nm),'--defined-only','--extern-only','--demangle',row['path']],text=True)
        need('qwen_service::TokenLedger::' not in symbols,'The changed inline ledger must have one application provider')
    artifacts={};commands=[];profiles={};inputs=[record(ROOT/'native/app/durable_token_ledger.h'),record(ROOT/'native/app/bounded_token_writer.h')]
    for arm,mode in (('control','per_token'),('candidate','request_end')):
        folder=args.out/arm;folder.mkdir()
        for header in Path(recovered['source']['path']).parent.glob('*.h'):shutil.copyfile(header,folder/header.name)
        for header in ('durable_token_ledger.h','bounded_token_writer.h'):
            shutil.copyfile(ROOT/'native/app'/header,folder/header)
        scope=dict(old_scope,schema='ps5-qwen-next-five-normal-v2',per_token_fsync_preserved=mode=='per_token',
            token_record_sync_policy=mode,completed_token_ledger_synced_before_request_result=True,
            interrupted_request_may_lose_unsynced_tail=mode=='request_end')
        text=original.replace(literal(old_scope),literal(scope))
        text=once(text,'            qwen_service::TokenLedger token_ledger;',
            '            qwen_service::TokenLedgerPolicy token_policy;token_policy.durability=qwen_service::TokenDurability::'+mode+';\n'
            '            token_policy.max_record_bytes=1u<<20;token_policy.max_bytes=2u<<20;\n'
            '            qwen_service::TokenLedger token_ledger(token_policy);')
        text=once(text,'            qwen_load::CpuSpan measured_run(qwen_load::request_run);',
            '            const auto complete_request_started=qwen_app::ProfileClock::now();\n'
            '            qwen_load::CpuSpan measured_run(qwen_load::request_run);')
        text=once(text,'token_ledger.close();}measured_run.end();',
            'token_ledger.close();}measured_run.end();\n'
            '            const double complete_request_span_ms=double(qwen_app::profile_elapsed_ns(complete_request_started))/1e6;')
        text=once(text,'row["token_ledger_bytes"]=token_ledger.bytes();',
            'row["token_ledger_bytes"]=token_ledger.bytes();row["token_ledger_sync_calls"]=token_ledger.syncs();\n'
            '            row["token_record_sync_policy"]='+json.dumps(mode)+';row["token_ledger_closed_before_request_result"]=true;\n'
            '            row["complete_request_span_ms"]=complete_request_span_ms;')
        checks=[]
        for name in ('observed_system_headroom','require_model_CPU_budget','wait_for_initial_model_CPU_budget',
                     'model_file_identity','model_directory_identity','resident_reset_empty_context'):
            before,after=body(original,name),body(text,name);need(before==after,'Unrelated admission function changed: '+name)
            checks.append(name)
        for call in ('qwen_native_driver_begin()','qwen_native_driver_complete()','qwen_app::stop_native_model_sources()',
                     'llama_init_from_model(','trial.run(','qwen_app::begin_completed_expert_routes()'):
            need(original.count(call)==text.count(call),'Model/source/GPU/request topology changed')
        source=folder/'entry.private.cpp';source.write_text(text,encoding='utf-8',newline='\n');obj=folder/'entry.o'
        command=recovered['command'].copy()
        # Every include spelling must resolve to the same selected header.
        # A second physical copy defeats pragma-once and duplicates types.
        overlay=load(command[command.index('-ivfsoverlay')+1])
        for root in overlay['roots']:
            root['external-contents']=(folder/Path(root['external-contents']).name).resolve().as_posix()
        selected=folder/'selected-view.private.json';save(selected,overlay)
        command[command.index('-ivfsoverlay')+1]=str(selected)
        command=[str(folder) if value==str(Path(recovered['source']['path']).parent) else value for value in command]
        command[command.index('-c')+1]=str(source);command[command.index('-o')+1]=str(obj)
        if '-MF' in command:command[command.index('-MF')+1]=str(folder/'entry.private.d')
        result=subprocess.run(command,capture_output=True,timeout=240,env=dict(os.environ,TMP=str(folder),TEMP=str(folder)))
        (folder/'compile.private.log').write_bytes(result.stdout+result.stderr)
        need(result.returncode==0,result.stderr.decode(errors='replace')[-3500:]);commands.append(command)
        profile=dict(completed=True,kind='R1-direct',entry_artifact=record(obj),source=record(source),
            overrides=dict(native_next_five_normal=scope),token_sync_policy=mode,
            maximum_records=32,maximum_record_bytes=1<<20,maximum_ledger_bytes=2<<20,
            complete_request_span_includes_final_sync_and_close=True,model_and_GPU_topology_unchanged=True,
            admission_functions_unchanged=checks,PS5_operations=0,native_performance_qualified=False)
        path=folder/'application-policy.private.json';save(path,profile)
        artifacts[arm]=dict(entry=record(obj),source=record(source));profiles[arm]=record(path)
    need(all(record(row['path'])==row for row in inputs),'Token-writer source changed during paired compilation')
    report=dict(completed=True,recovered=record(args.recovered),artifacts=artifacts,application_policies=profiles,
        commands=commands,inputs=inputs,syscall_interposition_used=False,actual_native_effective_policy_reported=True,
        model_and_GPU_topology_unchanged=True,PS5_operations=0,native_speed_or_quality_qualified=False,production_adopted=False)
    save(args.out/'result.private.json',report)
    print(json.dumps({k:v for k,v in report.items() if k not in ('recovered','artifacts','application_policies','commands','inputs')}))


if __name__=='__main__':main()
