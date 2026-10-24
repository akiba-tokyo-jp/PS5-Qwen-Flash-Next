#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check the actual native VM snapshot function against counter/ABI failures."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    a=parser.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    paths=[ROOT/'native/app/native_main.cpp',ROOT/'tests/native_vm_population.cpp',Path(__file__)]
    def fingerprint():return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()for p in paths}
    r=dict(state='running',inputs=fingerprint(),steps=[],console_requests=0,GPU_calls=0)
    host=a.workspace/'toolchain/msys-clang64/clang64/bin';env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''))
    text=paths[0].read_text();body=text.split('static Json diagnostic_VM_population() {',1)[1].split('\nstruct LoadProgress',1)[0]
    (a.out/'actual_native_vm_population.h').write_text('static Json diagnostic_VM_population() {'+body,encoding='utf-8')
    exe=a.out/'native-VM-population.exe'
    def run(name,cmd):
        result=subprocess.run(list(map(str,cmd)),capture_output=True,env=env,cwd=ROOT,timeout=120)
        (a.out/(name+'.private.log')).write_bytes(result.stdout+result.stderr)
        r['steps'].append(dict(name=name,returncode=result.returncode))
        if result.returncode:raise RuntimeError(result.stderr.decode('utf-8','replace')[-2400:])
        print(name+' passed',flush=True)
    try:
        run('actual_function_compile',[host/'clang++.exe','-std=c++17','-O2','-Wall','-Wextra','-Werror',
            '-I',a.out,ROOT/'tests/native_vm_population.cpp','-o',exe])
        for mode in ('normal','query_failure','size_failure','canary_failure'):run(mode,[exe,mode])
        assert r['inputs']==fingerprint();r['state']='focused_native_VM_population_host_passed_not_console_admitted'
    except BaseException:r['state']='failed';raise
    finally:(a.out/'receipt.private.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
