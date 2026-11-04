#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise actual selector code with mock batches, not model/ABI emulation."""
import argparse
import json
import os
from pathlib import Path
import subprocess

from build_performance_quantizer import record
from start_success_route import need,save

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=False)
    (args.out/'llama.h').write_text('#pragma once\n#include <cstdint>\n'
        'using llama_token=int32_t;struct llama_context;struct llama_sampler;struct llama_token_data_array;\n'
        'enum llama_process_type {LLAMA_PROCESS_TYPE_DECODE=1};\n',encoding='utf-8',newline='\n')
    (args.out/'llama-batch.h').write_text('#pragma once\n#include "llama.h"\n#include <array>\n#include <vector>\n'
        'struct llama_batch_ext{struct token{bool output=false;std::array<int32_t,4>pos{};};std::vector<token>tokens;};\n'
        'inline bool llama_batch_ext_set_output_logits(llama_batch_ext*b,int32_t i,bool value){b->tokens.at(i).output=value;return true;}\n',
        encoding='utf-8',newline='\n')
    compiler=args.workspace/'toolchain/msys-clang64/clang64/bin/clang++.exe'
    env=dict(os.environ,PATH=str(compiler.parent)+os.pathsep+os.environ.get('PATH',''),TMP=str(args.out),TEMP=str(args.out))
    commands=[]
    for mode in (0,1):
        binary=args.out/('prefill-phase-'+str(mode)+'.exe')
        jobs=[[str(compiler),'-std=c++17','-O2','-Wall','-Wextra','-Werror',
            '-DQWEN_PERF_PREFILL_POST_TRUNK='+str(mode),'-I',str(args.out),'-I',str(ROOT/'native/app'),
            str(ROOT/'tests/prefill_process_candidate_test.cpp'),'-o',str(binary)],[str(binary)]]
        for i,command in enumerate(jobs):
            result=subprocess.run(command,capture_output=True,timeout=90,env=env)
            (args.out/(str(mode)+'-'+str(i)+'.private.log')).write_bytes(result.stdout+result.stderr)
            need(result.returncode==0,result.stderr.decode(errors='replace')[-3000:]);commands.append(command)
    report=dict(completed=True,actual_selector_host_controls_passed=True,control_and_candidate=True,
        boundary_lengths=[1,2,31,32,33,63,64,65],repeated_prefill_after_decode=True,
        one_and_two_token_decode_flags_preserved=True,exception_restores_caller_flags=True,
        mock_batch_types=True,actual_PS5_ABI_compile_required=True,model_numerics_validated=False,
        PS5_operations=0,commands=commands,inputs=[record(ROOT/'native/app/prefill_process_candidate.cpp'),
            record(ROOT/'tests/prefill_process_candidate_test.cpp')])
    save(args.out/'result.private.json',report)
    print(json.dumps({k:v for k,v in report.items() if k not in ('commands','inputs')}))


if __name__=='__main__':main()
