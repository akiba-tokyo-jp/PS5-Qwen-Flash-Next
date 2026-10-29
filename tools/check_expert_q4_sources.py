#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Validate actual mixed-source admission and malformed-source refusals offline."""
import argparse,json,os,subprocess
from pathlib import Path
from expert_q4 import LOCK,record,require,write_json
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('workspace','cache','receipt','source-integrity','out'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    sealed=json.loads(a.source_integrity.read_text());bound=record(a.receipt)
    require(sealed['model_receipt_sha256']==bound['sha256'],'Exact published model receipt required')
    gate=dict(model_receipt_sha256=bound['sha256'],model_receipt_bytes=bound['bytes'],
        Expert_Q4_source_integrity=dict(schema='ps5-qwen-expert-q4-source-policy-v1',raw=a.source_integrity.read_bytes().decode('utf-8'),sha256=record(a.source_integrity)['sha256']))
    policy=a.out/'source-gate.private.json';write_json(policy,gate)
    host=a.workspace/'toolchain/msys-clang64/clang64/bin';upstream=a.cache/'upstream'/('llama.cpp-'+LOCK['llama_cpp']['revision'])
    env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''));sha=a.out/'SHA256.o';exe=a.out/'Q4-source-integrity.exe'
    commands=[[host/'clang.exe','-std=c11','-O2','-I',upstream/'vendor','-I',upstream/'vendor/hash', '-c',upstream/'vendor/hash/sha256/sha256.c','-o',sha],
        [host/'clang++.exe','-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',ROOT/'native/app','-I',upstream/'vendor',
         ROOT/'tests/expert_q4_source_integrity.cpp',ROOT/'native/app/model_integrity.cpp',sha,'-o',exe],
        [exe,a.receipt,policy]]
    before=[record(x)for x in (Path(__file__),a.receipt,a.source_integrity,ROOT/'tests/expert_q4_source_integrity.cpp',
        ROOT/'native/app/expert_q4_source_integrity.h',ROOT/'native/app/expert_q4_receipt.h',ROOT/'native/app/split_model_integrity.h',ROOT/'native/app/model_integrity.cpp')]
    for i,command in enumerate(commands):
        result=subprocess.run(list(map(str,command)),capture_output=True,timeout=120,env=env)
        (a.out/f'{i}.private.log').write_bytes(result.stdout+result.stderr);require(result.returncode==0,result.stderr.decode(errors='replace')[-4000:])
    for row in before:require(record(row['path'])==row,'Offline source gate input changed')
    write_json(a.out/'receipt.private.json',dict(completed=True,PS5_operations=0,inputs=before,gate=record(policy),
        executable=record(exe),commands=[list(map(str,command))for command in commands],native_result=json.loads(result.stdout)))
    print(result.stdout.decode(),end='')
if __name__=='__main__':main()
