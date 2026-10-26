#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise checkpoint replay in the real adapter with state/API stubs."""
import argparse,json,os,subprocess
from pathlib import Path
from check_model_checkpoint import record
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('workspace','cache','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);up=a.cache/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569';host=a.workspace/'toolchain/msys-clang64/clang64/bin'
    sampler=up/'src/llama-sampler.cpp';s=sampler.read_text();start=s.index('static void llama_sampler_greedy_apply(');end=s.index('static bool llama_sampler_greedy_backend_init(',start)
    inc=a.out/'actual_checkpoint_greedy.inc';inc.write_text(s[start:end],newline='\n')
    sources=[ROOT/'native/app/llama_engine.cpp',ROOT/'native/app/model_checkpoint.cpp',ROOT/'tests/llama_checkpoint_adapter.cpp']
    inputs=sources+[ROOT/'native/app/llama_engine.h',ROOT/'native/app/model_checkpoint.h',sampler,inc,Path(__file__)];fixed=[record(p)for p in inputs]
    exe=a.out/'checkpoint-adapter-tests.exe';command=[str(host/'clang++.exe'),'-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'native/app'),'-I',str(up/'include'),'-I',str(up/'ggml/include'),'-I',str(a.out),*map(str,sources),'-o',str(exe)]
    env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''));results=[]
    for name,c in [('compile',command)]+[(n,[str(exe),n])for n in ('positive','short_capture','short_restore','missing_PLE','wrong_routes','no_budget',
        'prefix-positive','prefix-miss','prefix-short-restore','prefix-missing-PLE','prefix-no-budget','prefix-wrong-model','prefix-observer-failure',
        'spec-accepted','spec-rejected','spec-discard','spec-target-EOG','spec-invalid','spec-short-restore','spec-missing-PLE',
        'spec-missing-row','spec-unknown-sync','spec-process-failure','spec-wrong-model','spec-no-budget')]:
        r=subprocess.run(c,capture_output=True,timeout=120,env=env);(a.out/(name+'.private.log')).write_bytes(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError(name+': '+r.stderr.decode(errors='replace')[-3000:])
        if name!='compile':results.append(json.loads(r.stdout))
    assert fixed==[record(p)for p in inputs]
    result=dict(controls=results,inputs=fixed,command=command,API_stubs_only=True,native_model_qualification=False,PS5_operations=0)
    (a.out/'receipt.private.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(host_cases=len(results),actual_adapter_and_greedy_source=True,all_passed=True,PS5_operations=0)),flush=True)
if __name__=='__main__':main()
