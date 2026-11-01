#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compare complete finite-row selection with the pinned upstream greedy body."""
import argparse,json,os,subprocess
from pathlib import Path
from expert_q4 import record,require,write_json
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--upstream',type=Path,required=True);p.add_argument('--compiler',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    upstream=a.upstream/'src/llama-sampler.cpp';text=upstream.read_text()
    start=text.index('static void llama_sampler_greedy_apply(');end=text.index('\nstatic bool llama_sampler_greedy_backend_init',start)
    body=text[start:end]
    code=r'''
#include "finite_greedy.h"
#include <algorithm>
#include <array>
#include <limits>
#include <random>
#include <vector>
#include <iostream>
struct llama_sampler {};
struct llama_token_data {std::int32_t id;float logit,p;};
struct llama_token_data_array {llama_token_data*data;std::size_t size;std::int64_t selected;bool sorted;};
UPSTREAM_BODY
int main(){
 std::mt19937 rng(971930);unsigned rows=0,errors=0,rejections=0;
 for(unsigned n:{1u,2u,31u,32u,33u,63u,64u,65u,513u,65537u,248320u})for(unsigned scenario=0;scenario<12;++scenario){
  std::vector<float>x(n);for(auto&v:x)v=float(int(rng()%2001)-1000)/37.0f;
  if(scenario==0)std::fill(x.begin(),x.end(),-std::numeric_limits<float>::max());
  if(scenario==1)std::fill(x.begin(),x.end(),-0.0f);
  if(scenario==2)std::fill(x.begin(),x.end(),std::numeric_limits<float>::max());
  if(n>64&&scenario==3){std::fill(x.begin(),x.end(),-1.0f);x[1]=x[64]=3.0f;}
  if(scenario==4)x.back()=1000.0f;
  std::vector<llama_token_data>c(n);for(unsigned i=0;i<n;++i)c[i]={int(i),x[i],0};
  llama_token_data_array r{c.data(),c.size(),-1,false};llama_sampler_greedy_apply(nullptr,&r);
  errors+=qwen_app::finite_greedy(x.data(),x.size())!=r.selected;++rows;
 }
 for(float bad:{std::numeric_limits<float>::quiet_NaN(),std::numeric_limits<float>::infinity(),-std::numeric_limits<float>::infinity()})
  for(unsigned at:{0u,31u,248319u}){std::vector<float>x(248320,1);x[at]=bad;try{qwen_app::finite_greedy(x.data(),x.size());++errors;}catch(const std::runtime_error&){++rejections;}}
 try{qwen_app::finite_greedy(nullptr,0);++errors;}catch(const std::invalid_argument&){++rejections;}
 try{float x=0;qwen_app::finite_greedy(&x,262145);++errors;}catch(const std::invalid_argument&){++rejections;}
 std::cout<<"{\"rows\":"<<rows<<",\"invalid_rejections\":"<<rejections<<",\"errors\":"<<errors<<"}\n";
 return errors?1:0;
}
'''.replace('UPSTREAM_BODY',body)
    source=a.out/'finite-greedy-reference.private.cpp';source.write_text(code,newline='\n')
    exe=a.out/'finite-greedy-reference.exe'
    command=[str(a.compiler),'-std=c++17','-O2','-fno-fast-math','-I',str(ROOT/'native/app'),str(source),'-o',str(exe)]
    env=dict(os.environ,PATH=str(a.compiler.parent)+os.pathsep+os.environ.get('PATH',''))
    r=subprocess.run(command,capture_output=True,timeout=90,env=env);(a.out/'build.private.log').write_bytes(r.stdout+r.stderr)
    require(r.returncode==0,r.stderr.decode(errors='replace')[-1500:])
    r=subprocess.run([str(exe)],capture_output=True,timeout=30,env=env);require(r.returncode==0,r.stderr.decode(errors='replace'))
    result=json.loads(r.stdout);require(result==dict(rows=132,invalid_rejections=11,errors=0),'Complete upstream comparison required')
    result.update(completed=True,upstream=record(upstream),implementation=record(ROOT/'native/app/finite_greedy.h'),
        source=record(source),command=command,model_inference=False,PS5_operations=0,CI_runs=0)
    write_json(a.out/'result.private.json',result);print(json.dumps({k:result[k]for k in ('completed','rows','invalid_rejections','errors')}))

if __name__=='__main__':main()
