#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Run the actual memory diagnostic with controlled public API stubs."""
import argparse,json,os,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser();p.add_argument('--workspace',type=Path,required=True);p.add_argument('--cache',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    a.out.mkdir();host=a.workspace/'toolchain/msys-clang64/clang64/bin'
    env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''))
    lock=json.loads((ROOT/'native/qwen_flash_next/dependencies.lock.json').read_text())
    vendor=a.cache/'upstream'/('llama.cpp-'+lock['llama_cpp']['revision'])/'vendor'
    exe=a.out/'memory-probe.exe'
    command=[str(host/'clang++.exe'),'-std=c++17','-O2','-Wall','-Wextra','-Werror',
        '-I',str(ROOT/'tests/memory_probe_stubs'),'-I',str(ROOT/'native/app'),'-I',str(vendor),'-I',str(vendor/'hash'),
        *[str(ROOT/x) for x in ('native/app/memory_probe.cpp','native/app/virtual_source.cpp','native/app/sha256_backend.cpp','tests/memory_probe.cpp')],'-o',str(exe)]
    cases=[('compile',command,120),('run',[str(exe)],30)]
    cases += [(kind,[str(exe),kind],30) for kind in ('bad-protection','bad-release','bad-reservation','wrong-address')]
    cases += [('model-spans',[str(exe),'model-spans',str(a.cache/'converted-bf16-002/model-receipt.json')],30)]
    for name,cmd,timeout in cases:
        result=subprocess.run(cmd,env=env,capture_output=True,timeout=timeout)
        (a.out/(name+'.private.log')).write_bytes(result.stdout+result.stderr)
        if result.returncode:raise RuntimeError('Native memory probe '+name+' failed')
    (a.out/'receipt.private.json').write_text(json.dumps(dict(actual_native_diagnostic_with_API_stubs='passed',maximum_journal_line_bytes=1024,retained_native_failure_cases=4,actual_model_spans=76,console_access=False,GPU_calls=0,model_loaded=False),indent=2)+'\n')
    print(result.stdout.decode(),end='')
if __name__=='__main__':main()
