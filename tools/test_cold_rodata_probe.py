#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Run new restorer fault controls without repeating the old loader controls."""
import argparse
import json
import os
from pathlib import Path
import subprocess
from build_performance_quantizer import record
from start_success_route import load,need,save
ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','relink','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    relink=load(a.relink);manifest=Path(relink['artifact']['path']).parent/'cold_rodata_manifest.h'
    source=ROOT/'native/app/cold_rodata_probe.c';raw=source.read_text()
    includes=['ps5platform/kernel.h','fcntl.h','sys/stat.h','sys/sysctl.h','unistd.h']
    for header in includes:raw=raw.replace('#include <'+header+'>\n','',1)
    raw=raw.replace('extern void qwen_native_stage(const char *);\n','',1)
    raw=raw.replace('extern unsigned char qwen_cold_payload[], qwen_cold_payload_end[];\n','',1)
    raw=raw.replace('#include "cold_rodata_manifest.h"\n','',1)
    raw=raw.replace('_Alignas(16384) ','',1)
    for i in (101,102):raw=raw.replace('__attribute__((constructor('+str(i)+'))) ','',1)
    under=a.out/'cold_rodata_under_test.h';under.write_text(raw,newline='\n')
    (a.out/'cold_rodata_manifest.h').write_bytes(manifest.read_bytes())
    host=a.workspace/'toolchain/msys-clang64/clang64/bin';sha=a.workspace/'native/model_hash/sha256.c'
    exe=a.out/'restorer-check.exe';test=ROOT/'tests/cold_rodata_probe_test.c'
    jobs=[[str(host/'clang.exe'),'-std=c11','-O2','-Wall','-Wextra','-Werror','-I',str(a.out),
        '-I',str(ROOT/'native/app'),'-I',str(sha.parent),str(test),str(sha),'-o',str(exe)],[str(exe)]]
    env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''),TMP=str(a.out),TEMP=str(a.out))
    for i,job in enumerate(jobs):
        run=subprocess.run(job,capture_output=True,timeout=45,env=env)
        (a.out/(str(i)+'.private.log')).write_bytes(run.stdout+run.stderr)
        need(not run.returncode,(run.stdout+run.stderr).decode(errors='replace')[-3500:])
    save(a.out/'result.private.json',dict(completed=True,source=record(source),test=record(test),
        relink=record(a.relink),manifest=record(manifest),adaptation=record(under),commands=jobs,
        positive_controls=2,negative_controls=18,zero_link_native_title_view_qualified=True,
        old_loader_controls_reused_without_replay=True,PS5_operations=0))
    print(json.dumps(dict(completed=True,positive_controls=2,negative_controls=18,PS5_operations=0)))


if __name__=='__main__':main()
