#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise the actual composed registry with real SHA256 and invalid-use cases."""
import argparse,json,os,subprocess
from pathlib import Path
from expert_q4 import record,require,write_json
from multiple_shader_source import STATE,PREPARE
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('compiler','upstream','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);sha=a.upstream/'vendor/hash/sha256'
    source=a.out/'registry-check.private.cpp'
    code=r'''
#include <algorithm>
#include <array>
#include <atomic>
#include <cstdint>
#include <cstring>
#include <stdexcept>
#include <iostream>
extern "C" {
#include "sha256.h"
}
namespace {constexpr std::size_t maximum_shader=1<<20;
std::atomic<bool>initialized{false},registration_fault{false},failed{false};unsigned hashes=0;
[[noreturn]]void fail(const char*m){failed.store(true);throw std::runtime_error(m);}
uint32_t u32(const unsigned char*p){uint32_t v;std::memcpy(&v,p,4);return v;}
std::array<unsigned char,32>digest(const void*p,std::size_t n){++hashes;std::array<unsigned char,32>r{};sha256_hash(r.data(),static_cast<const unsigned char*>(p),n);return r;}}
REGISTRY_STATE
const void*prepare(const void*storage,std::size_t stored_bytes,std::size_t*original_bytes,void**lease){
REGISTRY_PREPARE
return nullptr;
}
unsigned assertions=0;
void check(bool value){if(!value)throw std::runtime_error("Registry contract failed");++assertions;}
void reset(){additional_shaders={};additional_count=0;additional_verified_count=0;additional_modules=0;initialized=false;registration_fault=false;failed=false;}
template<class F>void rejects(F f){bool caught=false;try{f();}catch(const std::runtime_error&){caught=true;}check(caught);}
int main(){
 alignas(4)std::array<std::array<uint32_t,8>,5>programs{};
 std::array<std::array<unsigned char,32>,5>sha{};
 for(unsigned i=0;i<5;++i){programs[i]={0x07230203,0x00010000,i,3,0};sha[i]=digest(programs[i].data(),20);}
 for(unsigned i=0;i<4;++i)qwen_app_register_additional_shader(programs[i].data(),20,sha[i].data());
 check(additional_count==4&&!registration_fault.load());verify_additional_shader();check(qwen_app_additional_shaders_verified()==4);
 for(unsigned i=0;i<4;++i){std::size_t n=0;void*lease=reinterpret_cast<void*>(1);check(prepare(programs[i].data(),20,&n,&lease)==programs[i].data());check(n==20&&!lease);}
 check(qwen_app_additional_shader_modules()==4);std::size_t n=0;void*lease=nullptr;
 check(prepare(programs[4].data(),20,&n,&lease)==nullptr);
 const auto before=hashes;rejects([&]{prepare(programs[0].data(),24,&n,&lease);});check(hashes==before);
 failed=false;programs[0][4]=1;rejects([&]{prepare(programs[0].data(),20,&n,&lease);});programs[0][4]=0;
 reset();qwen_app_register_additional_shader(programs[0].data(),20,sha[0].data());qwen_app_register_additional_shader(programs[0].data(),20,sha[0].data());check(registration_fault.load()&&additional_count==1);
 reset();initialized=true;qwen_app_register_additional_shader(programs[0].data(),20,sha[0].data());check(registration_fault.load()&&additional_count==0);
 reset();for(unsigned i=0;i<5;++i)qwen_app_register_additional_shader(programs[i].data(),20,sha[i].data());check(registration_fault.load()&&additional_count==4);
 reset();auto bad=sha[1];bad[0]^=1;qwen_app_register_additional_shader(programs[0].data(),20,sha[0].data());qwen_app_register_additional_shader(programs[1].data(),20,bad.data());rejects([]{verify_additional_shader();});check(qwen_app_additional_shaders_verified()==0);rejects([&]{prepare(programs[0].data(),20,&n,&lease);});
 for(unsigned mode=0;mode<4;++mode){reset();const void*p=programs[0].data();std::size_t size=20;
  if(mode==0)p=static_cast<const unsigned char*>(p)+1;
  if(mode==1)size=16;if(mode==2)size=21;if(mode==3)programs[0][0]=0;
  qwen_app_register_additional_shader(p,size,sha[0].data());rejects([]{verify_additional_shader();});check(qwen_app_additional_shaders_verified()==0);programs[0][0]=0x07230203;
 }
 std::cout<<"{\"assertions\":"<<assertions<<",\"record_bytes\":"<<sizeof(additional_shaders)<<",\"completed\":true}\n";
}
'''.replace('REGISTRY_STATE',STATE).replace('REGISTRY_PREPARE',PREPARE)
    source.write_text(code,newline='\n');obj=a.out/'sha256.o';exe=a.out/'registry-check.exe'
    commands=[[str(a.compiler.with_name('clang.exe')),'-O2','-I',str(sha.parent),'-c',str(sha/'sha256.c'),'-o',str(obj)],
              [str(a.compiler),'-std=c++17','-O2','-I',str(sha),str(source),str(obj),'-o',str(exe)]]
    env=dict(os.environ,PATH=str(a.compiler.parent)+os.pathsep+os.environ.get('PATH',''))
    for i,cmd in enumerate(commands):
        r=subprocess.run(cmd,capture_output=True,timeout=90,env=env);(a.out/f'{i}.private.log').write_bytes(r.stdout+r.stderr)
        require(r.returncode==0,r.stderr.decode(errors='replace')[-1700:])
    r=subprocess.run([str(exe)],capture_output=True,timeout=30,env=env);require(r.returncode==0,r.stderr.decode(errors='replace'))
    result=json.loads(r.stdout);require(result['assertions']>=25 and result['record_bytes']==192,'All bounded registry cases required')
    result.update(implementation=record(ROOT/'tools/multiple_shader_source.py'),real_SHA256_source=record(sha/'sha256.c'),
        commands=commands,source=record(source),PS5_operations=0,model_inference=False,CI_runs=0)
    write_json(a.out/'result.private.json',result);print(json.dumps({k:result[k]for k in ('completed','assertions','record_bytes')}))

if __name__=='__main__':main()
