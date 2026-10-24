#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check the actual native prior-byte evidence validator and immutable decoder."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('workspace','cache','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    paths=[ROOT/'native/app/native_main.cpp',ROOT/'native/app/shader_assets.cpp',ROOT/'native/app/shader_assets.h',
        ROOT/'tests/prior_shader_assets.cpp',Path(__file__)]
    def fp():return {str(x.relative_to(ROOT)):hashlib.sha256(x.read_bytes()).hexdigest()for x in paths}
    before=fp();text=paths[0].read_text();body=text.split('static void validate_prior_shader_CPU(',1)[1].split('\nstatic Json read_prior_shader_CPU(',1)[0]
    (a.out/'actual_prior_shader_validator.h').write_text('static void validate_prior_shader_CPU('+body,encoding='utf-8')
    baseline=subprocess.check_output(['git','show','79f3c34:native/app/shader_assets.cpp'],cwd=ROOT).decode().replace('\r\n','\n')
    current=paths[1].read_text();start='extern "C" const void *qwen_app_prepare_shader_code('
    assert baseline.split(start,1)[1]==current.split(start,1)[1], 'Per-use SHA256 restoration or positive lease completion changed'
    receipt=dict(state='running',inputs=before,steps=[],per_use_decoder_and_completion_text_unchanged=True,
        source_revision='79f3c34',console_requests=0,GPU_calls=0)
    host=a.workspace/'toolchain/msys-clang64/clang64/bin';env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''))
    engine=a.cache/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569'
    exe=a.out/'actual-prior-validator.exe'
    commands=[('actual_validator_compile',[host/'clang++.exe','-std=c++17','-O1','-Wall','-Wextra','-Werror',
        '-I',ROOT/'native/app','-I',engine/'vendor','-I',a.out,ROOT/'tests/prior_shader_assets.cpp','-o',exe]),
        ('actual_validator_controls',[exe])]
    try:
        for name,command in commands:
            r=subprocess.run(list(map(str,command)),capture_output=True,cwd=ROOT,env=env,timeout=120)
            (a.out/(name+'.private.log')).write_bytes(r.stdout+r.stderr);receipt['steps'].append(dict(name=name,returncode=r.returncode))
            assert not r.returncode,r.stderr.decode('utf-8','replace')[-2500:];print(name+' passed',flush=True)
        assert before==fp();receipt['state']='focused_prior_shader_host_passed_not_console_admitted'
    except BaseException:receipt['state']='failed';raise
    finally:(a.out/'receipt.private.json').write_text(json.dumps(receipt,indent=2)+'\n')
if __name__=='__main__':main()
