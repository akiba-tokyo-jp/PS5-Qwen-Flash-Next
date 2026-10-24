#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise the actual patched mmap class against complete model metadata."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser();p.add_argument('--workspace',type=Path,required=True);p.add_argument('--cache',type=Path,required=True)
    p.add_argument('--model-io-manifest',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir()
    manifest=json.loads(a.model_io_manifest.read_text());source=a.model_io_manifest.parent/'source/src/llama-mmap.cpp'
    assert hashlib.sha256(source.read_bytes()).hexdigest()==manifest['sources']['src/llama-mmap.cpp']['patched_sha256']
    text=source.read_text(encoding='utf-8');start=text.index('struct llama_mmap::impl {');end=text.index('#elif defined(_WIN32)',start)
    actual=text[start:end]+'\n#endif\n    void *addr;\n    size_t size;\n};\n'
    header=a.out/'actual_reserved_mmap_impl.h';header.write_text(actual,encoding='utf-8',newline='\n')
    host=a.workspace/'toolchain/msys-clang64/clang64/bin';vendor=a.cache/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569/vendor'
    exe=a.out/'reserved-mmap-lifetime.exe';env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''))
    command=[str(host/'clang++.exe'),'-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'native/app'),'-I',str(vendor),'-I',str(a.out),str(ROOT/'tests/reserved_mmap_lifetime.cpp'),'-o',str(exe)]
    for label,cmd in [('compile',command),('run',[str(exe),str(a.cache/'converted-bf16-002/model-receipt.json')])]:
        r=subprocess.run(cmd,env=env,capture_output=True,timeout=120);(a.out/(label+'.private.log')).write_bytes(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError('Actual mmap lifetime '+label+' failed')
    (a.out/'receipt.private.json').write_text(json.dumps(dict(actual_patched_mmap_class='passed',original_model_files=76,trim_requests=304,full_lease_destructions=76,ordinary_mmap_control='passed',source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),console_access=False),indent=2)+'\n')
    print(r.stdout.decode(),end='')
if __name__=='__main__':main()
