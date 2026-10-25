#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build the portable codec and run focused manual exhaustive preservation controls."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def record(path):
    p=Path(path).resolve();return dict(path=str(p),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workspace',type=Path,required=True);p.add_argument('--cache',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    host=a.workspace/'toolchain/msys-clang64/clang64';vendor=ROOT/'native/thirdparty/lz4'
    provenance=json.loads((vendor/'UPSTREAM.json').read_text())
    for row in provenance['files']:
        assert hashlib.sha256((vendor/row['path']).read_bytes()).hexdigest()==row['sha256']
    includes=[ROOT/'native/app',vendor,a.cache/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569/vendor',host/'include']
    env=dict(os.environ,PATH=str(host/'bin')+os.pathsep+os.environ.get('PATH',''))
    commands=[]
    for name in ('lz4','lz4hc'):
        commands.append([host/'bin/clang.exe','-O3','-DNDEBUG','-I',vendor,'-c',vendor/(name+'.c'),'-o',a.out/(name+'.o')])
    exe=a.out/'bf16-lossless-screen.exe'
    commands.append([host/'bin/clang++.exe','-std=c++17','-O3','-Wall','-Wextra','-Werror',
        *[x for inc in includes for x in ('-I',inc)],ROOT/'tools/bf16_lossless_screen.cpp',
        a.out/'lz4.o',a.out/'lz4hc.o','-L',host/'lib','-lzstd','-o',exe])
    commands.append([exe,'--self-test'])
    steps=[]
    for i,cmd in enumerate(commands):
        r=subprocess.run(list(map(str,cmd)),cwd=ROOT,env=env,capture_output=True,timeout=180)
        (a.out/f'step-{i}.private.log').write_bytes(r.stdout+r.stderr)
        steps.append(dict(command=list(map(str,cmd)),returncode=r.returncode))
        if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace')[-3000:])
    proof=json.loads(r.stdout)
    inputs=[record(x) for x in [Path(__file__),ROOT/'tools/bf16_lossless_screen.cpp',ROOT/'native/app/bf16_lossless.h',ROOT/'native/app/bf16_decode_queue.h',
        vendor/'UPSTREAM.json',*[vendor/row['path'] for row in provenance['files']]]]
    (a.out/'receipt.private.json').write_text(json.dumps(dict(steps=steps,controls=proof,inputs=inputs,
        executable=record(exe),CPU_only=True,PS5_operations=0,CI_runs=0),indent=2)+'\n')
    print(json.dumps(proof),flush=True)
if __name__=='__main__':main()
