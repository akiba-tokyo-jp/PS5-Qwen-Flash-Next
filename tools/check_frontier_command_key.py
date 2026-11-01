#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reject stale command keys after every binding, generation, shape or push change."""
import argparse,os,subprocess
from pathlib import Path
from expert_q4 import record,require,write_json
ROOT=Path(__file__).resolve().parents[1]
FIXTURE=r'''#include "command_cache_key.h"
#include <iostream>
#include <stdexcept>
using namespace qwen_frontier;
int main(){
 std::uintptr_t ctx=7;std::uint64_t generation=2,pipeline=3,layout=4;
 std::uint32_t family=5;std::array<std::uint32_t,3>groups{8,9,10};
 std::vector<CommandBinding>bindings{{11,12,13},{14,15,16}};
 std::array<unsigned char,24>push{};
 auto key=[&]{return command_key(ctx,generation,pipeline,layout,family,groups,bindings,push.data(),push.size());};
 const auto original=key();unsigned rejected=0;
 auto changed=[&]{if(key()==original)throw std::runtime_error("Stale command key accepted");++rejected;};
 if(key()!=original)throw std::runtime_error("Stable key changed");
 ++ctx;changed();--ctx;++generation;changed();--generation;
 ++pipeline;changed();--pipeline;++layout;changed();--layout;++family;changed();--family;
 for(auto &g:groups){++g;changed();--g;}
 for(auto &b:bindings){++b.buffer;changed();--b.buffer;++b.offset;changed();--b.offset;++b.range;changed();--b.range;}
 for(auto &b:push){++b;changed();--b;}
 bindings.push_back({0,0,0});changed();bindings.pop_back();
 if(command_key(ctx,generation,pipeline,layout,family,groups,bindings,push.data(),push.size()-1)==original)throw std::runtime_error("Push size alias accepted");
 std::cout<<rejected+1<<" command-key invalidations and stable repeat passed; no Vulkan/GPU calls\n";
}'''

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in('workspace','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);src=a.out/'fixture.cpp';src.write_text(FIXTURE,newline='\n');host=a.workspace/'toolchain/msys-clang64/clang64/bin';exe=a.out/'fixture.exe';env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''))
 for i,c in enumerate([[str(host/'clang++.exe'),'-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'native/app'),str(src),'-o',str(exe)],[str(exe)]]):
  r=subprocess.run(c,capture_output=True,env=env,timeout=90);(a.out/f'{i}.private.log').write_bytes(r.stdout+r.stderr);require(r.returncode==0,r.stderr.decode(errors='replace'));print(r.stdout.decode(errors='replace').strip()or'Command-key fixture compiled')
 write_json(a.out/'receipt.private.json',dict(completed=True,stable_key_exact=True,all_binding_and_push_bytes_included=True,context_pipeline_layout_family_workgroups_generation_included=True,sources=[record(src),record(ROOT/'native/app/command_cache_key.h')],PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()
