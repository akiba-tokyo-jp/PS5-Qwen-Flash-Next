#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Execute the actual legacy policy validator with the candidate header view on the host."""
import argparse
import copy
import json
import os
from pathlib import Path
import subprocess

from build_performance_quantizer import record
from start_success_route import load,need,save

ROOT=Path(__file__).resolve().parents[1]


def check(workspace,current,view,out):
    out.mkdir(parents=True,exist_ok=False)
    policy=copy.deepcopy(load(current/'qwen-runtime/development.json'))
    gate=policy['native_first_generation_validation']
    # Packaging assigns fresh identity fields later. This host check tests
    # their format only and never claims native SELF/model integrity.
    gate.update(run_id='0'*32,candidate_SELF_sha256='1'*64,candidate_SELF_bytes=1,
        model_receipt_sha256='2'*64,model_receipt_bytes=1)
    data=out/'policy.private.json';save(data,policy)
    source=out/'check.cpp';source.write_text('''#include "first_generation_policy.h"
#include <fstream>
#include <iostream>
int main(int argc,char**argv){
    try{if(argc!=2)return 2;std::ifstream input(argv[1]);if(!input)return 3;
        const auto policy=nlohmann::json::parse(input);qwen_app::require_first_generation_policy(policy,false);
        std::cout<<"Actual legacy policy validator passed\\n";return 0;
    }catch(const std::exception&e){std::cerr<<e.what()<<"\\n";return 1;}
}
''',encoding='utf-8',newline='\n')
    host=workspace/'toolchain/msys-clang64/clang64/bin';up=current.parent/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569'
    executable=out/'check.exe'
    commands=[[str(host/'clang++.exe'),'-std=c++17','-O2','-I',str(view.parent),'-I',str(ROOT/'native/app'),
        '-I',str(up/'vendor'),'-I',str(up/'include'),'-I',str(up/'ggml/include'),'-ivfsoverlay',str(view),str(source),'-o',str(executable)],
        [str(executable),str(data)]]
    env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''),TMP=str(out),TEMP=str(out))
    for i,command in enumerate(commands):
        result=subprocess.run(command,capture_output=True,timeout=180,env=env);(out/(str(i)+'.private.log')).write_bytes(result.stdout+result.stderr)
        need(result.returncode==0,result.stderr.decode(errors='replace')[-3500:])
    result=dict(completed=True,actual_legacy_validator_passed=True,canonical_fixed_policy_values_preserved=True,
        dynamic_identity_fields_are_format_only_placeholders=True,SELF_or_model_integrity_claimed=False,
        source=record(source),artifact=record(executable),view=record(view),policy=record(data),commands=commands,PS5_operations=0)
    save(out/'result.private.json',result);return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','view','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();check(a.workspace,a.current,a.view,a.out)
    print(json.dumps(dict(completed=True,actual_legacy_validator_passed=True,PS5_operations=0)))


if __name__=='__main__':main()
