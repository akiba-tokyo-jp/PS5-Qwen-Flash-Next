#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Run the actual source planner using hash-checked captured backing metadata."""
import argparse,json,os,subprocess
from pathlib import Path
from expert_q4 import require,record,write_json
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('native-build','policy','candidate','workspace','cache','out'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    names=['expert_all_q2_source_integrity.h','expert_q2_composite_source.h','resident_all_q8_source.h','resident_output_q8_source.h','resident_shared_q8_source.h','precision_overlay_receipt.h']
    previous=a.cache/'build/Resident-Q8-source-map-11498/expert_q2_composite_source.h';old=previous.read_text();stub=old[old.index('#else\ninline nlohmann::json expert_q2_backing_metadata'):old.index('\n#endif',old.index('#else\ninline nlohmann::json expert_q2_backing_metadata'))]
    sources=[]
    for name in names:
        path=ROOT/'native/app'/name;text=path.read_text();sources.append(record(path))
        if name=='expert_q2_composite_source.h':
            begin=text.index('#else\ninline nlohmann::json expert_q2_backing_metadata');end=text.index('\n#endif',begin)
            require('Native backing metadata requires the PS5 descriptor ABI'in text[begin:end],'Only the unavailable Windows I/O stub may be replaced')
            text=text[:begin]+stub+text[end:]
        (a.out/name).write_text(text,newline='\n')
    up=a.cache/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569';host=a.workspace/'toolchain/msys-clang64/clang64/bin'
    env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''))
    commands=[
        [str(host/'clang.exe'),'-c',str(up/'vendor/hash/sha256/sha256.c'),'-I'+str(up/'vendor/hash'),'-o',str(a.out/'sha.o')],
        [str(host/'clang++.exe'),'-std=c++17','-O0','-I'+str(a.out),'-I'+str(ROOT/'native/app'),'-I'+str(a.native_build),'-I'+str(up/'vendor'),str(ROOT/'tests/precision_source_plan.cpp'),str(a.out/'sha.o'),'-o',str(a.out/'source-plan.exe')]]
    for i,command in enumerate(commands):
        r=subprocess.run(command,capture_output=True,timeout=180,env=env);(a.out/f'{i}.private.log').write_bytes(r.stdout+r.stderr);require(r.returncode==0,r.stderr.decode(errors='replace')[-3000:])
    command=[str(a.out/'source-plan.exe'),str(a.policy),str(a.candidate),*[str(a.cache/path)for path in ('resident-shared-Q8-10456/model-receipt.json','resident-output-Q8-9193/model-receipt.json','Expert-all-Q2-receipt-8652.json')]]
    r=subprocess.run(command,capture_output=True,timeout=60,env=env);(a.out/'result.private.log').write_bytes(r.stdout+r.stderr)
    write_json(a.out/'result.private.json',dict(completed=True,passed=r.returncode==0,actual_native_source_planner_predicates_preserved=True,
        only_Windows_unavailable_IO_stub_replaced=True,backing_metadata_whole_SHA256_verified=True,native_descriptor_ABI_execution_claimed=False,
        PS5_operations=0,policy=record(a.policy),candidate=record(a.candidate),native_plan=record(a.native_build/'precision-plan.private.h'),sources=sources,commands=commands))
    require(r.returncode==0,r.stderr.decode(errors='replace'));print(r.stdout.decode(),end='')

if __name__=='__main__':main()
