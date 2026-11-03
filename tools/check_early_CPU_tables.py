#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Test new CPU mapper, converted zero-hole boundaries and exact failure closure."""
import argparse
import json
import os
from pathlib import Path
import struct
import subprocess
from build_performance_quantizer import record
from early_CPU_tables_completion import FATAL,review
from external_zero_layout import exclude_converted
from native_dispatch import ELF
from start_success_route import load,need,save
ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','package','out'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--resume-after-body',action='store_true',help='Reuse the same already passed actual-C body controls')
    a=p.parse_args();package=load(a.package);early=package['early_CPU_tables']
    if a.resume_after_body:need(a.out.is_dir() and not(a.out/'result.private.json').exists(),'Only the same incomplete host scope may continue')
    else:a.out.mkdir(parents=True,exist_ok=False)
    source=Path(early['source']['path']);need(record(source)==early['source'],'The actual native CPU source changed')
    raw=source.read_text()
    for text in ('#include <ps5platform/kernel.h>\n','#include <sys/sysctl.h>\n','#include "early_CPU_tables_manifest.h"\n',
        'extern void qwen_native_stage(const char*);\n','extern void qwen_native_halt(const char*) __attribute__((noreturn));\n',
        'extern unsigned char __qwen_driver_tables_start[],__qwen_driver_tables_end[],__qwen_early_tables_end[];\n'):
        need(raw.count(text)==1,'One exact host-only declaration adapter required');raw=raw.replace(text,'',1)
    raw=raw.replace('extern const struct original_plan qwen_driver_table_storage;','static struct original_plan qwen_driver_table_storage;',1)
    for i in (101,102):raw=raw.replace('__attribute__((constructor('+str(i)+'))) ','',1)
    (a.out/'early_CPU_tables_under_test.h').write_text(raw,newline='\n')
    (a.out/'early_CPU_tables_manifest.h').write_bytes(Path(early['manifest']['path']).read_bytes())
    host=a.workspace/'toolchain/msys-clang64/clang64/bin';sha=a.workspace/'native/model_hash/sha256.c'
    exe=a.out/'early-CPU-check.exe';test=ROOT/'tests/early_CPU_tables_test.c'
    jobs=[[str(host/'clang.exe'),'-std=c11','-O2','-Wall','-Wextra','-Werror','-I',str(a.out),
        '-I',str(ROOT/'native/app'),'-I',str(sha.parent),str(test),str(sha),'-o',str(exe)],[str(exe)]]
    env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''),TMP=str(a.out),TEMP=str(a.out))
    for i,job in enumerate(jobs):
        if a.resume_after_body:
            need(exe.exists() and test.stat().st_mtime_ns<=exe.stat().st_mtime_ns and
                'early_CPU_actual_body_controls=17 positive=1 refusals=16 OS_mapping_calls=0 GPU_calls=0' in
                (a.out/'1.private.log').read_text(),'Exact passed actual-C controls required');continue
        run=subprocess.run(job,capture_output=True,timeout=45,env=env);(a.out/(str(i)+'.private.log')).write_bytes(run.stdout+run.stderr)
        need(not run.returncode,(run.stdout+run.stderr).decode(errors='replace')[-3500:])
    original=(Path(a.package).parent/'original-zero-tail-converted.elf').read_bytes();begin,end=early['layout']['begin'],early['layout']['end']
    cut,proof=exclude_converted(original,begin,end)
    need(cut==(Path(a.package).parent/'default-libc-parameters.elf').read_bytes(),'The actual post-conversion zero-tail transform differs')
    def mutate(at,fmt,value):
        out=bytearray(original);struct.pack_into(fmt,out,at,value);return bytes(out)
    phoff=struct.unpack_from('<Q',original,32)[0];stride,count=struct.unpack_from('<HH',original,54)
    headers=[struct.unpack_from('<IIQQQQQQ',original,phoff+i*stride) for i in range(count)]
    selected=next(i for i,h in enumerate(headers) if tuple(h)==tuple(proof['original_program']))
    other=next(i for i,h in enumerate(headers) if h[0]==1 and h[3]>=end)
    faults=[(original,begin+16384,end),(original,begin,end-16384),(original,begin,end+65536),
        (mutate(phoff+selected*stride+4,'<I',5),begin,end),
        (mutate(phoff+selected*stride+32,'<Q',begin-headers[selected][3]+1),begin,end),
        (mutate(phoff+other*stride+16,'<Q',begin+65536),begin,end),
        (b'x'+original[1:],begin,end)]
    for values in faults:
        try:exclude_converted(*values)
        except ValueError:pass
        else:raise RuntimeError('An invalid converted zero-tail scope was accepted')
    image=ELF(Path(early['control_native']['path']));names=('__cpu_indicator_init','_GLOBAL__I_000100','early_CPU_tables_map','early_CPU_tables_check')
    addresses=[0x400000+image.symbols[name]['value'] for name in names]
    def entry(i,returned=False):return ('initializer_'+('return' if returned else 'enter')+' index=0x%016x address=0x%016x\n'%(i,addresses[i])).encode()
    prefix=b'bootstrap_completed before_CXX_initializers\nCXX_initializers_begin\n'+entry(0)+entry(0,True)+entry(1)+entry(1,True)+entry(2)
    def row(status,mapped=0,zeroed=0):return ('early_CPU_tables_returned status=%d mapped=%d zeroed=%d checksum=0 mapping_bytes=%d allocation_bytes=%d minimum_free=2000 CPU_IO_returned=1 model_GPU_calls=0\n'%
        (status,mapped,zeroed,9502720 if mapped else 0,9502720 if mapped else 0)).encode()
    good=prefix+row(2)+FATAL;good_second=prefix+row(0,1,1)+entry(2,True)+entry(3)+row(6,1,1)+FATAL
    review(good,image);review(good_second,image)
    bad=[good.replace(b'CPU_IO_returned=1',b'CPU_IO_returned=0'),good.replace(b'status=2',b'status=0'),
        good.replace(FATAL,b'fatal_operation=unrelated\n'),good.replace(entry(1,True),b''),
        good.replace(entry(2),b'initializer_enter index=0x0000000000000004 address=0x0000000000400010\n'),
        good.replace(b'model_GPU_calls=0',b'model_GPU_calls=1'),good.replace(entry(2),entry(2).replace(('%016x'%addresses[2]).encode(),('%016x'%(addresses[2]+16)).encode())),
        good+b'after_failure_operation\n',good_second.replace(row(6,1,1),row(7,1,1))]
    for value in bad:
        try:review(value,image)
        except RuntimeError:pass
        else:raise RuntimeError('An unqualified CPU close boundary was accepted')
    save(a.out/'result.private.json',dict(completed=True,package=record(a.package),source=early['source'],header=early['header'],
        manifest=early['manifest'],native_body_test=record(test),commands=jobs,native_body_positive=1,native_body_refusals=16,
        converted_layout_positive=1,converted_layout_refusals=len(faults),close_boundary_positive=2,close_boundary_refusals=len(bad),
        completion_parser=record(ROOT/'tools/early_CPU_tables_completion.py'),additional_GPU_calls=0,OS_mapping_calls=0,PS5_operations=0,
        already_passed_actual_C_body_controls_reused=a.resume_after_body))
    print(dict(completed=True,native_body_controls=17,converted_layout_controls=8,source_bound_close_controls=11,PS5_operations=0))


if __name__=='__main__':main()
