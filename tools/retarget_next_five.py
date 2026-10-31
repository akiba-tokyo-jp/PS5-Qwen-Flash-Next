#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reuse qualified compiled providers and rebuild only changed experiment roles."""
import argparse,copy,json
from pathlib import Path
from build_next_five_comparison import VARIANTS,command_for,update_sources,ROOT
from build_cache_capacity_1125 import literal
from build_speculative_batch_probe import once
from expert_q4 import require,record,write_json
from scoped_native_variant import link,seal

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('parent','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--variant',choices=VARIANTS,required=True);a=p.parse_args();n=json.loads(a.parent.read_text());a.out.mkdir(parents=True,exist_ok=False)
    old=n['next_five_comparison']['scope'];scope=dict(old,candidate=a.variant,candidate_id=VARIANTS[a.variant],candidate_F32_and_token_equality_required=a.variant=='io-refill',variable_Expert_capture_counts=[2,4,6,8,10])
    v=scope['candidate_id'];ec=n['compile_commands'][0];entry=Path(ec[ec.index('-c')+1]).read_text();entry=once(entry,literal(old),literal(scope));entry=once(entry,'qwen_next_select(arm?'+str(old['candidate_id'])+':0);','qwen_next_select(arm?'+str(v)+':0);')
    entry=once(entry,'arm==0?"installed-control":'+json.dumps(old['candidate'])+';','arm==0?"installed-control":'+json.dumps(a.variant)+';')
    entry=once(entry,'throw std::runtime_error("Complete actual additional routes required");','throw std::runtime_error("Complete actual additional routes required: "+routes.at(ordinal).error);')
    variants=dict(entry=(ec,entry));deps=[Path(__file__),ROOT/'native/app/next_five_causal.h',ROOT/'native/app/next_five_policy.h']
    capture=command_for(n,'capture.private.cpp');cap=Path(capture[capture.index('-c')+1]).read_text()
    if '(used!=6&&used!=8&&used!=10)'in cap:cap=once(cap,'(used!=6&&used!=8&&used!=10)','(used!=2&&used!=4&&used!=6&&used!=8&&used!=10)')
    variants['capture']=(capture,cap)
    if v in(6,7):
        entry=once(entry,'                resident_reset_empty_context(context,model,startup.admission_report);','                llama_free(context);context=nullptr;resident_reused_context=nullptr;\n                context=llama_init_from_model(model,qwen_app::streaming_context_params(256,memory_budget.expert_cache,32));\n                if(!context)throw std::runtime_error("Changed KV context allocation failed");\n                resident_reset_empty_context(context,model,startup.admission_report);')
        entry=once(entry,'{"KV_bits",32}','{"KV_bits",arm?'+('16'if v==6 else'8')+':32}')
        enginecmd=n['routing_sharing']['commands'][2];engine=Path(enginecmd[enginecmd.index('-c')+1]).read_text();engine='#include "next_five_policy.h"\n'+engine
        engine=once(engine,'params.type_k = params.type_v = GGML_TYPE_F32;','params.type_k = params.type_v = qwen_next_variant()=='+str(v)+'?'+('GGML_TYPE_F16'if v==6 else'GGML_TYPE_Q8_0')+':GGML_TYPE_F32;')
        variants['engine']=(enginecmd,engine);variants['entry']=(ec,entry)
    if v==5:
        ownercmd=n['all_Q2_optimized_monitor']['commands'][1];owner=Path(ownercmd[ownercmd.index('-c')+1]).read_text();(a.out/'limit-winner-bundle.private.h').write_bytes((Path(ownercmd[ownercmd.index('-c')+1]).parent/'limit-winner-bundle.private.h').read_bytes())
        stream=(ROOT/'native/app/streaming_read_pool.h').read_text();stream='#include <cstdlib>\n#include <cstring>\n#include "next_five_policy.h"\n'+stream
        stream=once(stream,'    std::uint64_t occupancy_at_=0;','    void*refill_copy_=nullptr;\n    std::uint64_t occupancy_at_=0;')
        stream=once(stream,'        try{for(unsigned i=0;i<4;++i)','        if(posix_memalign(&refill_copy_,16384,2u<<20)||!refill_copy_)throw std::runtime_error("Owned producer copy allocation failed");\n        try{for(unsigned i=0;i<4;++i)')
        marker='            delivery_[5]+=now_ns()-s.ready_ns;'
        code='''            if(qwen_next_refill_before_consume()&&!failure&&!error&&got==std::int64_t(request.bytes)){
                lock.unlock();std::memcpy(refill_copy_,request.target,std::size_t(got));lock.lock();
                s.state=State::idle;--live;++completed;if(next<count)queue(lane);
                if(!failure){const auto began=now_ns();lock.unlock();try{consume(id,refill_copy_,got);}catch(...){failure=std::current_exception();}lock.lock();delivery_[6]+=now_ns()-began;}
                continue;
            }
'''
        stream=once(stream,marker,marker+'\n'+code);stream=once(stream,'if(threads_[i].joinable())threads_[i].join();}','if(threads_[i].joinable())threads_[i].join();std::free(refill_copy_);refill_copy_=nullptr;}')
        (a.out/'streaming_read_pool.h').write_text(stream,newline='\n');deps+=[a.out/'streaming_read_pool.h',a.out/'limit-winner-bundle.private.h'];variants['owner']=(ownercmd,owner)
        entry=once(entry,'if(compare&&arm==0&&(io_max_error!=0||bitwise_error))','if(compare&&(io_max_error!=0||bitwise_error))');variants['entry']=(ec,entry)
    variants={k:(cmd+['-I',str(ROOT/'native/app')],text)for k,(cmd,text)in variants.items()}
    r,jobs,sources=link(a.parent,a.out,variants,deps);update_sources(r,jobs,sources);r['GDN_model_comparison']['scope']=scope
    r['next_five_comparison']=dict(scope=scope,actual_sources=sources,commands=jobs,control=n['next_five_comparison']['control'],production_adopted=False)
    seal(r,a.workspace,a.cache,a.out);write_json(a.out/'core-safety.private.json',dict(completed=True,kind='next_five_latest_control',scope=scope,candidate=record(a.out/'receipt.private.json'),PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()
