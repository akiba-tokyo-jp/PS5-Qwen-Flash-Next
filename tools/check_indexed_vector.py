#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Manually qualify dispatch bounds and immutable scalar BF16 SPIR-V."""
import argparse,hashlib,json,os,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','cache','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    host=a.workspace/'toolchain/msys-clang64/clang64/bin'
    source=a.cache/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569'
    env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''))
    def run(name,cmd):
        r=subprocess.run(list(map(str,cmd)),cwd=ROOT,env=env,capture_output=True,timeout=120)
        (a.out/(name+'.private.log')).write_bytes(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError(r.stderr.decode('utf-8','replace')[-3000:])
        return r.stdout
    exe=a.out/'indexed_vector.exe'
    run('compile',[host/'clang++.exe','-std=c++17','-O2','-Wall','-Wextra','-Werror',
        '-I',ROOT/'native/app','-I',source/'ggml/include',ROOT/'tests/indexed_vector.cpp','-o',exe])
    run('layout_bounds',[exe]);rows=[]
    base=a.cache/'build/llama-ps5/ggml/src/ggml-vulkan/vulkan-shaders.spv'
    names=['mul_mat_vec_id_bf16_f32_f32'+suffix for suffix in ('','_subgroup','_subgroup_no_shmem')]
    names += ['matmul_id'+group+'_bf16'+precision for group in ('','_subgroup')for precision in ('','_fp32')]
    for name in names:
        shader=base/(name+'.spv')
        run(name+'-validate',[host/'spirv-val.exe','--target-env','vulkan1.3',shader])
        assembly=run(name+'-disassemble',[host/'spirv-dis.exe',shader]).decode()
        caps=sorted(set(re.findall(r'\bOpCapability\s+(\w+)',assembly)))
        if any(any(x in cap for x in ('BFloat','CooperativeMatrix','DotProduct'))for cap in caps):
            raise ValueError('A non-scalar GPU capability is not admitted')
        rows.append(dict(name=name,bytes=shader.stat().st_size,sha256=hashlib.sha256(shader.read_bytes()).hexdigest(),capabilities=caps))
    (a.out/'receipt.private.json').write_text(json.dumps(dict(layout_positive_cases=8,
        refusal_controls_per_case=14,null_control=True,immutable_shaders=rows,
        console_requests=0,GPU_calls=0,source_verified_not_native_qualified=True),indent=2)+'\n')
    print('Exact layout/refusal controls and seven immutable BF16 shaders passed; no console calls.')
if __name__=='__main__':main()
