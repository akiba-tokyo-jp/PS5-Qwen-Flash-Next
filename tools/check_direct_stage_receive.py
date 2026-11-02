#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compile the actual Direct receiver against a host-only fault transport."""
import argparse
import json
import os
from pathlib import Path
import subprocess

from build_performance_quantizer import record
from start_success_route import need,save

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workspace',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=False)
    source=ROOT/'native/qwen_flash_next/direct_stage_receive.h';text=source.read_text(encoding='utf-8')
    for header in ('sys/socket.h','netinet/in.h','sys/time.h'):
        line='#include <'+header+'>\n';need(text.count(line)==1,'Only three system declarations may be replaced by the mock ABI')
        text=text.replace(line,'',1)
    declaration='static _Alignas(16384) unsigned char direct_stage_window[16384];'
    need(text.count(declaration)==1,'One production window declaration required')
    text=text.replace(declaration,'static unsigned char *direct_stage_window;',1)
    copied=a.out/'direct_stage_under_test.h';copied.write_text(text,encoding='utf-8',newline='\n')
    test=ROOT/'tests/direct_stage_receive_test.c';sha=a.workspace/'native/model_hash/sha256.c'
    host=a.workspace/'toolchain/msys-clang64/clang64/bin';compiler=host/'clang.exe';exe=a.out/'direct-stage-test.exe'
    env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''))
    command=[str(compiler),'-std=c11','-O2','-Wall','-Wextra','-Werror','-I',str(a.out),
             '-I',str(sha.parent),str(test),str(sha),'-o',str(exe)]
    built=subprocess.run(command,capture_output=True,timeout=120,env=env);(a.out/'build.private.log').write_bytes(built.stdout+built.stderr)
    need(built.returncode==0,built.stderr.decode(errors='replace')[-3000:])
    run=subprocess.run([str(exe)],capture_output=True,timeout=20,env=env);(a.out/'run.private.log').write_bytes(run.stdout+run.stderr)
    need(run.returncode==0,run.stderr.decode(errors='replace'));result=json.loads(run.stdout)
    need(result['completed'] and result['returned_transport_and_file_cases']==14 and result['OS_objects']==0,'Every bounded fault control must return')
    result.update(inputs=[record(path) for path in (source,test,sha,Path(__file__))],
                  tested_header=record(copied),system_headers_and_PE_static_alignment_only_replaced=True,
                  actual_receiver_control_flow_unchanged=True,host_window_still_16384_aligned=True,command=command,
                  target_network_support_qualified=False,native_Direct_IO_qualified=False)
    save(a.out/'result.private.json',result);print(json.dumps({key:result[key] for key in ('completed','returned_transport_and_file_cases','PS5_operations')}))


if __name__=='__main__':main()
