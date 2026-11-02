#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Run ledger fault-injection controls and compile the native POSIX adapter."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=False)
    host=args.workspace/'toolchain/msys-clang64/clang64/bin/clang++.exe'
    target=args.workspace/'toolchain/llvm-mingw-20261006-ucrt-x86_64/bin/clang++.exe'
    sdk=args.workspace/'toolchain/ps5-sdk-radv/ps5-payload-sdk/target/include'
    env=dict(os.environ,PATH=str(host.parent)+os.pathsep+os.environ.get('PATH',''),
             TMP=str(args.out),TEMP=str(args.out))
    binary=args.out/'bounded-token-writer.exe'
    adapter=args.out/'ledger-adapter.cpp'
    adapter.write_text('#include "durable_token_ledger.h"\n'
                       'struct Json {std::string dump()const{return "{}";}};\n'
                       'void instantiate(){qwen_service::TokenLedger strict;strict.append("/data/unused",Json{});strict.close();\n'
                       'qwen_service::TokenLedgerPolicy p;p.durability=qwen_service::TokenDurability::request_end;\n'
                       'qwen_service::TokenLedger deferred(p);deferred.append("/data/unused",Json{});deferred.close();}\n',
                       encoding='utf-8',newline='\n')
    jobs=[
        [str(host),'-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'native/app'),
         str(ROOT/'tests/bounded_token_writer_test.cpp'),'-o',str(binary)],
        [str(binary)],
        [str(target),'--no-default-config','--target=x86_64-sie-ps5','-nostdinc++',
         '-isystem',str(sdk/'c++/v1'),'-isystem',str(sdk),'-std=c++17','-femulated-tls','-fexceptions','-fcxx-exceptions',
         '-Wall','-Wextra','-Werror','-I',str(ROOT/'native/app'),'-fsyntax-only',str(adapter)],
    ]
    for i,job in enumerate(jobs):
        r=subprocess.run(job,capture_output=True,timeout=90,env=env)
        (args.out/f'{i}.private.log').write_bytes(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError(f'Ledger check {i} failed: '+r.stderr.decode(errors='replace')[-3000:])
    files=[Path(__file__),ROOT/'native/app/bounded_token_writer.h',ROOT/'native/app/durable_token_ledger.h',
           ROOT/'tests/bounded_token_writer_test.cpp']
    result=dict(completed=True,host_fault_injection_passed=True,native_adapter_syntax_passed=True,
                default_durability='per_token',experimental_durability='request_end',
                synthetic_256_record_sync_calls=dict(per_token=256,request_end=1),
                identical_complete_record_bytes=True,PS5_operations=0,native_speed_measured=False,
                production_adopted=False,commands=jobs,
                inputs=[dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in files])
    (args.out/'result.private.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('commands','inputs')}))


if __name__=='__main__':main()
