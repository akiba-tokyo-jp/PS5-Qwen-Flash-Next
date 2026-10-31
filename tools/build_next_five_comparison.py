#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build a fixed latest-control comparison; no console operations."""
import argparse,copy,json
from pathlib import Path
from active_native_inputs import active_link_inputs
from build_cache_capacity_1125 import recipes,literal
from build_speculative_batch_probe import once
from expert_q4 import require,record,write_json
from scoped_native_variant import link,seal

ROOT=Path(__file__).resolve().parents[1]
VARIANTS={'routing4':1,'routing2':2,'adaptive':3,'speculation':4,'io-refill':5,'KV16':6,'KV8':7}

def command_for(n,stem):
    found={c[c.index('-o')+1]:c for c in recipes(n) if '-c'in c and '-o'in c and c[c.index('-o')+1]in n['link_command'] and Path(c[c.index('-c')+1]).name==stem}
    require(len(found)==1,'One linked provider required: '+stem);return next(iter(found.values()))

def update_sources(r,jobs,sources):
    for key in ('normal_performance','output_Q8_normal','cold_request','resident_all_Q8','resident_cache3072','resident_small_rows','resident_weight_normal','memory_quality_cohort'):
        r[key]['actual_sources'].update(sources);r[key]['commands'].update(jobs)
    r['all_Q2_optimized_monitor']['actual_entry']=sources['entry'];r['all_Q2_optimized_monitor']['commands'][0]=jobs['entry'];r['routing_winners_normal']['actual_entry']=sources['entry']
    if 'owner'in sources:r['all_Q2_optimized_monitor']['actual_owner']=sources['owner'];r['all_Q2_optimized_monitor']['commands'][1]=jobs['owner']
    r['GDN_model_comparison']['actual_sources'].update(sources);r['GDN_model_comparison']['commands'].update(jobs)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('parent','control','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--variant',choices=VARIANTS,required=True);a=p.parse_args();n=json.loads(a.parent.read_text());control=json.loads(a.control.read_text());a.out.mkdir(parents=True,exist_ok=False)
    require(n['four_next_rollback']['scope']['n_rs_seq']==1,'Qualified native rollback parent required')
    for row in active_link_inputs(control):require(record(row['path'])==row,'Latest installed control changed')
    v=VARIANTS[a.variant];ec=n['compile_commands'][0];cc=command_for(n,'routing.private.cpp');gc=command_for(n,'graph.private.cpp');en=n['routing_sharing']['commands'][2]
    oc=control['all_Q2_optimized_monitor']['commands'][1].copy();oc[oc.index('-o')+1]=n['all_Q2_optimized_monitor']['commands'][1][n['all_Q2_optimized_monitor']['commands'][1].index('-o')+1]
    seed=copy.deepcopy(n);seed['inputs_before']+=active_link_inputs(control);seedpath=a.out/'seed.private.json';write_json(seedpath,seed)
    scope=dict(n['GDN_model_comparison']['scope'],schema='ps5-qwen-next-five-comparison-v1',candidate=a.variant,candidate_id=v,
        original_single_token_fusion_in_both_arms=True,compact_rollback_in_both_arms=True,placement_keys_in_both_arms=768,
        candidate_F32_and_token_equality_required=v==5,quality_forces_EOS_rejections=True,software_limits_are_not_hardware_limits=True)
    entry=Path(ec[ec.index('-c')+1]).read_text();entry='#include "next_five_policy.h"\n#include "next_five_causal.h"\n'+entry
    entry=once(entry,literal(n['GDN_model_comparison']['scope']),literal(scope));entry=once(entry,'qwen_app_compact_rollback_select(arm==1);','qwen_app_compact_rollback_select(true);qwen_next_select(arm?'+str(v)+':0);')
    entry=entry.replace('qwen_app::CausalRollbackEngine','qwen_app::NextFiveCausalEngine')
    entry=once(entry,'const char *arm_name=arm==0?"original-convolution-normalization":"fused-convolution-normalization";', 'const char *arm_name=arm==0?"installed-control":'+json.dumps(a.variant)+';')
    entry=once(entry,'(compare&&rows!=io_rows[hash_arm])','(compare&&arm==0&&rows!=io_rows[hash_arm])')
    entry=once(entry,'else if(result.token_ids!=speed_ids[hash_arm][task]||result.output_bytes!=speed_bytes[hash_arm][task])','else if(arm==0&&(result.token_ids!=speed_ids[hash_arm][task]||result.output_bytes!=speed_bytes[hash_arm][task]))')
    entry=once(entry,'if(compare&&io_max_error!=0){double total_kl=0;','if(compare&&io_max_error!=0&&rows==io_rows[hash_arm]&&result.token_ids==speed_ids[hash_arm][task]){double total_kl=0;')
    entry=once(entry,'{"enabled",arm==1},{"complete_captures_elided"','{"enabled",true},{"complete_captures_elided"')
    entry=once(entry,'            row["phase"]=phase;','            std::uint64_t next_stats[4]{};qwen_next_routing_stats(next_stats);row["next_five"]={{"variant",qwen_next_variant()},{"Expert_count_events",{next_stats[0],next_stats[1],next_stats[2]}},{"ranked_rows",next_stats[3]},{"KV_bits",'+('arm?'+('16'if v==6 else'8')+':32'if v in(6,7)else'32')+'}};\n            row["phase"]=phase;')
    if v==5:
        entry=once(entry,'if(compare&&arm==0&&(io_max_error!=0||bitwise_error))','if(compare&&(io_max_error!=0||bitwise_error))')
    owner=Path(oc[oc.index('-c')+1]).read_text();oldheader=Path(oc[oc.index('-c')+1]).parent/'limit-winner-bundle.private.h';header=a.out/oldheader.name;header.write_bytes(oldheader.read_bytes())
    require('Q2_trial_mode=true'in header.read_text(),'Latest768 placement must be selected in both arms')
    routing=Path(cc[cc.index('-c')+1]).read_text();routing='#include "next_five_policy.h"\n#include "next_five_routing.inc"\n'+routing
    routing=once(routing,'extern "C" void qwen_app_routing_event_begin(){','extern "C" void qwen_app_routing_event_begin(){\n    next_event();')
    routing=once(routing,'    for(unsigned row=0;row<unsigned(elements/512);++row)\n        qwen_app::cache_rank_scores(source+row*512,target+row*512,cached,512,1.5f);','    for(unsigned row=0;row<unsigned(elements/512);++row){next_rank(source+row*512,cached);qwen_app::cache_rank_scores(source+row*512,target+row*512,cached,512,1.5f);}')
    routing=once(routing,'unsigned six_key(){return (six_mode<<5)|(qwen_app_route_mode()<<1)|unsigned(qwen_app_route_is_decode());}','unsigned six_key(){return ((six_mode<<5)|(qwen_app_route_mode()<<1)|unsigned(qwen_app_route_is_decode()))*8+qwen_next_experts();}')
    graph=Path(gc[gc.index('-c')+1]).read_text();graph='#include "next_five_policy.h"\n'+graph
    graph=once(graph,'n_expert_used=qwen_app::decode_policy_experts(qwen_app_route_mode(),unsigned(n_tokens));','n_expert_used=qwen_next_experts();')
    variants=dict(entry=(ec,entry),owner=(oc,owner),routing=(cc,routing),graph=(gc,graph))
    if v in(6,7):
        entry=once(entry,'                resident_reset_empty_context(context,model,startup.admission_report);',
            '                llama_free(context);context=nullptr;resident_reused_context=nullptr;\n                context=llama_init_from_model(model,qwen_app::streaming_context_params(256,memory_budget.expert_cache,32));\n                if(!context)throw std::runtime_error("Changed KV context allocation failed");\n                resident_reset_empty_context(context,model,startup.admission_report);')
        variants['entry']=(ec,entry)
        engine=Path(en[en.index('-c')+1]).read_text();engine='#include "next_five_policy.h"\n'+engine
        engine=once(engine,'params.type_k = params.type_v = GGML_TYPE_F32;','params.type_k = params.type_v = qwen_next_variant()=='+str(v)+'?'+('GGML_TYPE_F16'if v==6 else'GGML_TYPE_Q8_0')+':GGML_TYPE_F32;')
        variants['engine']=(en,engine)
    if v==5:
        stream=(ROOT/'native/app/streaming_read_pool.h').read_text();stream='#include <cstdlib>\n#include <cstring>\n#include "next_five_policy.h"\n'+stream
        stream=once(stream,'    std::uint64_t occupancy_at_=0;','    void*refill_copy_=nullptr;\n    std::uint64_t occupancy_at_=0;')
        stream=once(stream,'        try{for(unsigned i=0;i<4;++i)', '        if(posix_memalign(&refill_copy_,16384,2u<<20)||!refill_copy_)throw std::runtime_error("Owned producer copy allocation failed");\n        try{for(unsigned i=0;i<4;++i)')
        start='            delivery_[5]+=now_ns()-s.ready_ns;'
        code='''            if(qwen_next_refill_before_consume()&&!failure&&!error&&got==std::int64_t(request.bytes)){
                lock.unlock();std::memcpy(refill_copy_,request.target,std::size_t(got));lock.lock();
                s.state=State::idle;--live;++completed;if(next<count)queue(lane);
                if(!failure){const auto began=now_ns();lock.unlock();try{consume(id,refill_copy_,got);}catch(...){failure=std::current_exception();}lock.lock();delivery_[6]+=now_ns()-began;}
                continue;
            }
'''
        stream=once(stream,start,start+'\n'+code)
        stream=once(stream,'if(threads_[i].joinable())threads_[i].join();}', 'if(threads_[i].joinable())threads_[i].join();std::free(refill_copy_);refill_copy_=nullptr;}')
        (a.out/'streaming_read_pool.h').write_text(stream,newline='\n')
    deps=[Path(__file__),a.control,header,ROOT/'native/app/next_five_policy.h',ROOT/'native/app/next_five_causal.h',ROOT/'native/app/next_five_routing.inc']
    if v==5:deps.append(a.out/'streaming_read_pool.h')
    for label,(cmd,text)in list(variants.items()):variants[label]=(cmd+['-I',str(ROOT/'native/app')],text)
    r,jobs,sources=link(seedpath,a.out,variants,deps);update_sources(r,jobs,sources)
    r['GDN_model_comparison']['scope']=scope;r['next_five_comparison']=dict(scope=scope,actual_sources=sources,commands=jobs,control=record(a.control),production_adopted=False)
    seal(r,a.workspace,a.cache,a.out);write_json(a.out/'core-safety.private.json',dict(completed=True,kind='next_five_latest_control',scope=scope,candidate=record(a.out/'receipt.private.json'),PS5_operations=0,CI_runs=0))

if __name__=='__main__':main()
