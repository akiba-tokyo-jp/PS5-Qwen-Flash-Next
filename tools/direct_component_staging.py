#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Opt-in64MiB component transport; keep the qualified16KiB receiver window."""
import inspect
import json
import os
from pathlib import Path
import subprocess

import direct_self_staging as original
from build_performance_quantizer import record
from start_success_route import load,need,save
from success_case_control import build

ROOT=Path(__file__).resolve().parents[1]


def prepare(workspace,out,qualified):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    original.qualification(qualified)
    source=ROOT/'native/qwen_flash_next/direct_stage_receive.h'
    raw=source.read_text();old='DIRECT_STAGE_BYTES>(32ull<<20)'
    need(raw.count(old)==1,'One exact original total-byte upper bound required')
    extended=raw.replace(old,'DIRECT_STAGE_BYTES>(64ull<<20)')
    target=out/'component_direct_receive.h';target.write_text(extended,encoding='utf-8',newline='\n')
    tested=extended
    for header in ('sys/socket.h','netinet/in.h','sys/time.h'):
        tested=tested.replace('#include <'+header+'>\n','',1)
    declaration='static _Alignas(16384) unsigned char direct_stage_window[16384];'
    need(tested.count(declaration)==1,'The native16KiB aligned window must remain unchanged')
    tested=tested.replace(declaration,'static unsigned char *direct_stage_window;',1)
    (out/'direct_stage_under_test.h').write_text(tested,encoding='utf-8',newline='\n')
    harness=(ROOT/'tests/direct_stage_receive_test.c').read_text()
    host=Path(workspace)/'toolchain/msys-clang64/clang64/bin';sha=Path(workspace)/'native/model_hash/sha256.c'
    env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''),TMP=str(out),TEMP=str(out))
    checks=[]
    for size in ((32<<20)+17,64<<20,(64<<20)+1):
        rounded=(size+16383)&~16383
        text=harness.replace('#define DIRECT_STAGE_BYTES 17003u','#define DIRECT_STAGE_BYTES '+str(size)+'u',1)
        text=text.replace('stored[32768]','stored['+str(rounded)+']',1)
        text=text.replace('stored_size==32768','stored_size=='+str(rounded),1)
        text=text.replace('write_calls==2','write_calls=='+str(rounded//16384),1)
        text=text.replace('for(fault=GOOD;fault<FAULT_COUNT;++fault)','for(fault=GOOD;fault<=GOOD;++fault)',1)
        text=text.replace(',FAULT_COUNT);',',1);',1)
        if size>64<<20:
            start=text.index('int main(void){')
            text=text[:start]+'''int main(void){int operations=0;
                const int result=case_receive_direct_stage(&operations);
                CHECK(!result&&!operations&&!live_objects&&!opens&&!acks&&!write_calls);return 0;}
'''
        path=out/('size-'+str(size)+'.c');path.write_text(text,encoding='utf-8',newline='\n');exe=path.with_suffix('.exe')
        jobs=[[str(host/'clang.exe'),'-std=c11','-O2','-Wall','-Wextra','-Werror','-Wno-unused-function',
               '-Wno-unused-variable','-I',str(out),'-I',str(sha.parent),str(path),str(sha),'-o',str(exe)],[str(exe)]]
        for i,job in enumerate(jobs):
            result=subprocess.run(job,capture_output=True,timeout=45,env=env)
            (out/(str(size)+'-'+str(i)+'.private.log')).write_bytes(result.stdout+result.stderr)
            need(result.returncode==0,result.stderr.decode(errors='replace')[-3500:])
        checks.append(dict(bytes=size,accepted=size<=64<<20,positive_stream_and_aligned_tail=size<=64<<20,
                           refusal_before_OS_objects=size>64<<20,source=record(path),commands=jobs))
    save(out/'result.private.json',dict(completed=True,source=record(source),native_header=record(target),
        original_uploader=record(Path(original.__file__)),adapter=record(Path(__file__)),original_qualification=record(qualified),
        exact_native_change='One total-byte upper bound32MiB->64MiB',payload_window_bytes=16384,
        original14_failure_controls_reused_without_replay=True,new_size_controls=checks,OS_objects=0,PS5_operations=0))
    return out/'result.private.json'


def upload(capture,remote,out,lan,native_verify,*,workspace,mount_plan,current_rows,qualified,component_control):
    control=load(component_control)
    need(control['completed'] and control['original_qualification']==record(qualified) and
         control['adapter']==record(Path(__file__)) and
         control['original_uploader']==record(Path(original.__file__)) and
         all(record(control[k]['path'])==control[k] for k in ('source','native_header')) and
         len(control['new_size_controls'])==3 and control['payload_window_bytes']==16384,
         'Exact new size controls and unchanged original receiver/uploader qualification required')
    raw=Path(control['source']['path']).read_text()
    need(Path(control['native_header']['path']).read_text()==raw.replace('DIRECT_STAGE_BYTES>(32ull<<20)',
        'DIRECT_STAGE_BYTES>(64ull<<20)'),'No native receiver change except the upper bound is allowed')
    def build_component(workspace_arg,mount_arg,old,new,pending,operation,native_out,**keywords):
        need(operation=='receive-direct-stage' and old==new==current_rows and not pending and
             set(keywords)=={'direct_stage_context'},'Only one unchanged-current component receiver may use this adapter')
        context=keywords['direct_stage_context']
        need(context.count('#include "direct_stage_assigned_port.h"')==1,'The qualified assigned endpoint is required')
        # Action14 is a generic CPU hook. Retain the original37-page receiver
        # allowance although that hook normally uses the smaller metadata gate.
        context+='''
static int component_receive_headroom(void*unused){
    if(!qwen_launch_headroom(unused))return 0;
    uint32_t a=0,b=0;size_t na=4,nb=4;
    return !sysctlbyname("vm.stats.vm0.v_free_count",&a,&na,NULL,0)&&na==4&&
        !sysctlbyname("vm.stats.vm0.v_free_count",&b,&nb,NULL,0)&&nb==4&&a>=935&&b>=935;
}
#define qwen_launch_headroom component_receive_headroom
#define case_receive_direct_stage case_retire_completed_images
'''
        context+='#include '+json.dumps(Path(control['native_header']['path']).as_posix())+'\n'
        context+='#undef case_receive_direct_stage\n#undef qwen_launch_headroom\n'
        return build(workspace_arg,mount_arg,old,new,[],'retire-completed-images',native_out,completed_images_context=context)
    code=inspect.getsource(original.upload)
    need(code.count('capture[\'bytes\']<=32<<20')==1,'One exact original host total-byte bound required')
    code=code.replace('capture[\'bytes\']<=32<<20','capture[\'bytes\']<=64<<20',1)
    namespace=dict(original.__dict__,build=build_component)
    exec(compile(code,'qualified_component_upload','exec'),namespace)
    return namespace['upload'](capture,remote,out,lan,native_verify,workspace=workspace,mount_plan=mount_plan,
        current_rows=current_rows,qualified=qualified)
