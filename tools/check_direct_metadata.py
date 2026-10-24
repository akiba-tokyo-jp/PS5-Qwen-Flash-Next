#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check exact bounded GGUF metadata parsing and the actual PS5 Direct provider."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','cache','model-directory','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    lock=json.loads((ROOT/'native/qwen_flash_next/dependencies.lock.json').read_text())
    base=a.cache/'upstream'/('llama.cpp-'+lock['llama_cpp']['revision']);host=a.workspace/'toolchain/msys-clang64/clang64/bin'
    target=a.workspace/'toolchain/llvm-mingw-20261006-ucrt-x86_64/bin';sdk=a.workspace/'toolchain/ps5-sdk-radv/ps5-payload-sdk'
    paths=[ROOT/n for n in ('native/app/direct_metadata.h','native/app/direct_metadata.cpp','native/app/mapped_source.h',
        'native/app/mapped_source.cpp','native/app/paired_source_io.h','native/app/native_main.cpp','tools/build_native.py',
        'tests/direct_metadata.cpp','tests/mapped_source.cpp','tools/check_direct_metadata.py')]
    def fingerprint():return {str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest()for f in paths}
    libraries=[]
    for name in ('ggml.a','ggml-cpu.a','ggml-base.a'):
        rows=list((a.cache/'host-CPU-reference-066/build').rglob(name))+list((a.cache/'host-CPU-reference-066/build').rglob('lib'+name));assert len(rows)==1
        libraries.append(rows[0])
    r=dict(state='running',inputs=fingerprint(),steps=[],files=[],console_requests=0,GPU_calls=0,
        libraries=[dict(path=str(f),sha256=hashlib.sha256(f.read_bytes()).hexdigest())for f in libraries])
    env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''))
    def run(label,cmd):
        x=subprocess.run(list(map(str,cmd)),capture_output=True,env=env,cwd=ROOT,timeout=120)
        (a.out/(label+'.private.log')).write_bytes(x.stdout+x.stderr);r['steps'].append(dict(name=label,returncode=x.returncode))
        if x.returncode:raise RuntimeError(x.stderr.decode('utf-8','replace')[-3000:])
        return x.stdout
    try:
        exe=a.out/'direct-metadata.exe'
        run('actual_reader_compile',[host/'clang++.exe','-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',ROOT/'native/app',
            '-I',base/'ggml/include',ROOT/'tests/direct_metadata.cpp','-Wl,--start-group',*libraries,'-Wl,--end-group','-o',exe])
        run('exact_byte_cache_EOF_failure_deadline_controls',[exe]);print('Actual metadata byte and failure controls passed',flush=True)
        files=sorted(a.model_directory.glob('qwen-flash-next-bf16-*-of-00076.gguf'));assert len(files)==76
        for i,f in enumerate(files):
            before=(f.stat().st_size,f.stat().st_mtime_ns)
            row=json.loads(run(f'original_metadata_{i:02d}',[exe,f]));assert row['metadata_identical']and row['GGML_context_identical']
            assert before==(f.stat().st_size,f.stat().st_mtime_ns);r['files'].append(dict(name=f.name,**row))
        print('All76 original GGUF metadata/GGML contexts matched',flush=True)
        run('actual_PS5_provider_compile',[target/'clang++.exe','--no-default-config','--target=x86_64-sie-ps5',
            '-fno-stack-protector','-fno-plt','-femulated-tls','-fPIC','-std=c++17','-O1','-fexceptions','-fcxx-exceptions','-frtti','-nostdinc++',
            '-isystem',sdk/'target/include/c++/v1','-isystem',sdk/'target/include','-I',ROOT/'native/app','-I',base/'ggml/include',
            '-Wall','-Wextra','-Werror','-c',ROOT/'native/app/direct_metadata.cpp','-o',a.out/'direct-metadata-PS5.o'])
        assert r['inputs']==fingerprint();r['state']='focused_direct_metadata_host_passed_not_console_admitted'
        print('Actual PS5 Direct metadata provider compiled',flush=True)
    except BaseException:r['state']='failed';raise
    finally:(a.out/'receipt.private.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
