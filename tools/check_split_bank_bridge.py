#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check the actual split-bank borrower against mocks and compile its native ABI."""
import argparse,json,os,subprocess
from pathlib import Path
from build_preservation_integrity import record
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in('workspace','cache','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    source=ROOT/'native/app/owned_mapped_backend.cpp';text=source.read_text()
    helper=text[text.index('namespace {'):text.index('extern "C" int ggml_app_vk_probe_owned_matvec')]
    body=text[text.index('extern "C" int ggml_app_vk_probe_owned_split_bank'):]
    inc=a.out/'actual_owned_split.inc';inc.write_text(helper+body,newline='\n')
    up=a.cache/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569';host=a.workspace/'toolchain/msys-clang64/clang64/bin'
    libraries=list((a.cache/'host-CPU-reference-066/build').rglob('*ggml-base.a'))
    if len(libraries)!=1:raise ValueError('Existing qualified GGML metadata library required')
    library=libraries[0];test=ROOT/'tests/split_bank_bridge.cpp';exe=a.out/'split-bank-bridge.exe'
    prior_path=a.cache/'build/application-native-PLE-2654/receipt.private.json';prior=json.loads(prior_path.read_text())
    native=next(c.copy()for c in prior['compile_commands']if Path(c[c.index('-c')+1]).name=='owned_mapped_backend.cpp')
    native[native.index('-o')+1]=str(a.out/'owned_mapped_backend.o');native+=['-Wall','-Wextra','-Werror']
    # Keep application warnings strict while treating unchanged upstream
    # header-local helpers as third-party implementation details.
    for i in range(len(native)-1):
        if native[i]=='-I'and Path(native[i+1]).is_relative_to(up):native[i]='-isystem'
    commands=[[str(host/'clang++.exe'),'-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'native/app'),
        '-I',str(up/'ggml/include'),'-I',str(a.out),str(test),str(library),'-o',str(exe)],[str(exe)],native]
    files=[Path(__file__),source,test,inc,library,prior_path,*[ROOT/'native/app'/n for n in
        ('split_bank_bridge.h','split_padded_bank.h','ready_expert_wave.h','padded_bank.h','padded_bank_layout.h')]]
    fixed=[record(f)for f in files];env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''))
    controls=None
    for i,c in enumerate(commands):
        r=subprocess.run(c,capture_output=True,timeout=180,env=env);(a.out/f'{i}.private.log').write_bytes(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError('Split-bank check '+str(i)+': '+r.stderr.decode(errors='replace')[-3000:])
        if i==1:controls=json.loads(r.stdout)
        print('Split-bank check '+str(i)+' passed',flush=True)
    if fixed!=[record(f)for f in files]:raise ValueError('Split-bank inputs changed during checking')
    result=dict(controls=controls,inputs=fixed,commands=commands,actual_native_ABI_compiled=True,
        current_production_bank_predicate_unchanged=True,PS5_execution=False,GPU_or_IO_overlap_qualified=False,CI_runs=0)
    (a.out/'receipt.private.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items()if k not in('inputs','commands')}))
if __name__=='__main__':main()
