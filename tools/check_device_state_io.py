#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check pinned device-state byte-copy code with an explicit metadata backend."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
REV='0a1ef309cdbb9f2024f58a38fb4c42352c5db569'
def record(p):return dict(path=str(p.resolve()),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','cache','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);up=a.cache/('upstream/llama.cpp-'+REV)
    cpp=up/'src/llama-context.cpp';header=up/'src/llama-context.h';s=cpp.read_text();h=header.read_text()
    body=s[s.index('class llama_io_write_device :'):s.index('size_t llama_context::state_get_size()')]
    start=h.index('struct llama_memory_buffer {');end=h.index(';',h.index('using llama_memory_buffers =',start))+1
    definitions=h[start:end];extracted=a.out/'actual_device_state_io.inc'
    extracted.write_text('// Pinned llama.cpp MIT source, metadata-only host test.\n'+definitions+'\n'+body,newline='\n')
    files=[cpp,header,up/'src/llama-io.h',ROOT/'tests/device_state_io.cpp',Path(__file__)];fixed=[record(p)for p in files]
    host=a.workspace/'toolchain/msys-clang64/clang64/bin';exe=a.out/'device-state-tests.exe'
    command=[str(host/'clang++.exe'),'-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(a.out),'-include',str(up/'src/llama-io.h'),str(ROOT/'tests/device_state_io.cpp'),'-o',str(exe)]
    env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''))
    for i,c in enumerate([command,[str(exe)]]):
        r=subprocess.run(c,capture_output=True,timeout=120,env=env);(a.out/(str(i)+'.private.log')).write_bytes(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace')[-4000:])
    assert fixed==[record(p)for p in files]
    result=dict(controls=json.loads(r.stdout),inputs=fixed,extracted=record(extracted),command=command,upstream_revision=REV,
        stub_backend_only=True,native_state_API_not_qualified=True,PS5_operations=0,CI_runs=0)
    (a.out/'receipt.private.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result['controls']),flush=True)
if __name__=='__main__':main()
