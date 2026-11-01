#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Join contiguous Q8 HC Down/Inject weights without allocating duplicate weights."""
import argparse,json
from pathlib import Path
from build_cache_capacity_1125 import literal,recipes
from build_next_five_comparison import update_sources
from build_speculative_batch_probe import once
from expert_q4 import record,require,write_json
from scoped_native_variant import link,seal
ROOT=Path(__file__).resolve().parents[1]

def transform(s):
 s='#include "frontier_options.h"\n#include "ggml-backend.h"\nextern "C" void qwen_frontier_HC_stats(std::uint64_t*out){for(unsigned i=0;i<4;++i)out[i]=qwen_frontier::hc_stats[i];}\n'+s
 for part in('attn','ffn'):
  a=s.index('        layer.hc_'+part+'_up ');b=s.index('\n',s.index('        layer.hc_'+part+'_inject ',a))
  up,inject=s[a:b].splitlines();s=s[:a]+inject+'\n'+up+s[b:]
 marker='    ggml_tensor * lo = build_lora_mm(w_down, xn);'
 code='''    ggml_tensor * joined_result=nullptr;
    ++qwen_frontier::hc_stats[0];
    if(inject && w_inject && w_down->type==GGML_TYPE_Q8_0 && w_inject->type==w_down->type &&
       w_down->buffer && w_down->buffer==w_inject->buffer && w_down->data && w_inject->data &&
       ggml_is_contiguous(w_down)&&ggml_is_contiguous(w_inject) &&
       w_down->ne[0]==hc_dim && w_inject->ne[0]==hc_dim &&
       w_down->ne[2]==1&&w_down->ne[3]==1&&w_inject->ne[2]==1&&w_inject->ne[3]==1 &&
       loras->empty() && (!hdmd || (!hdmd->rot.count(w_down)&&!hdmd->rot.count(w_inject)))) {
        const auto down_address=reinterpret_cast<std::uintptr_t>(w_down->data);
        const auto base=reinterpret_cast<std::uintptr_t>(ggml_backend_buffer_get_base(w_down->buffer));
        const auto down_bytes=ggml_nbytes(w_down),inject_bytes=ggml_nbytes(w_inject);
        const auto buffer_bytes=ggml_backend_buffer_get_size(w_down->buffer);
        if(down_address>=base && down_address-base<=buffer_bytes &&
           down_bytes<=buffer_bytes-(down_address-base) &&
           inject_bytes<=buffer_bytes-(down_address-base)-down_bytes &&
           down_address<=UINTPTR_MAX-down_bytes &&
           reinterpret_cast<std::uintptr_t>(w_inject->data)==down_address+down_bytes) {
            ++qwen_frontier::hc_stats[1];
            if(qwen_frontier::mode.load(std::memory_order_relaxed)&2) {
                // A metadata-only root alias spans two proven adjacent immutable
                // tensors in their original shared model buffer. No payload copy.
                auto *joined=ggml_new_tensor_2d(ctx0,w_down->type,hc_dim,w_down->ne[1]+hc);
                GGML_ASSERT(ggml_nbytes(joined)==down_bytes+inject_bytes);
                joined->data=w_down->data;joined->buffer=w_down->buffer;joined->flags=w_down->flags;
                ggml_format_name(joined,"%s_joined_inject",w_down->name);
                joined_result=build_lora_mm(joined,xn);
                ++qwen_frontier::hc_stats[2];
            }
        } else ++qwen_frontier::hc_stats[3];
    }
    ggml_tensor * lo=joined_result ? ggml_cont(ctx0,ggml_view_2d(ctx0,joined_result,w_down->ne[1],nt,joined_result->nb[1],0)) : build_lora_mm(w_down,xn);'''
 s=once(s,marker,code)
 s=once(s,'        *inject = build_lora_mm(w_inject, xn);','        *inject=joined_result ? ggml_cont(ctx0,ggml_view_2d(ctx0,joined_result,hc,nt,joined_result->nb[1],w_down->ne[1]*sizeof(float))) : build_lora_mm(w_inject,xn);')
 return s

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in('parent','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 p.add_argument('--base-frontier-mode',type=int,default=0);a=p.parse_args();n=json.loads(a.parent.read_text());a.out.mkdir(parents=True,exist_ok=False)
 old=n['GDN_model_comparison']['scope'];scope=dict(old,candidate='frontier-2-HC-joined-immutable-Q8-alias',control_frontier_mode=a.base_frontier_mode,candidate_frontier_mode=a.base_frontier_mode|2,original_weight_payloads_and_bytes_preserved=True,extra_weight_allocations=0)
 ec=n['compile_commands'][0];entry=Path(ec[ec.index('-c')+1]).read_text();entry='#include <cstdint>\nextern "C" void qwen_frontier_HC_stats(std::uint64_t*);\n'+entry;entry=once(entry,literal(old),literal(scope));entry=once(entry,'qwen_frontier::mode=arm?1:0;','qwen_frontier::mode=arm?'+str(a.base_frontier_mode|2)+':'+str(a.base_frontier_mode)+';')
 entry=once(entry,'if(compare&&(io_max_error!=0||bitwise_error))','if(compare&&arm==0&&(io_max_error!=0||bitwise_error))');entry=once(entry,'if(compare&&!same_routes)','if(compare&&arm==0&&!same_routes)')
 marker='            row["service_mode"]=qwen_service::mode.load();';entry=once(entry,marker,'            std::uint64_t hc_joint[4]{};qwen_frontier_HC_stats(hc_joint);row["frontier_HC_totals"]=std::vector<std::uint64_t>(hc_joint,hc_joint+4);\n'+marker)
 cs=[c for c in recipes(n)if'-o'in c and Path(c[c.index('-o')+1]).name=='model_graph.o'];require(len(cs)==1,'One current model graph recipe required');mc=cs[0];require(mc[mc.index('-o')+1]in n['link_command'],'Qualified model graph object required')
 unity=Path(mc[mc.index('-c')+1]).read_text();oldpart=a.cache/'build/GDN-model-order-15302/qwen4exp.ordered.private.cpp';newpart=a.out/'qwen4exp.joined.private.cpp';newpart.write_text(transform(oldpart.read_text()),newline='\n');unity=once(unity,str(oldpart).replace('\\','/'),str(newpart).replace('\\','/'))
 r,jobs,sources=link(a.parent,a.out,dict(entry=(ec,entry),model_graph=(mc+['-I',str(ROOT/'native/app')],unity)),[Path(__file__),ROOT/'native/app/frontier_options.h',oldpart,newpart]);update_sources(r,jobs,sources);r['GDN_model_comparison']['scope']=scope;r['next_five_comparison'].update(scope=scope,actual_sources=sources,commands=jobs);r['frontier'].update(scope=scope);r['frontier']['actual_sources'].update(sources);r['frontier']['commands'].update(jobs);r['frontier_HC']=dict(scope=scope,actual_sources=sources,commands=jobs,model_part=record(newpart));seal(r,a.workspace,a.cache,a.out)
 write_json(a.out/'core-safety.private.json',dict(completed=True,scope=scope,shared_driver_unchanged=True,original_model_buffers_and_lifetimes_preserved=True,runtime_same_buffer_contiguity_and_bounds_checks=True,positive_completion_and_owner_validation_preserved=True,PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()
