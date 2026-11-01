#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compare one checked, zero-copy decode projection against separate GDN Q4 projections."""
import argparse,json
from pathlib import Path
from build_next_five_comparison import update_sources
from build_cache_capacity_1125 import literal
from build_speculative_batch_probe import once
from expert_q4 import record,require,write_json
from scoped_native_variant import link,seal
ROOT=Path(__file__).resolve().parents[1]

def transform(source):
 source='#include "throughput_options.h"\n'+source
 old='    ggml_tensor * qkv_mixed = build_lora_mm(model.layers[il].wqkv, input, model.layers[il].wqkv_s);'
 new='''    ggml_tensor * joined_projection=nullptr;
    auto *qkv_weight=model.layers[il].wqkv;
    auto *gate_weight=model.layers[il].wqkv_gate;
    ++qwen_throughput::stats[3];
    if(input->ne[1]==1&&input->ne[2]==1&&input->ne[3]==1&&n_seqs==1&&n_seq_tokens==1&&
       qkv_weight&&gate_weight&&qkv_weight->type==GGML_TYPE_Q4_0&&gate_weight->type==qkv_weight->type&&
       !model.layers[il].wqkv_s&&!model.layers[il].wqkv_gate_s&&loras->empty()&&
       (!hdmd||(!hdmd->rot.count(qkv_weight)&&!hdmd->rot.count(gate_weight)))&&
       qkv_weight->buffer&&qkv_weight->buffer==gate_weight->buffer&&qkv_weight->data&&gate_weight->data&&
       ggml_is_contiguous(qkv_weight)&&ggml_is_contiguous(gate_weight)&&
       qkv_weight->ne[0]==input->ne[0]&&gate_weight->ne[0]==input->ne[0]&&
       qkv_weight->ne[2]==1&&qkv_weight->ne[3]==1&&gate_weight->ne[2]==1&&gate_weight->ne[3]==1){
        const auto at=reinterpret_cast<std::uintptr_t>(qkv_weight->data);
        const auto base=reinterpret_cast<std::uintptr_t>(ggml_backend_buffer_get_base(qkv_weight->buffer));
        const auto bytes=ggml_backend_buffer_get_size(qkv_weight->buffer);
        const auto qbytes=ggml_nbytes(qkv_weight),gbytes=ggml_nbytes(gate_weight);
        if(at>=base&&at-base<=bytes&&qbytes<=bytes-(at-base)&&gbytes<=bytes-(at-base)-qbytes&&
           at<=UINTPTR_MAX-qbytes&&reinterpret_cast<std::uintptr_t>(gate_weight->data)==at+qbytes){
            ++qwen_throughput::stats[4];
            if(qwen_throughput::mode.load(std::memory_order_relaxed)&2){
                auto *joined=ggml_new_tensor_2d(ctx0,qkv_weight->type,qkv_weight->ne[0],qkv_weight->ne[1]+gate_weight->ne[1]);
                GGML_ASSERT(ggml_nbytes(joined)==qbytes+gbytes);
                joined->data=qkv_weight->data;joined->buffer=qkv_weight->buffer;joined->flags=qkv_weight->flags;
                ggml_format_name(joined,"%s_joined_gate",qkv_weight->name);
                joined_projection=build_lora_mm(joined,input);
                ++qwen_throughput::stats[5];
            }
        }else ++qwen_throughput::stats[6];
    }
    ggml_tensor * qkv_mixed=joined_projection ? ggml_reshape_2d(ctx0,ggml_view_1d(ctx0,joined_projection,qkv_weight->ne[1],0),qkv_weight->ne[1],1) : build_lora_mm(qkv_weight,input,model.layers[il].wqkv_s);'''
 source=once(source,old,new)
 return once(source,'    ggml_tensor * z = build_lora_mm(model.layers[il].wqkv_gate, input, model.layers[il].wqkv_gate_s);','    ggml_tensor * z=joined_projection ? ggml_reshape_2d(ctx0,ggml_view_1d(ctx0,joined_projection,gate_weight->ne[1],qkv_weight->ne[1]*sizeof(float)),gate_weight->ne[1],1) : build_lora_mm(gate_weight,input,model.layers[il].wqkv_gate_s);')

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in('parent','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();n=json.loads(a.parent.read_text());a.out.mkdir(parents=True,exist_ok=False)
 old=n['GDN_model_comparison']['scope'];scope=dict(old,candidate='throughput-2-GDN-common-input-Q4-joined-decode',control_frontier_mode=7,candidate_frontier_mode=7,control_throughput_mode=0,candidate_throughput_mode=2,metadata_only_weight_alias=True,original_weight_payloads_and_bytes_preserved=True,extra_weight_allocations=0)
 ec=n['compile_commands'][0];entry=Path(ec[ec.index('-c')+1]).read_text();entry='#include "throughput_options.h"\n'+entry
 entry=once(entry,literal(old),literal(scope));entry=once(entry,'qwen_frontier::mode=arm?11:3;','qwen_frontier::mode=7;qwen_throughput::mode=arm?2:0;')
 marker='            row["service_mode"]=qwen_service::mode.load();';entry=once(entry,marker,'            row["throughput_mode"]=qwen_throughput::mode.load();row["throughput_totals"]=std::vector<std::uint64_t>(qwen_throughput::stats,qwen_throughput::stats+12);\n'+marker)
 mc=n['frontier']['commands']['model_graph'];require(mc[mc.index('-o')+1]in n['link_command'],'Current selected model graph provider required')
 unity=Path(mc[mc.index('-c')+1]).read_text();oldpart=Path(n['frontier_HC']['model_part']['path']);newpart=a.out/'qwen4exp.joined-GDN.private.cpp';newpart.write_text(transform(oldpart.read_text()),newline='\n');unity=once(unity,str(oldpart).replace('\\','/'),str(newpart).replace('\\','/'))
 r,jobs,sources=link(a.parent,a.out,dict(entry=(ec,entry),model_graph=(mc+['-I',str(ROOT/'native/app')],unity)),[Path(__file__),ROOT/'native/app/throughput_options.h',oldpart,newpart]);update_sources(r,jobs,sources)
 r['GDN_model_comparison']['scope']=scope;r['next_five_comparison'].update(scope=scope,actual_sources=sources,commands=jobs);r['frontier']['scope']=scope;r['frontier']['actual_sources'].update(sources);r['frontier']['commands'].update(jobs)
 r['throughput']=dict(scope=scope,actual_sources=sources,commands=jobs,model_part=record(newpart));seal(r,a.workspace,a.cache,a.out)
 write_json(a.out/'core-safety.private.json',dict(completed=True,scope=scope,shared_driver_unchanged=True,same_buffer_adjacency_and_bounds_checked=True,LoRA_Hadamard_and_scale_fallbacks_preserved=True,ordinary_positive_completion_and_owner_validation_preserved=True,PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()
