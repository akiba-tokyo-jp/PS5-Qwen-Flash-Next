#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compare reset metadata with the actual pinned fresh SLRU implementation."""
import argparse
import json
import os
import subprocess
from pathlib import Path
from shader_storage import record

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workspace',type=Path,required=True)
    p.add_argument('--moe-source',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True)
    original=a.moe_source.read_text();begin=original.index('struct moe_cache_slru {')
    end=original.index('// gate, up, down',begin)
    test=ROOT/'tests/resident_cache_reset_behavior.inc'
    text='''#include "expert_policy.h"
#include "resident_cache_reset.h"
#include <array>
#include <iostream>
static bool use_adaptive;
extern "C" bool llama_app_expert_policy_enabled(){return use_adaptive;}
#define GGML_ASSERT(x) do{if(!(x))throw std::runtime_error("Original assertion");}while(0)
#define GGML_ABORT(...) throw std::runtime_error("Original abort")
'''+original[begin:end]+'\n'+test.read_text()
    source=a.out/'actual-cache-reset.cpp';source.write_text(text,newline='\n')
    runtime=a.workspace/'toolchain/msys-clang64/clang64/bin'
    env=dict(os.environ,PATH=str(runtime)+os.pathsep+os.environ.get('PATH',''))
    exe=a.out/'cache-reset-check.exe'
    command=[runtime/'clang++.exe','-std=c++17','-O2','-Wall','-Wextra','-Werror',
             '-I',ROOT/'native/app',source,'-o',exe]
    inputs=[record(x)for x in (Path(__file__),a.moe_source,test,ROOT/'native/app/resident_cache_reset.h',ROOT/'native/app/expert_policy.h')]
    result=subprocess.run(list(map(str,command)),capture_output=True,timeout=120,env=env)
    (a.out/'build.private.log').write_bytes(result.stdout+result.stderr)
    if result.returncode:raise RuntimeError(result.stderr.decode(errors='replace'))
    result=subprocess.run([str(exe)],capture_output=True,timeout=120,env=env)
    (a.out/'result.private.log').write_bytes(result.stdout+result.stderr)
    if result.returncode:raise RuntimeError(result.stderr.decode(errors='replace'))
    for row in inputs:
        if record(row['path'])!=row:raise ValueError('Actual cache test input changed')
    report=json.loads(result.stdout)
    if report['fresh_behavior_comparisons']!=768 or not report['invalid_lookup_refused']:
        raise ValueError('Complete original cache behavior proof required')
    receipt=dict(inputs=inputs,actual_original_SLRU_slice_SHA256=record(source)['sha256'],result=report,
                 command=list(map(str,command)),PS5_operations=0,host_model_inference=False)
    (a.out/'receipt.private.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(report),flush=True)


if __name__=='__main__':main()
