#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Recover the boot-qualified journal source and require the complete selected object."""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess

from build_performance_quantizer import record
from start_success_route import load,need,save

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();native=load(a.current/'provenance/native-link.receipt.private.json')
    selected=native['resident_bootstrap_namespace'];source=ROOT/'native/app/native_bootstrap.cpp'
    text=source.read_text(encoding='utf-8')
    need(record(source)['sha256']==selected['original']['sha256'],'Complete original journal source differs')
    tree=ast.parse((ROOT/'tools/build_resident_comparison.py').read_text(encoding='utf-8'))
    replacements=[n.value.value for n in ast.walk(tree) if isinstance(n,ast.Assign) and
        any(isinstance(t,ast.Name) and t.id=='replacement' for t in n.targets) and isinstance(n.value,ast.Constant) and
        isinstance(n.value.value,str) and n.value.value.startswith('void path_for_pid(')]
    need(len(replacements)==1,'One pure historical boot namespace replacement required')
    begin=text.index('void path_for_pid(');end=text.index('\nint above_stdio(',begin)
    generated='#include "bootstrap_journal_path.h"\n'+text[:begin]+replacements[0]+text[end:]
    need(hashlib.sha256(generated.encode()).hexdigest()==selected['generated']['sha256'],
         'Complete boot-qualified source must reproduce its recorded SHA256')
    a.out.mkdir(parents=True,exist_ok=False);path=a.out/'native-bootstrap-boot-qualified.private.cpp'
    path.write_text(generated,encoding='utf-8',newline='\n')
    sdk=a.workspace/'toolchain/ps5-sdk-radv/ps5-payload-sdk'
    compiler=a.workspace/'toolchain/llvm-mingw-20261006-ucrt-x86_64/bin/clang++.exe'
    flags=['--no-default-config','--target=x86_64-sie-ps5','-fno-stack-protector','-fno-plt','-femulated-tls',
        '-fdenormal-fp-math=ieee','-fPIC','-std=c++17','-O1','-DNDEBUG','-fvisibility-nodllstorageclass=default',
        '-fexceptions','-fcxx-exceptions','-frtti','-nostdinc++','-isystem',str(sdk/'target/include/c++/v1'),
        '-isystem',str(sdk/'target/include'),'-I',str(ROOT/'native/app'),'-DQWEN_NATIVE_PLATFORM=1']
    attempts=[];found=None
    for opt in ('-O1','-O2','-O3'):
        for sections in ([],['-ffunction-sections','-fdata-sections']):
            current=[opt if x=='-O1' else x for x in flags]+sections
            obj=a.out/('bootstrap-'+str(len(attempts))+'.o')
            command=[str(compiler),*current,'-c',str(path),'-o',str(obj)]
            result=subprocess.run(command,capture_output=True,timeout=120,env=dict(os.environ,TMP=str(a.out),TEMP=str(a.out)))
            (a.out/(str(len(attempts))+'.private.log')).write_bytes(result.stdout+result.stderr)
            need(result.returncode==0,result.stderr.decode(errors='replace')[-2500:])
            value=record(obj);attempts.append(dict(command=command,artifact=value))
            if value['sha256']==selected['object']['sha256']:found=attempts[-1];break
        if found:break
    save(a.out/'result.private.json',dict(completed=bool(found),source=record(path),expected=selected,
        attempts=attempts,exact_object=found,PS5_operations=0,production_adopted=False))
    need(found,'Source is byte-exact, but the selected complete object has not reproduced')
    print(json.dumps(dict(completed=True,source_and_object_byte_exact=True,compiler_attempts=len(attempts),PS5_operations=0)))


if __name__=='__main__':main()
