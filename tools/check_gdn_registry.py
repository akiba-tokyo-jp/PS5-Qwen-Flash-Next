#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise the actual generated registry walk against the lazy compile contract."""
import argparse,os,subprocess
from pathlib import Path
from build_io_gpu_comparison import GPU_STATE
from expert_q4 import record,write_json,require
STUB=r'''
#include <array>
#include <algorithm>
#include <memory>
#include <mutex>
#include <cstdint>
#include <stdexcept>
#include <vector>
#include <iostream>
namespace vk {struct Device{};}
struct Pipe{bool compile_pending=false,compiled=false;std::shared_ptr<Pipe>next;};
using vk_pipeline=std::shared_ptr<Pipe>;
struct Device{vk::Device device;unsigned subgroup_size=32,vendor_id=1,subgroup_min_size=32,subgroup_max_size=64;bool subgroup_size_control=false,subgroup_arithmetic=true,subgroup_clustered=true;};
using vk_device=std::shared_ptr<Device>;
constexpr unsigned VK_VENDOR_ID_INTEL=2;
unsigned destroyed=0,visits=0;
void need(bool v){if(!v)throw std::runtime_error("Actual GDN registry/lazy protocol failed");}
void ggml_vk_destroy_pipeline(vk::Device&,vk_pipeline&p){need(p->compiled&&!p->compile_pending);++destroyed;}
bool is_pow2(unsigned v){return v&&!(v&(v-1));}
#define GGML_ASSERT(v) need(v)
unsigned gated_delta_net_f32_len=4,gated_delta_net_f32_nocluster_len=4,gated_delta_net_f32_shmem_len=4;
unsigned char gated_delta_net_f32_data[4]{},gated_delta_net_f32_nocluster_data[4]{},gated_delta_net_f32_shmem_data[4]{};
struct vk_op_gated_delta_net_push_constants{};
'''
TAIL=r'''
static void ggml_app_phase(const char*){}
void walk(vk_device&device,vk_pipeline requested={}){
 auto ggml_vk_create_pipeline=[&](vk_device&,vk_pipeline&p,const char*,size_t,const void*,const char*,unsigned,size_t,std::array<unsigned,3>w,const std::vector<unsigned>&s,unsigned,bool,bool,unsigned){
  ++visits;if(!p)p=std::make_shared<Pipe>();need(w[2]==4&&s[0]==128&&s[2]/s[3]==4&&128%s[3]==0);
  if(p==requested)p->compiled=true;
 };
REPLACE_ACTUAL_BLOCK
}
int main()try{
 auto d=std::make_shared<Device>();walk(d);need(visits==2);auto*r=qwen_gdn_find(d);need(r&&!r->pipelines[0]->compiled);
 auto*p=r;walk(d);need(visits==4&&qwen_gdn_find(d)==p);
 walk(d,r->pipelines[0]);need(visits==6&&r->pipelines[0]->compiled&&!r->pipelines[1]->compiled);
 walk(d,r->pipelines[1]);need(visits==8&&r->pipelines[1]->compiled);qwen_app_gdn_trial_select(true);
 r->pipelines[0]->compile_pending=true;bool refused=false;try{qwen_app_gdn_trial_release();}catch(const std::runtime_error&){refused=true;}
 need(refused&&destroyed==0&&qwen_gdn_find(d)==p);r->pipelines[0]->compile_pending=false;
 for(unsigned i=1;i<8;++i){auto next=std::make_shared<Device>();next->subgroup_size=i%2?64:32;next->subgroup_clustered=i%2;walk(next);}
 auto extra=std::make_shared<Device>();refused=false;try{walk(extra);}catch(const std::runtime_error&){refused=true;}need(refused);
 qwen_app_gdn_trial_release();need(destroyed==2);for(auto&row:qwen_gdn_trials)need(!row);
 std::cout<<"PASS: actual generated device registry, repeated shader walk, requested lazy compile,8-device bound, pending-owner refusal and compiled-handle retirement\n";return 0;
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}
'''
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in('source','compiler','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();text=a.source.read_text();require(text.count(GPU_STATE)==1,'Actual registry source must match the tested implementation');a.out.mkdir(parents=True,exist_ok=False)
 start=text.index('    {\n        std::lock_guard<std::mutex>lock(qwen_gdn_registry_mutex);',text.index('const uint32_t gdn_sizes[]'));end=text.index('\n    if (device->subgroup_arithmetic',start);block=text[start:end]
 cpp=a.out/'registry.private.cpp';cpp.write_text(STUB+GPU_STATE+TAIL.replace('REPLACE_ACTUAL_BLOCK',block),newline='\n');exe=a.out/'registry.exe';env=dict(os.environ,PATH=str(a.compiler.parent)+os.pathsep+os.environ.get('PATH',''))
 for i,cmd in enumerate([[str(a.compiler),'-std=c++17','-O2',str(cpp),'-o',str(exe)],[str(exe)]]):
  r=subprocess.run(cmd,capture_output=True,timeout=180,env=env);(a.out/f'{i}.private.log').write_bytes(r.stdout+r.stderr);require(r.returncode==0,(r.stdout+r.stderr).decode(errors='replace')[-3000:]);print(r.stdout.decode(),end='')
 write_json(a.out/'complete.private.json',dict(completed=True,actual_generated_source=record(a.source),host_only=True,shader_math_not_executed=True,lazy_compile_registry_and_normal_retirement_checked=True,PS5_operations=0))
if __name__=='__main__':main()
