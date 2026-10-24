#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise the actual patched transfer loops with host copy/fence API stubs."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]

def function(source,marker):
    start=source.index(marker); opening=source.index('{',start); depth=1;end=opening+1
    while depth:
        if source[end]=='{':depth+=1
        if source[end]=='}':depth-=1
        end+=1
    return source[start:end]+'\n'

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--workspace',type=Path,required=True);p.add_argument('--cache',type=Path,required=True);a=p.parse_args()
    lock=json.loads((ROOT/'native/qwen_flash_next/dependencies.lock.json').read_text())
    path=a.cache/'upstream'/('llama.cpp-'+lock['llama_cpp']['revision'])/'ggml/src/ggml-vulkan/ggml-vulkan-buffers.cpp'
    source=path.read_text();patch=ROOT/'patches/llama/0004-bounded-native-staging.patch'
    receipt=json.loads((a.cache/'build/llama-ps5/receipt.private.json').read_text())
    assert any(row['name']==patch.name and row['sha256']==hashlib.sha256(patch.read_bytes()).hexdigest()for row in receipt['upstream_patches'])
    out=a.cache/'build/staging-check';out.mkdir(parents=True,exist_ok=True)
    actual='static constexpr size_t ggml_app_transfer_limit = 64u << 20;\n'
    for marker in ['extern "C" bool ggml_app_bounded_staging_enabled()',
        'void ggml_vk_buffer_write(vk_buffer& dst, size_t offset, const void * src, size_t size)',
        'void ggml_vk_buffer_read(vk_buffer& src, size_t offset, void * dst, size_t size)']:
        actual+=function(source,marker)
    (out/'actual-staging.inc').write_text(actual,encoding='utf-8')
    host=a.workspace/'toolchain/msys-clang64/clang64/bin';env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''))
    exe=out/'staging-tests.exe'
    command=[str(host/'clang++.exe'),'-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(out),str(ROOT/'tests/bounded_staging.cpp'),'-o',str(exe)]
    for label,args in [('compile',command),('actual_transfer_loops',[str(exe)])]:
        result=subprocess.run(args,env=env,capture_output=True,timeout=90)
        (out/(label+'.private.log')).write_bytes(result.stdout+result.stderr)
        if result.returncode:raise RuntimeError(result.stderr.decode('utf-8','replace'))
        print(label+' passed: '+result.stdout.decode().strip(),flush=True)
    (out/'receipt.private.json').write_text(json.dumps(dict(patched_source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        patch_sha256=hashlib.sha256(patch.read_bytes()).hexdigest(),raw_bytes_preserved=True,failed_chunk_not_retried=True,
        staging_limit_bytes=64<<20,console_access=False,GPU_execution=False,model_loaded=False),indent=2)+'\n')

if __name__=='__main__':main()
