#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Manual exact-palette host controls; no model execution, console call, or CI."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
def record(path):
    p=Path(path).resolve()
    return dict(path=str(p),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=False)
    runtime=args.workspace/'toolchain/msys-clang64/clang64'
    exe=args.out/'bf16-palette-screen.exe'
    shader=args.workspace/'toolchain/shaderc-clang64/clang64/bin'
    env=dict(os.environ,PATH=str(shader)+os.pathsep+str(runtime/'bin')+os.pathsep+os.environ.get('PATH',''))
    commands=[
        [runtime/'bin/clang++.exe','-std=c++17','-O3','-Wall','-Wextra','-Werror',
         '-I',ROOT/'native/app',ROOT/'tests/bf16_palette.cpp','-o',exe],
        [exe]]
    for i,command in enumerate(commands):
        r=subprocess.run(list(map(str,command)),cwd=ROOT,env=env,capture_output=True,timeout=90)
        (args.out/f'step-{i}.private.log').write_bytes(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace')[-2400:])
    controls=json.loads(r.stdout)
    spv=args.out/'bf16-palette-decode.spv'
    shader_commands=[
        [shader/'glslangValidator.exe','-V','--target-env','vulkan1.2',
         ROOT/'native/qwen_flash_next/bf16_palette_decode.comp','-o',spv],
        [runtime/'bin/spirv-val.exe','--target-env','vulkan1.2',spv]]
    for i,command in enumerate(shader_commands):
        r=subprocess.run(list(map(str,command)),cwd=ROOT,env=env,capture_output=True,timeout=90)
        (args.out/f'shader-{i}.private.log').write_bytes(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError('SPIR-V validation failed: '+r.stderr.decode(errors='replace')[-2400:])
    proof=dict(controls=controls,commands=[list(map(str,c))for c in commands],executable=record(exe),
        inputs=[record(p)for p in (Path(__file__),ROOT/'native/app/bf16_palette.h',ROOT/'tests/bf16_palette.cpp',
                                  ROOT/'native/qwen_flash_next/bf16_palette_decode.comp')],
        shader=record(spv),shader_commands=[list(map(str,c))for c in shader_commands],SPIRV_validated=True,
        GPU_qualified=False,PS5_operations=0,CI_runs=0)
    (args.out/'receipt.private.json').write_text(json.dumps(proof,indent=2)+'\n')
    print(json.dumps(controls),flush=True)
if __name__=='__main__':main()
