#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reduce only early CPU SELF scratch/read size, preserving min+21 and GPU guards."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess

from audit_expert_all_q2_safety import body
from build_performance_quantizer import record
from build_speculative_batch_probe import once
from reconstruct_main_self_source import generate
from start_success_route import load,need,save

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','out'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=False)
    package=load(args.current/'provenance/current-package.private.json')
    parent=load(package['effective_application_policy']['profile']['path'])
    need(parent['kind']=='R1-direct' and parent['token_sync_policy']=='request_end' and parent['native_performance_qualified'],
         'The adopted direct R1 entry is required')
    native=load(args.current/'provenance/native-link.receipt.private.json');original=Path(parent['source']['path']).read_text(encoding='utf-8')
    for header in Path(parent['source']['path']).parent.glob('*.h'):shutil.copyfile(header,args.out/header.name)
    text=original;before=body(text,'bind_resident_main_SELF')
    after=once(before,'{"window_bytes",1048576}','{"window_bytes",65536}')
    after=once(after,'(r->bytes+1048575)/1048576+1','(r->bytes+65535)/65536+1')
    after=once(after,'{"maximum_read_window_bytes",1048576}','{"maximum_read_window_bytes",65536}')
    after=once(after,'ps5-qwen-main-SELF-v1','ps5-qwen-main-SELF-small-window-v1')
    text=once(text,before,after)
    for name in ('observed_system_headroom','require_model_CPU_budget','wait_for_initial_model_CPU_budget',
                 'model_file_identity','model_directory_identity','resident_reset_empty_context'):
        need(body(original,name)==body(text,name),'An unrelated model/GPU guard changed')
    source=args.out/'entry.private.cpp';source.write_text(text,encoding='utf-8',newline='\n')
    command=native['compile_commands'][0].copy();old_view=str(Path(parent['source']['path']).parent)
    overlay=load(command[command.index('-ivfsoverlay')+1])
    for root in overlay['roots']:root['external-contents']=(args.out/Path(root['external-contents']).name).resolve().as_posix()
    selected=args.out/'selected-view.private.json';save(selected,overlay)
    command=[str(args.out) if v==old_view else v for v in command];command[command.index('-ivfsoverlay')+1]=str(selected)
    obj=args.out/'entry.o';command[command.index('-c')+1]=str(source);command[command.index('-o')+1]=str(obj)
    if '-MF' in command:command[command.index('-MF')+1]=str(args.out/'entry.private.d')
    pure,old=generate(args.current)
    pure=once(pure,'WINDOW=1048576','WINDOW=65536');pure=once(pure,'window_bytes=1048576','window_bytes=65536')
    need('result.selected_floor=minimum+21;' in pure and 'return free>=result.selected_floor;' in pure,
         'The exact existing CPU threshold must remain unchanged')
    reader=args.out/'main-entry-SELF.private.c';reader.write_text(pure,encoding='utf-8',newline='\n')
    llvm=args.workspace/'toolchain/llvm-mingw-20261006-ucrt-x86_64/bin';sdk=args.workspace/'toolchain/ps5-sdk-radv/ps5-payload-sdk/target/include'
    upstream=args.current.parent/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569'
    reader_obj=args.out/'early-SELF.o'
    C=[str(llvm/'clang.exe'),'--no-default-config','--target=x86_64-sie-ps5','-isystem',str(sdk),
        '-std=gnu11','-fno-stack-protector','-fno-plt','-femulated-tls','-fPIC','-O2','-ffunction-sections','-fdata-sections',
        '-I',str(ROOT/'native/app'),'-I',str(upstream/'vendor'),'-c',str(reader),'-o',str(reader_obj)]
    for index,job in enumerate((C,command)):
        result=subprocess.run(job,capture_output=True,timeout=240,env=dict(os.environ,TMP=str(args.out),TEMP=str(args.out)))
        (args.out/(str(index)+'.private.log')).write_bytes(result.stdout+result.stderr)
        need(result.returncode==0,result.stderr.decode(errors='replace')[-3500:])
    settings=load(args.current/'qwen-runtime/development.json');scope=dict(settings['native_resident_main_SELF'],
        schema='ps5-qwen-main-SELF-small-window-v1',window_bytes=65536)
    profile=dict(completed=True,kind='CPU-SELF-window',entry_artifact=record(obj),source=record(source),
        overrides=dict(native_next_five_normal=settings['native_next_five_normal'],native_resident_main_SELF=scope),
        token_sync_policy='request_end',model_and_GPU_topology_unchanged=True,
        CPU_SELF_provider=dict(source=record(reader),artifact=record(reader_obj),parent_source=old['pure_C_source'],
            window_bytes=65536,original_window_bytes=1048576,OS_minimum_plus_21_unchanged=True,
            full_SHA256_inode_EOF_and_completed_launch_binding_preserved=True),
        source_audit=True,native_performance_qualified=False,PS5_operations=0)
    path=args.out/'application-policy.private.json';save(path,profile)
    report=dict(completed=True,application_policy=record(path),entry=record(obj),reader=record(reader_obj),commands=[C,command],
        prior_pure_C_reader_byte_exact=True,early_CPU_window_bytes=65536,CPU_scratch_reduction_bytes=1048576-65536,
        CPU_minimum_plus_21_unchanged=True,model_GPU_memory_and_completion_guards_unchanged=True,
        full_SELF_hash_identity_EOF_requirements_preserved=True,PS5_operations=0,native_qualified=False)
    save(args.out/'result.private.json',report)
    print(json.dumps({k:v for k,v in report.items() if k not in ('application_policy','entry','reader','commands')}))


if __name__=='__main__':main()
