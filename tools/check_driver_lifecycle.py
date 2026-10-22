#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Host API-stub tests for the actual native frontend and per-BO owner source."""
import argparse
import json
import os
from pathlib import Path
import subprocess
from driver_inputs import sha
ROOT = Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','cache'): parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    host=args.workspace/'toolchain/msys-clang64/clang64/bin'
    out=args.cache/'build/driver-lifecycle-check';out.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''))
    cases=[('frontend',[str(host/'clang++.exe'),'-std=c++17','-O2','-Wall','-Wextra','-Werror',
        '-I',str(ROOT/'native/app'),str(ROOT/'native/app/driver_lifecycle.cpp'),str(ROOT/'tests/driver_lifecycle.cpp'),'-o',str(out/'frontend.exe')]),
        ('perbo',[str(host/'clang.exe'),'-std=gnu11','-O2','-Wall','-Wextra','-Werror','-Wno-unused-function',
        '-I',str(ROOT/'native/driver'),'-I',str(args.workspace/'vendor/PS5_Mesa/src/amd/vulkan/winsys/ps5'),
        '-DPS5_AI_MOSS_TRIAL_10G=1',str(ROOT/'tests/native_perbo.c'),'-o',str(out/'perbo.exe')]),
        ('journal',[str(host/'clang.exe'),'-std=gnu11','-O2','-Wall','-Wextra','-Werror','-Wno-unused-function',
        '-I',str(ROOT/'native/driver'),str(ROOT/'tests/driver_journal.c'),'-o',str(out/'journal.exe')])]
    receipt={'console_access':False,'GPU_executed':False,'steps':[],
        'sources':[{'path':str(path),'sha256':sha(path)}for path in sorted((ROOT/'native/driver').iterdir())if path.is_file()]}
    for name,command in cases:
        for phase,cmd in [('compile',command),('API_stubs',[str(out/(name+'.exe'))])]:
            result=subprocess.run(cmd,env=env,capture_output=True,timeout=90)
            (out/(name+'-'+phase+'.private.log')).write_bytes(result.stdout+result.stderr)
            receipt['steps'].append({'name':name+'_'+phase,'returncode':result.returncode})
            (out/'receipt.private.json').write_text(json.dumps(receipt,indent=2)+'\n')
            if result.returncode:raise RuntimeError(result.stderr.decode('utf-8','replace'))
            print(name+' '+phase+' passed: '+result.stdout.decode('utf-8','replace').strip(),flush=True)
if __name__=='__main__':main()
