#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Test the actual plain-output adapter and its strict geometry refusals."""
import argparse,os,subprocess
from pathlib import Path
from expert_q4 import record,require,write_json
ROOT=Path(__file__).resolve().parents[1]
CPP=r'''
#include "output_plain_segments.h"
#include <iostream>
int main(){
 std::vector<std::uint64_t>sizes(20,1);sizes[3]=536870912;sizes[19]=138559648;
 const auto spans=qwen_app::output_plain_segments(675430560,{3,19},sizes);
 if(spans.size()!=2||spans[0].logical_offset!=0||spans[1].logical_offset!=536870912||spans[0].physical!=3||spans[1].physical!=19||spans[1].bytes!=138559648||spans[0].physical_offset||spans[1].physical_offset)return 1;
 unsigned refused=0;
 auto reject=[&](std::uint64_t n,std::vector<std::size_t>p,std::vector<std::uint64_t>s){try{qwen_app::output_plain_segments(n,p,s);return false;}catch(const std::runtime_error&){++refused;return true;}};
 for(auto n:{0ull,1ull,675430559ull,675430561ull,UINT64_MAX})if(!reject(n,{3,19},sizes))return 2;
 for(auto p:std::vector<std::vector<std::size_t>>{{},{3},{3,19,3},{3,3},{19,3},{3,20},{20,19}})if(!reject(675430560,p,sizes))return 3;
 for(unsigned i:{3u,19u})for(int d:{-1,1}){auto bad=sizes;bad[i]+=d;if(!reject(675430560,{3,19},bad))return 4;}
 std::cout<<"full_output_source_exact=1 refused="<<refused<<"\n";return refused==16?0:5;
}
'''
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('workspace','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);src=a.out/'check.cpp';src.write_text(CPP,newline='\n');host=a.workspace/'toolchain/msys-clang64/clang64/bin';exe=a.out/'check.exe'
 for i,c in enumerate([[str(host/'clang++.exe'),'-std=c++17','-O2','-I'+str(ROOT/'native/app'),str(src),'-o',str(exe)],[str(exe)]]):
  r=subprocess.run(c,capture_output=True,timeout=120,env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH','')));(a.out/f'{i}.log').write_bytes(r.stdout+r.stderr);require(r.returncode==0,r.stderr.decode(errors='replace'))
 write_json(a.out/'complete.private.json',dict(completed=True,full_two_part_source_preserved=True,refusals=16,inputs=[record(__file__),record(src),record(ROOT/'native/app/output_plain_segments.h')],PS5_operations=0))
 print(r.stdout.decode().strip())
if __name__=='__main__':main()
