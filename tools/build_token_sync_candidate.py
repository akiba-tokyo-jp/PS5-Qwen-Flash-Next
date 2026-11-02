#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build paired scoped token-sync wrappers without recompiling the model entry."""
import argparse
import json
import os
from pathlib import Path
import subprocess

from build_performance_quantizer import record
from start_success_route import load,need,save

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','out'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=False)
    retained=load(args.current/'provenance/retained-relink-inputs.private.json')
    entries=[r for r in retained if Path(r['original_path']).name=='entry.o'];need(len(entries)==1,'One current entry provider required')
    entry={k:entries[0][k] for k in ('path','bytes','sha256')}
    need(record(entry['path'])==entry,'Current entry changed')
    llvm=args.workspace/'toolchain/llvm-mingw-20261006-ucrt-x86_64/bin'
    undefined=subprocess.check_output([str(llvm/'llvm-nm.exe'),'--undefined-only',entry['path']],text=True)
    need(all(any(line.split()[-1]==name for line in undefined.splitlines() if line.split()) for name in ('open','fsync','close')),
         'Actual entry must call the three interposed syscalls symbolically')
    sdk=args.workspace/'toolchain/ps5-sdk-radv/ps5-payload-sdk'
    source=ROOT/'native/app/token_ledger_sync_candidate.cpp';header=ROOT/'native/app/token_ledger_sync_gate.h'
    inputs=[record(source),record(header)];artifacts={};commands=[]
    test=ROOT/'tests/token_ledger_sync_gate_test.cpp';inputs.append(record(test))
    host=args.workspace/'toolchain/msys-clang64/clang64/bin/clang++.exe'
    binary=args.out/'token-sync-gate-check.exe'
    test_jobs=[[str(host),'-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'native/app'),
                str(test),'-o',str(binary)],[str(binary)]]
    for i,command in enumerate(test_jobs):
        result=subprocess.run(command,capture_output=True,timeout=90,env=dict(os.environ,
            PATH=str(host.parent)+os.pathsep+os.environ.get('PATH',''),TMP=str(args.out),TEMP=str(args.out)))
        (args.out/('host-check-'+str(i)+'.private.log')).write_bytes(result.stdout+result.stderr)
        need(result.returncode==0,result.stderr.decode(errors='replace')[-3000:]);commands.append(command)
    for arm,flag in (('control',0),('candidate',1)):
        obj=args.out/(arm+'-token-sync.o')
        command=[str(llvm/'clang++.exe'),'--no-default-config','--target=x86_64-sie-ps5','-nostdinc++',
            '-isystem',str(sdk/'target/include/c++/v1'),'-isystem',str(sdk/'target/include'),'-std=c++17',
            '-femulated-tls','-fno-stack-protector','-fno-plt','-fPIC','-O2','-ffunction-sections','-fdata-sections',
            '-DQWEN_PERF_REQUEST_END_SYNC='+str(flag),'-I',str(ROOT/'native/app'),'-c',str(source),'-o',str(obj)]
        result=subprocess.run(command,capture_output=True,timeout=90,env=dict(os.environ,TMP=str(args.out),TEMP=str(args.out)))
        (args.out/(arm+'.private.log')).write_bytes(result.stdout+result.stderr)
        need(result.returncode==0,result.stderr.decode(errors='replace')[-3000:])
        artifacts[arm]=record(obj);commands.append(command)
    need(all(record(r['path'])==r for r in inputs) and record(entry['path'])==entry,'Source inputs changed during compilation')
    report=dict(completed=True,artifacts=artifacts,commands=commands,inputs=inputs,actual_entry=entry,
        link_flags=['--wrap=open','--wrap=fsync','--wrap=close'],exact_three_owned_ledger_names_only=True,
        candidate_durability='request_end',control_durability='per_token',close_flush_before_success=True,
        descriptor_isolation_reuse_capacity_and_fault_injection_passed=True,
        interrupted_request_tail_may_be_lost=True,PS5_operations=0,native_speed_or_quality_measured=False,production_adopted=False)
    save(args.out/'result.private.json',report)
    print(json.dumps({k:v for k,v in report.items() if k not in ('artifacts','commands','inputs','actual_entry','link_flags')}))


if __name__=='__main__':main()
