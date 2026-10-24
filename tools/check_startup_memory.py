#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise the actual startup-read provider with bounded memory admission."""
import argparse,hashlib,json,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','cache','out'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=False)
    paths=[ROOT/name for name in ('native/app/native_main.cpp','native/app/direct_integrity.cpp','native/app/direct_integrity.h',
        'native/app/memory_backpressure.h','native/app/system_memory.h','tests/startup_memory.cpp','tests/memory_backpressure.cpp',
        'tools/check_startup_memory.py')]
    def inputs():return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()for p in paths}
    initial=inputs();receipt=dict(inputs=initial,steps=[],console_requests=0,GPU_calls=0)
    host=args.workspace/'toolchain/msys-clang64/clang64/bin'
    env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''))
    def run(label,command):
        result=subprocess.run(list(map(str,command)),cwd=ROOT,env=env,capture_output=True,timeout=150)
        (args.out/(label+'.private.log')).write_bytes(result.stdout+result.stderr)
        receipt['steps'].append(dict(name=label,returncode=result.returncode))
        if result.returncode:raise RuntimeError(result.stderr.decode('utf-8','replace')[-3000:])
        print(label+' passed',flush=True)
    try:
        source=(ROOT/'native/app/direct_integrity.cpp').read_text()
        start=source.index('struct NativeDirect final:DirectIntegrityOps {')
        end=source.index('\n};',start)+3
        (args.out/'native_direct_fixture.h').write_text(source[start:end],encoding='utf-8')
        executable=args.out/'actual-startup-provider.exe'
        flags=[host/'clang++.exe','-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',ROOT/'native/app','-I',args.out]
        run('actual_provider_host_compile',[*flags,ROOT/'tests/startup_memory.cpp','-o',executable])
        run('actual_provider_admission_faults',[executable])
        executable=args.out/'memory-backpressure.exe'
        run('shared_controller_compile',[*flags,ROOT/'tests/memory_backpressure.cpp','-o',executable])
        run('shared_controller_original_bounds',[executable])
        run('actual_stream_and_PS5_provider',[sys.executable,'-B',ROOT/'tools/check_direct_integrity.py',
            '--workspace',args.workspace,'--cache',args.cache,'--out',args.out/'stream'])
        assert inputs()==initial
        receipt.update(state='focused_startup_memory_host_passed_not_console_admitted',
            actual_provider_class_executed=True,memory_predicates_and_reserves_unchanged=True,
            shared_boundary_ms=20000,shared_process_ms=60000,reads_retried=0)
    except BaseException:receipt['state']='failed';raise
    finally:(args.out/'receipt.private.json').write_text(json.dumps(receipt,indent=2)+'\n')
if __name__=='__main__':main()
