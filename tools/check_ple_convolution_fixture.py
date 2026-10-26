#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check the complete bounded PLE convolution graph and compile its native fixture."""
import argparse,json,os,subprocess
from pathlib import Path
from check_model_checkpoint import record
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in('workspace','cache','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    up=a.cache/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569';host=a.workspace/'toolchain/msys-clang64/clang64/bin'
    providers=list((a.cache/'host-CPU-reference-066/build').rglob('ggml-base.a'))+list((a.cache/'host-CPU-reference-066/build').rglob('libggml-base.a'))
    if len(providers)!=1:raise ValueError('Exact existing metadata provider required')
    library=providers[0];prior_path=a.cache/'build/application-native-metadata-2615/receipt.private.json';prior=json.loads(prior_path.read_text())
    files=[Path(__file__),library,prior_path,up/'ggml/include/ggml.h']+[ROOT/f for f in(
        'native/app/ple_slice_graph.h','native/app/ple_convolution_graph.h','native/app/ple_slice_admission.h',
        'native/app/ple_slice_admission.cpp','native/app/mapped_source.cpp','tests/ple_convolution_graph.cpp')]
    fixed=[record(f)for f in files];exe=a.out/'ple-convolution.exe'
    native=next(c.copy()for c in prior['compile_commands']if Path(c[c.index('-c')+1]).name=='llama_engine.cpp')
    native[native.index('-c')+1]=str(ROOT/'native/app/ple_slice_admission.cpp');native[native.index('-o')+1]=str(a.out/'ple_slice_admission.o')
    native+=['-Wall','-Wextra','-Werror']
    commands=[[str(host/'clang++.exe'),'-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'native/app'),
        '-I',str(up/'ggml/include'),str(ROOT/'tests/ple_convolution_graph.cpp'),str(library),'-o',str(exe)],[str(exe)],native]
    env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''));controls=None
    for i,c in enumerate(commands):
        r=subprocess.run(c,capture_output=True,timeout=120,env=env);(a.out/f'{i}.private.log').write_bytes(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError('PLE convolution '+str(i)+': '+r.stderr.decode(errors='replace')[-2400:])
        if i==1:controls=json.loads(r.stdout)
    assert controls['actual_GGML_full_convolution_graphs']==16 and controls['exact_F32_outputs']==409600
    assert fixed==[record(f)for f in files]
    result=dict(controls=controls,inputs=fixed,commands=commands,actual_native_fixture_compiled=True,
        native_fixture_model_or_CPU_fallback=False,committed_console_execution_enabled=False,
        actual_backend_or_speed_qualified=False,PS5_operations=0,CI_runs=0)
    (a.out/'receipt.private.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k not in('inputs','commands')}),flush=True)
if __name__=='__main__':main()
