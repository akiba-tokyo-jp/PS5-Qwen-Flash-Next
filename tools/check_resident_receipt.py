#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Run integrity binding controls against the actual native JSON validator.

Only the JSON validator is extracted: native descriptor ABI calls are exercised
by the separately recorded PS5 title. This tool performs no console requests.
"""
import argparse,json,os,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','cache','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    header=(ROOT/'native/app/resident_launch_integrity.h').read_text()
    first=header.index('inline void validate_resident_launch_receipt')
    last=header.index('inline nlohmann::json verify_resident_launch_integrity',first)
    code=('#include "resident_shader_integrity.h"\n#include <iostream>\n'
          'namespace qwen_app {using ResidentFileIdentity=std::array<std::uint64_t,10>;\n'+header[first:last]+'}\n'+
          (ROOT/'tests/resident_launch_receipt.inc').read_text())
    source=a.out/'receipt-controls.cpp';source.write_text(code,newline='\n')
    runtime=a.workspace/'toolchain/msys-clang64/clang64/bin';exe=a.out/'check.exe'
    command=[runtime/'clang++.exe','-std=c++17','-O2','-I',ROOT/'native/app','-I',
             a.cache/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569/vendor',source,'-o',exe]
    env=dict(os.environ,PATH=str(runtime)+os.pathsep+os.environ.get('PATH',''))
    for i,args in enumerate((command,[exe])):
        result=subprocess.run(list(map(str,args)),capture_output=True,timeout=90,env=env)
        (a.out/f'{i}.log').write_bytes(result.stdout+result.stderr)
        if result.returncode:raise RuntimeError(result.stderr.decode(errors='replace')[-3000:])
    if result.stdout.strip()!=b'47':raise ValueError('All 47 altered binding controls are required')
    receipt=dict(completed=True,negative_controls=47,PS5_operations=0,GPU_calls=0,
                 native_descriptor_ABI_not_exercised=True)
    (a.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt))


if __name__=='__main__':main()
