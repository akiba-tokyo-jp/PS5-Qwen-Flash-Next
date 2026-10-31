#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise early-refill byte ownership and returned-error draining on the host."""
import argparse,json,os,subprocess
from pathlib import Path
from expert_q4 import require,record,write_json
ROOT=Path(__file__).resolve().parents[1]
CPP=r'''
#include <malloc.h>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <atomic>
static int host_align(void**p,std::size_t a,std::size_t n){*p=_aligned_malloc(n,a);return *p?0:1;}
static void host_free(void*p){_aligned_free(p);}
static bool early=false;
extern "C" bool qwen_next_refill_before_consume(){return early;}
#include "stream-host.private.h"
int main()try{
 unsigned cases=0;
 for(bool enabled:{false,true})for(unsigned failure=0;failure<4;++failure){
  early=enabled;std::array<void*,4>leases{};for(auto&p:leases)if(host_align(&p,16384,2u<<20))throw std::runtime_error("Host lease allocation");
  std::atomic<unsigned>entered{0},returned{0};unsigned consumed=0;bool caught=false;
  qwen_app::StreamingReadPool pool([&](const qwen_app::BoundedReadRequest&r)->std::int64_t{
   ++entered;const auto id=unsigned(r.offset/16384);std::this_thread::sleep_for(std::chrono::milliseconds(id%3));
   if(failure==1&&id==5){++returned;throw std::runtime_error("Returned read error");}
   std::memset(r.target,int(id+17),r.bytes);++returned;return r.bytes;
  });pool.start();std::array<qwen_app::BoundedReadRequest,12>requests{};
  for(unsigned i=0;i<12;++i)requests[i]={1,nullptr,16384,std::uint64_t(i)*16384};
  try{pool.run(requests.data(),12,leases,[&](unsigned id){if(failure==2&&id==7)throw std::runtime_error("Returned pre-read error");},[&](unsigned id,const void*p,std::int64_t bytes){
    if(bytes!=16384)throw std::runtime_error("Length differs");const auto*b=static_cast<const unsigned char*>(p);
    for(unsigned i=0;i<unsigned(bytes);++i)if(b[i]!=id+17)throw std::runtime_error("Read lease overwritten before consumption");
    std::this_thread::sleep_for(std::chrono::milliseconds(2));
    for(unsigned i=0;i<unsigned(bytes);++i)if(b[i]!=id+17)throw std::runtime_error("Read lease overwritten during consumption");
    ++consumed;if(failure==3&&id==4)throw std::runtime_error("Returned consumer error");
   });}catch(const std::runtime_error&){caught=true;}
  if(caught!=(failure!=0)||entered!=returned||(!failure&&consumed!=12)||entered>12)throw std::runtime_error("Completion/error accounting differs");
  pool.require_completed();pool.stop_completed();for(void*p:leases)host_free(p);++cases;
 }
 std::cout<<"ownership_and_error_drain_cases="<<cases<<" all_bytes_preserved=1 all_reads_returned=1\n";return 0;
}catch(const std::exception&e){std::cerr<<e.what();return 1;}
'''
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('build','workspace','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);header=a.build/'streaming_read_pool.h';body=header.read_text().replace('posix_memalign','host_align').replace('std::free(refill_copy_)','host_free(refill_copy_)')
 (a.out/'stream-host.private.h').write_text(body,newline='\n');cpp=a.out/'check.private.cpp';cpp.write_text(CPP,newline='\n');host=a.workspace/'toolchain/msys-clang64/clang64/bin';exe=a.out/'check.exe'
 commands=[[str(host/'clang++.exe'),'-std=c++17','-O2','-I'+str(a.out),'-I'+str(ROOT/'native/app'),str(cpp),'-o',str(exe)],[str(exe)]]
 for i,cmd in enumerate(commands):
  run=subprocess.run(cmd,capture_output=True,timeout=120,env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH','')));(a.out/f'{i}.private.log').write_bytes(run.stdout+run.stderr);require(run.returncode==0,run.stderr.decode(errors='replace')[-2000:])
 write_json(a.out/'complete.private.json',dict(completed=True,ownership_error_drain_cases=8,allocation_wrappers_only_changed_for_host=True,all_bytes_preserved_during_consumption=True,all_queued_reads_returned=True,source=record(header),inputs=[record(__file__),record(cpp)],PS5_operations=0,native_speed_proven=False));print(run.stdout.decode().strip())
if __name__=='__main__':main()
