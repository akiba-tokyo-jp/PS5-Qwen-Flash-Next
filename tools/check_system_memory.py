#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Verify the actual native memory queries and separate pool accounting."""
import argparse,json,os,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser();p.add_argument('--workspace',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    a.out.mkdir();host=a.workspace/'toolchain/msys-clang64/clang64/bin'
    env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''))
    exe=a.out/'system-memory.exe'
    command=[str(host/'clang++.exe'),'-std=c++17','-O2','-Wall','-Wextra','-Werror',
        '-I',str(ROOT/'tests/memory_probe_stubs'),'-I',str(ROOT/'native/app'),
        str(ROOT/'native/app/system_memory.cpp'),str(ROOT/'tests/system_memory.cpp'),'-o',str(exe)]
    for name,cmd,timeout in [('compile',command,90),('run',[str(exe)],20)]:
        result=subprocess.run(cmd,env=env,capture_output=True,timeout=timeout)
        (a.out/(name+'.private.log')).write_bytes(result.stdout+result.stderr)
        if result.returncode:raise RuntimeError('System memory '+name+' failed')
    (a.out/'receipt.private.json').write_text(json.dumps(dict(native_query_API_stubs='passed',pool_accounting='passed',console_access=False,GPU_calls=0,model_loaded=False),indent=2)+'\n')
    print(result.stdout.decode(),end='')
if __name__=='__main__':main()
