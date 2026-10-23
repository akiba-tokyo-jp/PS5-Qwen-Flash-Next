#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Run the actual patched scheduler and GGML metadata arena on the host."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser();p.add_argument('--workspace',type=Path,required=True);p.add_argument('--cache',type=Path,required=True)
    p.add_argument('--model-io-manifest',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir()
    m=json.loads(a.model_io_manifest.read_text());source=a.model_io_manifest.parent/'source/ggml/src/ggml-backend.cpp'
    assert hashlib.sha256(source.read_bytes()).hexdigest()==m['sources']['ggml/src/ggml-backend.cpp']['patched_sha256']
    (a.out/'actual_scheduler_backend.cpp').write_bytes(source.read_bytes())
    base=a.cache/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569';host=a.workspace/'toolchain/msys-clang64/clang64/bin'
    libraries=[]
    for name in ['ggml.a','ggml-cpu.a','ggml-base.a']:
        rows=list((a.cache/'host-CPU-reference-066/build').rglob(name))+list((a.cache/'host-CPU-reference-066/build').rglob('lib'+name));assert len(rows)==1
        libraries.append(str(rows[0]))
    exe=a.out/'scheduler-arena.exe'
    command=[str(host/'clang++.exe'),'-std=c++17','-O2','-I',str(ROOT/'native/app'),'-I',str(a.out),'-I',str(base/'ggml/include'),'-I',str(base/'ggml/src'),'-I',str(base/'ggml/src/ggml-cpu'),str(ROOT/'tests/scheduler_arena.cpp'),'-Wl,--start-group',*libraries,'-Wl,--end-group','-o',str(exe)]
    env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''))
    for label,cmd in [('compile',command),('run',[str(exe)])]:
        r=subprocess.run(cmd,env=env,capture_output=True,timeout=150);(a.out/(label+'.private.log')).write_bytes(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError('Actual scheduler '+label+' failed')
    result=json.loads(r.stdout);result.update(model_inference=False,model_payload_reads=0,console_requests=0,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest())
    (a.out/'receipt.private.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
