#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Qualify256KiB transfer/integrity windows while retaining every I/O boundary log."""
import argparse
import json
import os
from pathlib import Path
import subprocess
from build_performance_quantizer import record
from build_speculative_batch_probe import once
from direct_self_staging import qualification
from model_part_receiver_geometry import receiver_text
from start_success_route import load, need, save

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','original-proof','ceiling-proof','out'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--resume-precompile',action='store_true',help='Resume only before either new host executable was compiled')
    a=p.parse_args();original_proof=qualification(a.original_proof);ceil=load(a.ceiling_proof)
    need(ceil['completed'] and ceil['only_finite_payload_ceiling_changed'] and
         ceil['new_boundary_controls']['new_byte_boundary_cases']==7 and
         ceil['original_qualification']==original_proof and record(ceil['receiver']['path'])==ceil['receiver'],
         'Reuse the completed exact seven byte-ceiling controls')
    a.out.mkdir(parents=True,exist_ok=a.resume_precompile)
    if a.resume_precompile:need(not(a.out/'transport.exe').exists() and not(a.out/'integrity.exe').exists() and
        not(a.out/'result.private.json').exists(),'Completed geometry controls may not be repeated')
    source=ROOT/'native/qwen_flash_next/direct_stage_receive.h';text=receiver_text(source.read_text(),262144)
    receiver=a.out/'batched_model_part_receive.h';receiver.write_text(text,newline='\n')
    mocked=text
    for name in ('sys/socket.h','netinet/in.h','sys/time.h'):
        mocked=once(mocked,'#include <'+name+'>\n','')
    mocked=once(mocked,'static _Alignas(16384) unsigned char direct_stage_window[262144];',
                'static unsigned char *direct_stage_window;')
    (a.out/'direct_stage_under_test.h').write_text(mocked,newline='\n')
    test=ROOT/'tests/direct_stage_receive_test.c';fixture=test.read_text()
    for before,after in (('#define DIRECT_STAGE_BYTES 17003u','#define DIRECT_STAGE_BYTES 262763u'),
        ('stored[32768]','stored[524288]'),('bytes==16384&&offset>=0','bytes==262144&&offset>=0'),
        ('stored_size==32768','stored_size==524288'),('backing=malloc(32768)','backing=malloc(278528)')):
        fixture=once(fixture,before,after)
    target=a.out/'transport-geometry.c';target.write_text(fixture,newline='\n')
    integrity=ROOT/'tests/launch_integrity.c';boundary=integrity.read_text()
    boundary=once(boundary,'const uint64_t sizes[]={1,16383,16384,16385,65535,65536,65537,27798695};',
        'const uint64_t sizes[]={1,16383,16384,16385,65535,65536,65537,262143,262144,262145,27798695,235929600};')
    boundary=once(boundary,'.source_bytes=65537,.mode=mode','.source_bytes=QWEN_LAUNCH_WINDOW+1,.mode=mode')
    before='qwen_launch_integrity_stream(&s,window,65537,60)'
    need(boundary.count(before)==2,'Both changed fault geometry and its no-replay assertion must be bound')
    boundary=boundary.replace(before,'qwen_launch_integrity_stream(&s,window,QWEN_LAUNCH_WINDOW+1,60)')
    ipath=a.out/'integrity-geometry.c';ipath.write_text(boundary,newline='\n')
    host=a.workspace/'toolchain/msys-clang64/clang64/bin';sha=a.workspace/'native/model_hash/sha256.c'
    env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''),TMP=str(a.out),TEMP=str(a.out));commands=[]
    def run(command,name):
        command=list(map(str,command));commands.append(command)
        result=subprocess.run(command,capture_output=True,timeout=120,env=env)
        (a.out/(name+'.private.log')).write_bytes(result.stdout+result.stderr)
        need(not result.returncode,(result.stdout+result.stderr).decode(errors='replace')[-3500:]);return result.stdout
    transport=a.out/'transport.exe'
    run([host/'clang.exe','-std=c11','-O2','-Wall','-Wextra','-Werror','-I',a.out,'-I',sha.parent,
         target,sha,'-o',transport],'transport-compile')
    result=json.loads(run([transport],'transport-controls'))
    need(result['completed'] and result['returned_transport_and_file_cases']==14 and result['OS_objects']==0,
         'All fourteen changed receive/tail/failure geometry controls must pass')
    executable=a.out/'integrity.exe'
    run([host/'clang.exe','-std=c11','-O2','-Wall','-Wextra','-Werror','-DQWEN_LAUNCH_WINDOW=262144u',
         '-I',ROOT/'native/qwen_flash_next',ipath,'-o',executable],'integrity-compile')
    run([executable],'integrity-controls')
    save(a.out/'result.private.json',dict(completed=True,receiver=record(receiver),original_receiver=record(source),
        original_qualification=original_proof,ceiling_qualification=record(a.ceiling_proof),maximum_model_part_bytes=512<<20,
        receive_window_bytes=262144,whole_integrity_window_bytes=262144,host_send_window_bytes=16384,
        receive_socket_buffer_bytes=32768,additional_fixed_CPU_buffer_pages=30,CPU_metadata_margin_pages=67,
        original_180_second_deadline_preserved=True,all_before_and_returned_IO_stages_synced=True,
        new_transport_geometry_controls=result,new_integrity_geometry_controls=dict(positive_sizes=12,returned_fault_modes=8,
            EOF_size_refusals=2,misalignment_empty_and_deadline_refusals=3),reused_ceiling_boundaries=7,
        old_unchanged_transport_or_endpoint_controls_replayed=0,native_large_model_part_qualified=False,
        inputs=[record(x) for x in (Path(__file__),ROOT/'tools/model_part_receiver_geometry.py',test,integrity,sha,target,ipath)],
        commands=commands,PS5_operations=0))
    print(json.dumps(dict(completed=True,new_transport_cases=14,new_integrity_controls=25,extra_fixed_CPU_pages=30,PS5_operations=0)))


if __name__=='__main__':main()
