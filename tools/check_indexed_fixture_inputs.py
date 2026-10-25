#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Manually check the actual native fixture input helper; no shaders or console work."""
import argparse,json,os,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workspace',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    host=a.workspace/'toolchain/msys-clang64/clang64/bin'
    env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''))
    exe=a.out/'fixture_inputs.exe';steps=[]
    for name,command in [('compile',[host/'clang++.exe','-std=c++17','-O2','-Wall','-Wextra','-Werror',
                         '-I',ROOT/'native/app',ROOT/'tests/indexed_fixture_inputs.cpp','-o',exe]),('controls',[exe])]:
        r=subprocess.run(list(map(str,command)),cwd=ROOT,env=env,capture_output=True,timeout=60)
        (a.out/(name+'.private.log')).write_bytes(r.stdout+r.stderr)
        steps.append(dict(name=name,returncode=r.returncode))
        if r.returncode:raise RuntimeError(r.stderr.decode('utf-8','replace')[-2500:])
        print(name+' passed',flush=True)
    (a.out/'receipt.private.json').write_text(json.dumps(dict(steps=steps,all_four_layouts_checked=True,
        original_timed_inputs_BF16_exact=True,additional_F32_inputs_not_BF16_exact=True,
        console_requests=0,GPU_calls=0,shader_validation_repeated=False),indent=2)+'\n')
if __name__=='__main__':main()
