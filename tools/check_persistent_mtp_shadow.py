#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Host-check causal MTP state transitions and compile the bounded PS5 shadow."""
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
    for name in ('workspace','current','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    app=ROOT/'native/app';up=a.current.parent/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569'
    sdk=a.workspace/'toolchain/ps5-sdk-radv/ps5-payload-sdk/target/include'
    host=a.workspace/'toolchain/msys-clang64/clang64/bin';target=a.workspace/'toolchain/llvm-mingw-20261006-ucrt-x86_64/bin'
    test=a.out/'causal-cursor-test.exe';obj=a.out/'persistent-mtp-shadow.o'
    sources=[app/name for name in ('persistent_mtp_cursor.h','persistent_mtp_shadow.h','persistent_mtp_shadow.cpp','session.h')]
    sources += [ROOT/'tests/persistent_mtp_cursor_test.cpp',up/'src/llama-ext.h',up/'include/llama.h']
    inputs=[record(path) for path in sources]
    hc=[str(host/'clang++.exe'),'-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(app),str(sources[4]),'-o',str(test)]
    tc=[str(target/'clang++.exe'),'--no-default-config','--target=x86_64-sie-ps5','-nostdinc++',
        '-isystem',str(sdk/'c++/v1'),'-isystem',str(sdk),'-std=c++17','-fexceptions','-fcxx-exceptions','-femulated-tls',
        '-fno-stack-protector','-fno-plt','-fPIC','-O2','-ffunction-sections','-fdata-sections','-Wall','-Wextra','-Werror',
        '-I',str(app),'-I',str(up/'include'),'-I',str(up/'src'),'-I',str(up/'ggml/include'),'-I',str(up/'vendor'),
        '-c',str(app/'persistent_mtp_shadow.cpp'),'-o',str(obj)]
    commands=[hc,[str(test)],tc];env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''),TMP=str(a.out),TEMP=str(a.out))
    for i,command in enumerate(commands):
        result=subprocess.run(command,capture_output=True,timeout=240,env=env);(a.out/(str(i)+'.private.log')).write_bytes(result.stdout+result.stderr)
        need(result.returncode==0,result.stderr.decode(errors='replace')[-4000:])
    need(all(record(row['path'])==row for row in inputs),'A checked shadow source changed during compilation')
    save(a.out/'result.private.json',dict(completed=True,causal_single_reject_accept_catchup_bonus_EOG_controls_passed=True,
        target_compiled=True,artifact=record(obj),inputs=inputs,commands=commands,model_loads=0,GPU_calls=0,PS5_operations=0,
        native_context_memory_geometry_qualified=False,native_proposal_accuracy_or_speed_qualified=False,production_adopted=False))
    print(json.dumps(dict(completed=True,host_causal_controls_passed=True,target_compiled=True,PS5_operations=0)))


if __name__=='__main__':main()
