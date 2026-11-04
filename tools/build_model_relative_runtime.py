#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compile the qualified concurrent model adapter for the actual native ABI."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
from build_performance_quantizer import record
from driver_table_storage import sections
from start_success_route import load,need,save
ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','controls','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();proof=load(a.controls);need(proof['completed'] and proof['new_concurrent_controls']==9 and
        record(proof['source']['path'])==proof['source'] and proof['maximum_extra_workers']==1 and
        proof['additional_FDs']==0,'Exact changed concurrent controls and zero extra source descriptors required')
    prior=load(proof['predictor_proof']['path']);need(record(prior['source']['path'])==prior['source'],
        'The independently qualified native predictor changed')
    a.out.mkdir(parents=True,exist_ok=False)
    names=('model_relative_prefetch_runtime.cpp','model_relative_prefetch_runtime.h','model_relative_prefetch.h',
        'relative_span_predictor.h','model_pread_observation.h','system_memory.h')
    for name in names:shutil.copyfile(ROOT/'native/app'/name,a.out/name)
    target=a.workspace/'toolchain/llvm-mingw-20261006-ucrt-x86_64/bin';sdk=a.workspace/'toolchain/ps5-sdk-radv/ps5-payload-sdk/target/include'
    up=a.current.parent/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569';obj=a.out/'model-relative-prefetch.o'
    command=[str(target/'clang++.exe'),'--no-default-config','--target=x86_64-sie-ps5','-nostdinc++',
        '-isystem',str(sdk/'c++/v1'),'-isystem',str(sdk),'-std=c++17','-fexceptions','-fcxx-exceptions',
        '-femulated-tls','-fno-stack-protector','-fno-plt','-fPIC','-O2','-ffunction-sections','-fdata-sections',
        '-Wall','-Wextra','-Werror','-I',str(a.out),'-I',str(up/'vendor'),'-c',str(a.out/names[0]),'-o',str(obj)]
    run=subprocess.run(command,capture_output=True,timeout=90,env=dict(os.environ,TMP=str(a.out),TEMP=str(a.out)))
    (a.out/'compile.private.log').write_bytes(run.stdout+run.stderr)
    need(not run.returncode,(run.stdout+run.stderr).decode(errors='replace')[-4000:])
    native_sections=sections(obj.read_bytes())
    need(not any(s['name'].startswith(('.init_array','.ctors')) and s['bytes'] for s in native_sections),
        'The provider must not add an unmeasured global constructor')
    symbols=subprocess.check_output([str(target/'llvm-nm.exe'),'--defined-only','--format=posix',str(obj)],text=True)
    need(all(name+' ' in symbols for name in ('__wrap_pread','__wrap_close')),'Both actual source ownership wrappers must be defined')
    save(a.out/'result.private.json',dict(completed=True,artifact=record(obj),controls=record(a.controls),
        predictor_proof=proof['predictor_proof'],inputs=[record(a.out/name) for name in names],command=command,
        actual_native_pread_offset_bytes=8,new_global_constructors=0,maximum_extra_workers=1,
        maximum_simultaneous_reads=4,actual_scratch_bytes=2<<20,additional_source_FDs=0,
        required_link_flags=['--wrap=pread','--wrap=close'],native_model_integration_qualified=False,
        model_decode_tok_s_measured=False,PS5_operations=0,production_adopted=False))
    print(dict(completed=True,native_ABI_compiled=True,new_global_constructors=0,PS5_operations=0))


if __name__=='__main__':main()
