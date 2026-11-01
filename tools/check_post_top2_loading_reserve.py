#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise OS-floor, reservation and once-only loading-scope boundaries."""
import argparse,os,subprocess
from pathlib import Path
from expert_q4 import record,require,write_json
ROOT=Path(__file__).resolve().parents[1]
CPP=r'''
#include "post_top2_loading_reserve.h"
#include <iostream>
int main(){
 qwen_app::PostTop2LoadingReserve s;unsigned cases=0;
 for(auto n:{0u,897u,898u,1103u,1104u,1153u,1154u,6000u}){
  if(s.extra(n,898,206,256)!=256)return 1;++cases;
 }
 s.select(true);
 for(auto n:{0u,897u,898u,1103u,1104u,1153u,1154u,6000u}){
  const auto extra=s.extra(n,898,206,256);if(extra!=206||((n>=898+extra)!=(n>=1104)))return 2;++cases;
 }
 for(auto legacy:{0u,21u,64u,128u,206u,512u}){if(s.extra(6000,898,206,legacy)!=legacy)return 3;++cases;}
 auto reject=[&](auto f){try{f();return false;}catch(const std::exception&){++cases;return true;}};
 if(!reject([&]{s.select(true);})||!reject([&]{s.extra(6000,897,206,256);})||!reject([&]{s.extra(6000,898,205,256);}))return 4;
 s.select(false);if(s.extra(1104,898,206,256)!=256||!reject([&]{s.select(false);})||!reject([&]{s.select(true);}))return 5;
 const auto stats=s.stats();if(stats[0]||!stats[1]||stats[2]!=8||stats[3]!=8||stats[4]!=6||stats[5]!=0)return 6;
 std::cout<<"loading_scope_boundary_cases="<<cases<<" OS_minimum_and_reservation_preserved=1\n";return cases==27?0:7;
}
'''
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('workspace','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);src=a.out/'check.cpp';src.write_text(CPP,newline='\n');host=a.workspace/'toolchain/msys-clang64/clang64/bin';exe=a.out/'check.exe'
 for i,c in enumerate([[str(host/'clang++.exe'),'-std=c++17','-O2','-I'+str(ROOT/'native/app'),str(src),'-o',str(exe)],[str(exe)]]):
  r=subprocess.run(c,capture_output=True,timeout=120,env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH','')));(a.out/f'{i}.log').write_bytes(r.stdout+r.stderr);require(r.returncode==0,r.stderr.decode(errors='replace'))
 write_json(a.out/'complete.private.json',dict(completed=True,boundary_cases=27,OS_minimum_pages=898,OS_reservation_pages=206,
  no_admission_below_1104_pages=True,only_legacy256_padding_changes=True,once_only_scope=True,inputs=[record(__file__),record(src),record(ROOT/'native/app/post_top2_loading_reserve.h')],PS5_operations=0))
 print(r.stdout.decode().strip())
if __name__=='__main__':main()
