#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check exact Direct integrity streaming and compile the actual PS5 provider; no console access."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workspace',type=Path,required=True);p.add_argument('--cache',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    lock=json.loads((ROOT/'native/qwen_flash_next/dependencies.lock.json').read_text())
    source=a.cache/'upstream'/('llama.cpp-'+lock['llama_cpp']['revision'])
    sdk=a.workspace/'toolchain/ps5-sdk-radv/ps5-payload-sdk'
    host=a.workspace/'toolchain/msys-clang64/clang64/bin';target=a.workspace/'toolchain/llvm-mingw-20261006-ucrt-x86_64/bin'
    env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''))
    paths=[ROOT/name for name in ('native/app/direct_integrity.h','native/app/direct_integrity.cpp',
        'native/app/sha256_backend.cpp','tests/direct_integrity.cpp','tools/check_direct_integrity.py')]
    before={str(path.relative_to(ROOT)):sha(path)for path in paths}
    receipt=dict(schema='ps5-qwen-direct-startup-integrity-host-v1',inputs=before,steps=[],console_requests=0,GPU_calls=0)
    def run(label,cmd):
        result=subprocess.run(list(map(str,cmd)),cwd=ROOT,env=env,capture_output=True,timeout=120)
        (a.out/(label+'.private.log')).write_bytes(result.stdout+result.stderr)
        receipt['steps'].append(dict(name=label,returncode=result.returncode))
        if result.returncode:raise RuntimeError(result.stderr.decode('utf-8','replace')[-4000:])
        print(label+' passed',flush=True)
    try:
        exe=a.out/'direct-integrity.exe'
        run('actual_stream_compile',[host/'clang++.exe','-std=c++17','-O2','-Wall','-Wextra','-Werror',
            '-I',ROOT/'native/app','-I',source/'vendor','-I',source/'vendor/hash',ROOT/'native/app/sha256_backend.cpp',ROOT/'tests/direct_integrity.cpp','-o',exe])
        data=bytes(range(256))*8192+b'non-aligned-original-EOF-tail'*37
        fixture=a.out/'fixture.private.bin';fixture.write_bytes(data)
        run('original_SHA256_EOF_failure_deadline_controls',[exe,fixture,hashlib.sha256(data).hexdigest()])
        run('actual_PS5_provider_compile',[target/'clang++.exe','--no-default-config','--target=x86_64-sie-ps5',
            '-fno-stack-protector','-fno-plt','-femulated-tls','-fPIC','-std=c++17','-O1','-fexceptions','-fcxx-exceptions','-frtti','-nostdinc++',
            '-isystem',sdk/'target/include/c++/v1','-isystem',sdk/'target/include','-I',ROOT/'native/app','-I',source/'vendor','-I',source/'vendor/hash',
            '-Wall','-Wextra','-Werror','-c',ROOT/'native/app/direct_integrity.cpp','-o',a.out/'direct-integrity-PS5.o'])
        assert before=={str(path.relative_to(ROOT)):sha(path)for path in paths}
        receipt.update(state='focused_direct_integrity_host_passed_not_console_admitted',
            buffer_bytes=1<<20,alignment_bytes=16384,exact_original_SHA256=True,unaligned_EOF_tail=True,
            short_and_negative_reads_rejected=True,operation_retries=0)
    except BaseException:
        receipt['state']='failed';raise
    finally:(a.out/'receipt.private.json').write_text(json.dumps(receipt,indent=2)+'\n')
if __name__=='__main__':main()
