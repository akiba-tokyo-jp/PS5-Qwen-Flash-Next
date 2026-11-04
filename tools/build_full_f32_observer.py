#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build a bounded qualification observer for existing full-vocabulary CPU rows."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess

from build_performance_quantizer import record
from start_success_route import load,need,save

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','recovered','out'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=False)
    recovered=load(args.recovered);need(recovered['completed'] and recovered['object_byte_exact'],'Actual current entry required')
    rows=load(args.current/'provenance/retained-relink-inputs.private.json')
    engine=next(r for r in rows if Path(r['original_path']).name=='engine.o')
    need(record(engine['path'])=={k:engine[k] for k in ('path','bytes','sha256')},'Retained engine changed')
    llvm=args.workspace/'toolchain/llvm-mingw-20261006-ucrt-x86_64/bin'
    symbols=subprocess.check_output([str(llvm/'llvm-nm.exe'),'--defined-only','--extern-only',engine['path']],text=True)
    setters=[s.split()[-1] for s in symbols.splitlines() if 'set_logits_observer' in s]
    need(len(setters)==1 and setters[0]=='_ZN8qwen_app11LlamaEngine19set_logits_observerENSt3__18functionIFvPKfmEEE',
         'One actual completed-row observer with the matching libc++ function ABI required')
    old=load(recovered['recovered']['path']);prep=load(old['selected_precision_preparation']['path'])
    metadata=next(r for r in old['outputs'] if r['sha256']==prep['candidate']['sha256'])
    need(record(metadata['path'])==metadata,'Recovered current model metadata changed')
    receipt=load(metadata['path']);weight=next(t for t in receipt['tensors'] if t['name']=='output.weight')
    columns=weight['shape'][1];need(columns==248320,'The actual current vocabulary geometry is required')
    upstream=args.current.parent/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569'
    source=ROOT/'native/app/full_f32_observer.cpp';test=ROOT/'tests/full_f32_observer_test.cpp'
    host=args.workspace/'toolchain/msys-clang64/clang64/bin/clang++.exe'
    env=dict(os.environ,PATH=str(host.parent)+os.pathsep+os.environ.get('PATH',''),TMP=str(args.out),TEMP=str(args.out))
    commands=[]
    def run(command,name):
        value=subprocess.run(command,capture_output=True,timeout=180,env=env);commands.append(command)
        (args.out/(name+'.private.log')).write_bytes(value.stdout+value.stderr)
        need(value.returncode==0,value.stderr.decode(errors='replace')[-3500:]);return value.stdout
    executable=args.out/'observer-check.exe'
    run([str(host),'-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'native/app'),
         '-I',str(upstream/'vendor'),'-I',str(upstream/'vendor/hash'),str(test),str(ROOT/'native/app/sha256_backend.cpp'),'-o',str(executable)],'host-compile')
    stdout=run([str(executable)],'host-run')
    expected=hashlib.sha256(struct.pack('<4f',1,-2.5,0,3)).hexdigest().encode()
    need(b'sha256='+expected in stdout,'Independent full-row byte digest or observer forwarding failed')
    sdk=args.workspace/'toolchain/ps5-sdk-radv/ps5-payload-sdk/target/include';obj=args.out/'full-f32-observer.o'
    command=[str(llvm/'clang++.exe'),'--no-default-config','--target=x86_64-sie-ps5','-nostdinc++',
        '-isystem',str(sdk/'c++/v1'),'-isystem',str(sdk),'-std=c++17','-fexceptions','-fcxx-exceptions',
        '-femulated-tls','-fno-stack-protector','-fno-plt','-fPIC','-O2','-ffunction-sections','-fdata-sections',
        '-DQWEN_F32_OBSERVER_SETTER='+json.dumps(setters[0]),'-DQWEN_F32_OBSERVER_COLUMNS='+str(columns),
        '-I',str(upstream/'vendor'),'-c',str(source),'-o',str(obj)]
    run(command,'native-compile')
    report=dict(completed=True,artifact=record(obj),engine=engine,model_metadata=metadata,columns=columns,
        link_flags=['--wrap='+setters[0]],commands=commands,inputs=[record(source),record(test)],
        host_forwarding_clear_and_geometry_fault_controls_passed=True,independent_SHA256_fixture_passed=True,
        maximum_rows_per_request=33,row_copies=0,extra_GPU_downloads=0,model_or_GPU_calls_added=0,
        qualification_only=True,performance_timings_usable=False,native_qualified=False,PS5_operations=0)
    save(args.out/'result.private.json',report)
    print(json.dumps({k:v for k,v in report.items() if k not in ('artifact','engine','model_metadata','commands','inputs','link_flags')}))


if __name__=='__main__':main()
