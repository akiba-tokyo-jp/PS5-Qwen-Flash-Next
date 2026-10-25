#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check native GPU-client ownership with host API stubs; never execute a GPU."""
import argparse,hashlib,json,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def record(p):
    p=p.resolve();return dict(path=str(p),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('workspace','cache','out'):parser.add_argument('--'+key,type=Path,required=True)
    parser.add_argument('--policy',type=Path);parser.add_argument('--app-config',type=Path)
    a=parser.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    if bool(a.policy)!=bool(a.app_config):parser.error('policy and app-config must be supplied together')
    host=a.workspace/'toolchain/msys-clang64/clang64/bin'
    upstream=a.cache/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569'
    env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''))
    steps=[];inputs=[Path(__file__)]
    for name,files in [('dispatch',[ROOT/'tests/palette_gpu_dispatch.cpp',ROOT/'native/app/palette_gpu_dispatch.cpp']),
                       ('policy',[ROOT/'tests/palette_gpu_policy.cpp',ROOT/'native/app/startup.cpp'])]:
        exe=a.out/(name+'.exe');inputs+=files
        command=[host/'clang++.exe','-std=c++17','-O2','-Wall','-Wextra','-Werror',
            '-I',ROOT/'native/app','-I',a.workspace/'toolchain/Vulkan-Headers/include','-I',upstream/'vendor',*files,'-o',exe]
        arguments=[a.policy,a.app_config]if name=='policy'and a.policy else[]
        for label,cmd in [(name+'-compile',command),(name+'-controls',[exe,*arguments])]:
            r=subprocess.run(list(map(str,cmd)),cwd=ROOT,env=env,capture_output=True,timeout=120)
            (a.out/(label+'.private.log')).write_bytes(r.stdout+r.stderr)
            if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace')[-3500:] or label+' failed')
            steps.append(dict(name=label,returncode=0));print(label+' passed',flush=True)
    result_test=ROOT/'tests/test_palette_gpu_result.py'
    r=subprocess.run([sys.executable,'-B',str(result_test)],cwd=ROOT,capture_output=True,timeout=30)
    (a.out/'result-controls.private.log').write_bytes(r.stdout+r.stderr)
    if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace')[-2500:])
    steps.append(dict(name='result-controls',returncode=0));print('result-controls passed',flush=True)
    inputs += [result_test,ROOT/'tools/palette_gpu_result.py']
    inputs+=list((ROOT/'native/app').glob('palette*.h'))+[ROOT/'native/app/bf16_palette.h']
    receipt=dict(steps=steps,inputs=[record(p)for p in inputs],
        host_API_stubs=True,unknown_fence_blocks_reuse=True,failed_submit_blocks_reuse=True,
        owned_coherent_buffer_bounds_checked=True,strict_policy_refusals=True,
        PS5_operations=0,GPU_execution=False,CI_runs=0)
    (a.out/'receipt.private.json').write_text(json.dumps(receipt,indent=2)+'\n')
if __name__=='__main__':main()
