#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Replay actual fixture construction with pinned GGML allocation functions and metadata stubs."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def record(path):
    return dict(path=str(path.resolve()),bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
def function(text,marker):
    start=text.index(marker);brace=text.index('{',start);depth=1;end=brace+1
    while depth:
        if text[end]=='{':depth+=1
        if text[end]=='}':depth-=1
        end+=1
    return text[start:end]+'\n'
def construction(text,name):
    start=text.index('    for(unsigned role=0;role<3;++role) {',text.index('auto *ctx=ggml_init(params)'))
    end=text.index('    auto *buffer=ggml_backend_alloc_ctx_tensors',start)
    return 'void '+name+'(ggml_context *ctx,Fixture *f,const Json &p) {\n'+text[start:end]+'}\n'
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','cache','out'):parser.add_argument('--'+name,type=Path,required=True)
    a=parser.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    up=a.cache/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569'
    files=[up/'ggml/src/ggml.c',up/'ggml/src/ggml-backend.cpp',up/'ggml/src/ggml-alloc.c',
        a.cache/'vector-bank-app-build-2499/source-at-execution/vector_bank_admission.cpp',ROOT/'native/app/vector_bank_admission.cpp',
        ROOT/'tests/vector_bank_allocation.cpp',ROOT/'native/app/padded_bank.h',Path(__file__)]
    fixed=[record(p)for p in files];c,backend,alloc,failed,candidate=[p.read_text()for p in files[:5]]
    text=function(c,'size_t ggml_nbytes(')
    start=backend.index('struct ggml_backend_buft_alloc_buffer_n_plan_item');end=backend.index('// default implementation of alloc_buffer_n',start)
    text+=backend[start:end]
    text+=function(alloc,'static size_t aligned_offset(')+function(alloc,'struct ggml_tallocr ggml_tallocr_new(')+function(alloc,'enum ggml_status ggml_tallocr_alloc(')
    text+=construction(failed,'build_failed')+construction(candidate,'build_candidate')
    extracted=a.out/'actual_bank_allocation.inc';extracted.write_text(text,newline='\n')
    host=a.workspace/'toolchain/msys-clang64/clang64/bin';exe=a.out/'allocation-tests.exe'
    command=[str(host/'clang++.exe'),'-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(a.out),'-I',str(ROOT/'native/app'),
        '-I',str(up/'ggml/include'),'-I',str(up/'vendor'),str(ROOT/'tests/vector_bank_allocation.cpp'),'-o',str(exe)]
    policy=a.cache/'vector-bank-assets-2494/policy.private.json'
    env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''))
    for i,cmd in enumerate([command,[str(exe),str(policy)]]):
        r=subprocess.run(cmd,capture_output=True,timeout=120,env=env);(a.out/(str(i)+'.private.log')).write_bytes(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace')[-3000:])
    assert fixed==[record(p)for p in files]
    result=json.loads(r.stdout);result.update(inputs=fixed,extracted=record(extracted),policy=record(policy),command=command,native_execution=False)
    (a.out/'receipt.private.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items()if k not in ('inputs','extracted','policy','command','controls')}),flush=True)
if __name__=='__main__':main()
