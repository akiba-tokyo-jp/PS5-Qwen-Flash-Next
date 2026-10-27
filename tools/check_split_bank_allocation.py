#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check split-buffer ownership with actual allocation code and compile its PS5 ABI."""
import argparse,json,os,subprocess
from pathlib import Path
from build_preservation_integrity import record
from check_vector_bank_allocation import function
ROOT=Path(__file__).resolve().parents[1]
SCENARIOS=('positive','reentrant','wrong-thread','second-allocation-failed','aliased-allocation',
    'overlapping-addresses','missing-coherency','invalid-descriptor','unknown-use','returned-ineligible',
    'coarse-alignment','CPU-backend','cache128','checkpoint-failed')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('workspace','cache','qualified-native','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    up=a.cache/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569'
    source=ROOT/'native/app/split_bank_allocation.cpp';test=ROOT/'tests/split_bank_allocation.cpp'
    c=up/'ggml/src/ggml.c';backend=up/'ggml/src/ggml-backend.cpp';alloc=up/'ggml/src/ggml-alloc.c'
    raw=backend.read_text();start=raw.index('struct ggml_backend_buft_alloc_buffer_n_plan_item')
    end=raw.index('// default implementation of alloc_buffer_n',start)
    extracted=a.out/'actual_split_allocation.inc'
    extracted.write_text(function(c.read_text(),'size_t ggml_nbytes(')+raw[start:end]+
        ''.join(function(alloc.read_text(),s)for s in ('static size_t aligned_offset(',
            'struct ggml_tallocr ggml_tallocr_new(','enum ggml_status ggml_tallocr_alloc(')),newline='\n')
    prior=json.loads(a.qualified_native.read_text());native=next(cmd.copy()for cmd in prior['compile_commands']
        if '-c'in cmd and Path(cmd[cmd.index('-c')+1]).name=='native_main.cpp')
    native[native.index('-c')+1]=str(source);native[native.index('-o')+1]=str(a.out/'split-bank-allocation-PS5.o')
    native+=['-Wall','-Wextra','-Werror']
    for i in range(len(native)-1):
        if native[i]=='-I'and Path(native[i+1]).is_relative_to(up):native[i]='-isystem'
    host=a.workspace/'toolchain/msys-clang64/clang64/bin';exe=a.out/'split-allocation.exe'
    compile_host=[str(host/'clang++.exe'),'-std=c++17','-O2','-Wall','-Wextra','-Werror',
        '-I',str(ROOT/'native/app'),'-I',str(up/'ggml/include'),'-I',str(a.out),str(test),str(source),'-o',str(exe)]
    files=[Path(__file__),source,test,extracted,c,backend,alloc,a.qualified_native,
        ROOT/'tools/check_vector_bank_allocation.py',*[ROOT/'native/app'/n for n in
        ('split_bank_allocation.h','split_bank_bridge.h','split_padded_bank.h','ready_expert_wave.h',
         'padded_bank.h','padded_cache_geometry.h','system_memory.h','native_gpu.h','native_allocator_budget.h')]]
    fixed=[record(f)for f in files];env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''))
    results=[]
    for i,cmd in enumerate([compile_host,*[[str(exe),s]for s in SCENARIOS],native]):
        r=subprocess.run(cmd,capture_output=True,timeout=180,env=env);(a.out/f'{i}.private.log').write_bytes(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError('Split allocation step '+str(i)+': '+r.stderr.decode(errors='replace')[-3500:])
        if 1<=i<=len(SCENARIOS):
            control=json.loads(r.stdout)
            if control.get('passed')is not True or control.get('physical_weight_bytes')!=0 or control.get('GPU_calls')!=0:
                raise ValueError('Unexpected allocation harness result')
            results.append(dict(scenario=SCENARIOS[i-1],**control))
    if fixed!=[record(f)for f in files]:raise ValueError('Split allocation inputs changed during checks')
    result=dict(schema='ps5-qwen-split-allocation-host-v1',inputs=fixed,commands=[compile_host,native],
        controls=results,actual_upstream_nbytes_packing_and_tallocr=True,actual_application_allocation_owner_tested=True,
        native_SDK_object=record(a.out/'split-bank-allocation-PS5.o'),group_conservative_charge_bytes=256<<20,
        total_conservative_cache_charge_bytes=512<<20,physical_Vulkan_allocation_qualified=False,
        GPU_IO_overlap_qualified=False,PS5_operations=0,CI_runs=0)
    (a.out/'receipt.private.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(allocation_owner_controls=len(results),actual_planner_extracted=True,
        native_SDK_object_compiled=True,physical_weight_bytes=0,PS5_operations=0)),flush=True)


if __name__=='__main__':main()
