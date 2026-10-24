#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise the actual bounded bootstrap probe and compile its PS5 provider."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    a=parser.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    host=a.workspace/'toolchain/msys-clang64/clang64/bin';target=a.workspace/'toolchain/llvm-mingw-20261006-ucrt-x86_64/bin'
    sdk=a.workspace/'toolchain/ps5-sdk-radv/ps5-payload-sdk'
    paths=[ROOT/p for p in ('native/app/native_bootstrap.cpp','native/app/stage_memory_probe.h',
        'tests/stage_memory_probe.cpp','tests/stage_probe_stubs/sys/sysctl.h','tools/check_stage_memory_probe.py')]
    def fingerprint():return{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()for p in paths}
    receipt=dict(state='running',inputs=fingerprint(),steps=[],console_requests=0,GPU_calls=0)
    env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''))
    def run(label,command):
        result=subprocess.run(list(map(str,command)),capture_output=True,env=env,cwd=ROOT,timeout=120)
        (a.out/(label+'.private.log')).write_bytes(result.stdout+result.stderr)
        receipt['steps'].append(dict(name=label,returncode=result.returncode))
        if result.returncode:raise RuntimeError(result.stderr.decode('utf-8','replace')[-2400:])
        print(label+' passed',flush=True)
    try:
        exe=a.out/'actual-bootstrap-probe.exe'
        run('actual_bootstrap_host_compile',[host/'clang++.exe','-std=c++17','-O2','-Wall','-Wextra','-Werror',
            '-I',ROOT/'tests/stage_probe_stubs',ROOT/'tests/stage_memory_probe.cpp','-o',exe])
        for mode in ('normal','capacity','counter_failure','short_write'):run(mode,[exe,mode])
        run('actual_PS5_bootstrap_compile',[target/'clang++.exe','--no-default-config','--target=x86_64-sie-ps5',
            '-fno-stack-protector','-fno-plt','-femulated-tls','-fPIC','-std=c++17','-O1','-fexceptions','-fcxx-exceptions','-frtti','-nostdinc++',
            '-isystem',sdk/'target/include/c++/v1','-isystem',sdk/'target/include',
            '-Wall','-Wextra','-Werror','-c',ROOT/'native/app/native_bootstrap.cpp','-o',a.out/'actual-bootstrap-PS5.o'])
        assert receipt['inputs']==fingerprint();receipt['state']='focused_stage_memory_probe_host_passed_not_console_admitted'
    except BaseException:receipt['state']='failed';raise
    finally:(a.out/'receipt.private.json').write_text(json.dumps(receipt,indent=2)+'\n')
if __name__=='__main__':main()
