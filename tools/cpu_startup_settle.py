#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Add a separately tested passive settle before the original CPU SELF reader."""
from pathlib import Path
import os
import shutil
import subprocess
import json

from build_performance_quantizer import record
from build_speculative_batch_probe import once
from start_success_route import need,save

ROOT=Path(__file__).resolve().parents[1]
ADAPTER=r'''
#include "cpu_startup_settle.h"
#include <stdio.h>
static uint64_t startup_settle_now(void*ctx){(void)ctx;return now();}
static int startup_settle_observe(void*ctx,struct qwen_cpu_settle_sample*s){
    (void)ctx;uint32_t last=0;
    if(!scalar("vm.stats.vm0.v_free_count",&s->free)||!scalar("vm.stats.vm0.v_free_min",&s->minimum)||
       !scalar("vm.stats.vm0.v_free_reserved",&s->reserved)||!scalar("vm.stats.vm0.v_free_target",&s->target)||
       !scalar("vm.stats.vm0.v_free_count",&last))return 0;
    if(last<s->free)s->free=last;return 1;
}
static int startup_settle_pause(void*ctx){(void)ctx;const struct timespec pause={0,10000000};return nanosleep(&pause,NULL);}
static void startup_settle_event(void*ctx,int done,unsigned polls,const struct qwen_cpu_settle_sample*s){
    (void)ctx;char line[240];snprintf(line,sizeof(line),"CPU_startup_passive_settle done=%d polls=%u free=%u minimum=%u reserved=%u target=%u required=%u original_reader_floor=%u maximum_ms=5000 GPU_calls=0",
        done,polls,s->free,s->minimum,s->reserved,s->target,s->minimum+1173u,s->minimum+21u);qwen_native_stage(line);
}
static int startup_settle(void){
    const struct qwen_cpu_settle_ops ops={startup_settle_now,startup_settle_observe,startup_settle_pause,startup_settle_event};
    return qwen_cpu_startup_settle(NULL,&ops);
}
'''


def transform(original):
    marker='static int identity(int fd,uint64_t out[10]){'
    text=once(original,marker,ADAPTER+'\n'+marker)
    marker='    const uint64_t start=now();if(!start||!sample()){memory_stage();return 0;}'
    return once(text,marker,'    const uint64_t start=now();if(!start){memory_stage();return 0;}\n'
        '    if(!startup_settle()){(void)sample();memory_stage();return 0;}\n'
        '    if(!sample()){memory_stage();return 0;}')


def check(workspace,out):
    out.mkdir(parents=True,exist_ok=False);host=workspace/'toolchain/msys-clang64/clang64/bin'
    header=ROOT/'native/app/cpu_startup_settle.h';test=ROOT/'tests/cpu_startup_settle_test.c';exe=out/'settle-test.exe'
    env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''))
    command=[str(host/'clang.exe'),'-std=c11','-O2','-Wall','-Wextra','-Werror','-I',str(header.parent),str(test),'-o',str(exe)]
    run=subprocess.run(command,capture_output=True,timeout=120,env=env);(out/'build.private.log').write_bytes(run.stdout+run.stderr)
    need(run.returncode==0,run.stderr.decode(errors='replace')[-3000:])
    run=subprocess.run([str(exe)],capture_output=True,timeout=10,env=env);(out/'run.private.log').write_bytes(run.stdout+run.stderr)
    need(run.returncode==0,run.stderr.decode(errors='replace'));result=json.loads(run.stdout);need(result['completed'] and result['cases']==14,'All passive-settle controls must pass')
    result.update(inputs=[record(header),record(test),record(Path(__file__))]);save(out/'result.private.json',result);return record(out/'result.private.json')


def build(workspace,base,out):
    tested=check(workspace,out/'startup-settle-host')
    header=ROOT/'native/app/cpu_startup_settle.h';shutil.copyfile(header,out/header.name)
    parent=base['reader'];source_path=Path(base['commands'][0][base['commands'][0].index('-c')+1]);original=source_path.read_text(encoding='utf-8')
    source=out/'main-entry-SELF.private.c';source.write_text(transform(original),encoding='utf-8',newline='\n');artifact=out/'early-SELF.o'
    command=base['commands'][0].copy();command[1:1]=['-I',str(out)];command[command.index('-c')+1]=str(source);command[command.index('-o')+1]=str(artifact)
    if '-MF'in command:command[command.index('-MF')+1]=str(out/'reader.private.d')
    run=subprocess.run(command,capture_output=True,timeout=120,env=dict(os.environ,TMP=str(out),TEMP=str(out)));(out/'reader.private.log').write_bytes(run.stdout+run.stderr)
    need(run.returncode==0,run.stderr.decode(errors='replace')[-3000:])
    return dict(source=record(source),artifact=record(artifact),header=record(out/header.name),source_before=record(source_path),artifact_before=parent,
        host_controls=tested,command=command,maximum_settle_ms=5000,maximum_sleep_calls=500,working_extra_pages=1152,
        original_CPU_floor_unchanged=True,original_30_second_deadline_includes_settle=True,whole_SHA_identity_EOF_unchanged=True,
        no_model_GPU_workers_allocations_source_reads_or_VM_writes_in_settle=True)
