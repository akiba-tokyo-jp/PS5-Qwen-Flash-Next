#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build a shared-model, stateless MTP-head feasibility and target-verification slice."""
import argparse,json,re,subprocess,sys
from pathlib import Path
from build_cache_capacity_1125 import literal,recipes
from build_next_five_comparison import update_sources
from build_speculative_batch_probe import once
from expert_q4 import record,require,write_json
from scoped_native_variant import link,seal
ROOT=Path(__file__).resolve().parents[1]
PREFIX=r'''
#include "llama_engine.h"
#include "llama-ext.h"
#include <array>
#include <functional>
#include <chrono>
#include <cmath>
namespace {
bool post_mtp_enabled=false;
struct PostMtpState {const void*owner=nullptr;llama_context*aux=nullptr;llama_batch_ext*batch=nullptr;
 std::array<float,10240>live{},saved{},pair0{};bool valid=false,saved_valid=false,pair_valid=false,unknown=false;std::function<int32_t()>draft;};
PostMtpState post_mtp;std::uint64_t post_mtp_stats[5]{};
}
extern "C" void qwen_post_mtp_select(bool v){post_mtp_enabled=v;}
extern "C" int32_t qwen_post_mtp_draft(){return post_mtp_enabled&&post_mtp.draft?post_mtp.draft():LLAMA_TOKEN_NULL;}
extern "C" void qwen_post_mtp_stats(std::uint64_t*out){std::copy_n(post_mtp_stats,5,out);}
'''
INSTALL=r'''
    if(post_mtp.owner)throw std::runtime_error("Only one target/MTP owner is admitted");
    post_mtp.owner=this;post_mtp.valid=post_mtp.saved_valid=post_mtp.pair_valid=false;
    llama_set_embeddings_nextn(context_,true,true);
    post_mtp.draft=[this]()->int32_t{
        if(!post_mtp_enabled||!ready_||!post_mtp.valid||pending_==LLAMA_TOKEN_NULL||llama_vocab_is_eog(vocabulary_,pending_)){++post_mtp_stats[4];return LLAMA_TOKEN_NULL;}
        const auto start=std::chrono::steady_clock::now();
        try {GpuBoundary boundary(gpu_begin_,gpu_complete_,gpu_retain_);post_mtp.unknown=true;
            if(!post_mtp.aux){auto p=llama_context_default_params();p.ctx_type=LLAMA_CONTEXT_TYPE_MTP;p.n_ctx=256;p.n_batch=p.n_ubatch=1;p.n_seq_max=p.n_rs_seq=1;
                p.n_threads=p.n_threads_batch=6;p.offload_kqv=true;p.op_offload=true;p.moe_cache_size=0;p.type_k=p.type_v=GGML_TYPE_F32;p.no_perf=false;
                post_mtp.aux=llama_init_from_model(model_,p);if(!post_mtp.aux)throw std::runtime_error("Shared-model MTP context unavailable");
                post_mtp.batch=llama_batch_ext_init(post_mtp.aux);if(!post_mtp.batch)throw std::runtime_error("MTP batch unavailable");++post_mtp_stats[2];}
            llama_memory_clear(llama_get_memory(post_mtp.aux),true);llama_batch_ext_clear(post_mtp.batch);
            const auto index=llama_batch_ext_add_token(post_mtp.batch,0,pending_);const llama_pos pos=position_;
            if(index<0||!llama_batch_ext_set_pos(post_mtp.batch,index,&pos)||!llama_batch_ext_set_output_logits(post_mtp.batch,index,true)||
               !llama_batch_ext_set_embd_state(post_mtp.batch,index,llama_embd{post_mtp.live.data(),1,post_mtp.live.size()}))throw std::runtime_error("Exact MTP hidden/token batch unavailable");
            if(llama_process(post_mtp.aux,LLAMA_PROCESS_TYPE_DECODE,post_mtp.batch)!=0)throw std::runtime_error("MTP auxiliary graph failed; retain owner");
            llama_synchronize(post_mtp.aux);if(gpu_checkpoint_)gpu_checkpoint_();post_mtp.unknown=false;
            const auto*logits=llama_get_logits_ith(post_mtp.aux,-1);const int count=llama_vocab_n_tokens(vocabulary_);if(!logits||count!=248320)throw std::runtime_error("Complete MTP logits required");
            int32_t best=0;for(int32_t i=0;i<count;++i){if(!std::isfinite(logits[i]))throw std::runtime_error("Non-finite MTP proposal logits");if(logits[i]>logits[best])best=i;}
            ++post_mtp_stats[0];++post_mtp_stats[3];boundary.complete();post_mtp_stats[1]+=std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now()-start).count();return best;
        }catch(...){failed_=true;throw;}
    };
'''
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in('parent','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();n=json.loads(a.parent.read_text());a.out.mkdir(parents=True,exist_ok=False);en=n['routing_sharing']['commands'][2]
 require(en[en.index('-o')+1]in n['link_command'],'Actual selected engine required');engine=PREFIX+Path(en[en.index('-c')+1]).read_text()
 engine=once(engine,'"\\\\.ffn_(gate|up|down|gate_up)_exps\\\\.weight$"','"^blk\\\\.([0-9]|[1-3][0-9]|4[0-7])\\\\.ffn_(gate|up|down|gate_up)_exps\\\\.weight$"')
 engine=once(engine,'params.load_mtp = false;','params.load_mtp = true;')
 anchor='        throw std::runtime_error("Sampler allocation failed");\n    }\n}'
 engine=once(engine,anchor,anchor[:-1]+INSTALL+'}')
 engine=once(engine,'    llama_sampler_free(sampler_);','''    if(post_mtp.owner==this){if(post_mtp.unknown)return;post_mtp.draft={};if(post_mtp.batch)llama_batch_ext_free(post_mtp.batch);if(post_mtp.aux)llama_free(post_mtp.aux);post_mtp.batch=nullptr;post_mtp.aux=nullptr;post_mtp.owner=nullptr;post_mtp.valid=false;}
    llama_sampler_free(sampler_);''')
 engine=once(engine,'    stage("inference_decode_synchronization_completed");','''    {const auto*h=llama_get_embeddings_nextn_ith(context_,-1);if(!h)throw std::runtime_error("Matched HC NextN hidden state missing");for(unsigned i=0;i<10240;++i){if(!std::isfinite(h[i]))throw std::runtime_error("Non-finite HC hidden state");post_mtp.live[i]=h[i];}post_mtp.valid=true;post_mtp.pair_valid=count==2;if(count==2){const auto*first=llama_get_embeddings_nextn_ith(context_,0);if(!first)throw std::runtime_error("First causal HC row missing");std::copy_n(first,10240,post_mtp.pair0.begin());}}
    stage("inference_decode_synchronization_completed");''')
 engine=once(engine,'    CheckpointApplicationState state{request_epoch_,position_,pending_,ready_,prompt_};','    post_mtp.saved=post_mtp.live;post_mtp.saved_valid=post_mtp.valid;\n    CheckpointApplicationState state{request_epoch_,position_,pending_,ready_,prompt_};')
 engine=once(engine,'    position_=saved.position;pending_=saved.pending;ready_=saved.ready;','    post_mtp.live=post_mtp.saved;post_mtp.valid=post_mtp.saved_valid;\n    position_=saved.position;pending_=saved.pending;ready_=saved.ready;')
 engine=once(engine,'                    ++position_;pending_=LLAMA_TOKEN_NULL;restored_logits_active_=true;++compact_rejections;','                    if(!post_mtp.pair_valid)throw std::runtime_error("Causal first HC row required after compact rejection");post_mtp.live=post_mtp.pair0;post_mtp.valid=true;\n                    ++position_;pending_=LLAMA_TOKEN_NULL;restored_logits_active_=true;++compact_rejections;')
 selected={c[c.index('-o')+1]:c for c in recipes(n)if '-c'in c and '-o'in c and c[c.index('-o')+1]in n['link_command']}
 choices=[c for c in selected.values()if 'selection_probs=ggml_map_custom1(ctx0,selection_probs,qwen_app_route_rank'in Path(c[c.index('-c')+1]).read_text()];require(len(choices)==1,'One actual routing graph provider required');gr=choices[0]
 graph=once(Path(gr[gr.index('-c')+1]).read_text(),'if(n_expert==512&&n_tokens<=2&&qwen_app_route_is_decode()&&qwen_app::routing_policy','if(il<48&&n_expert==512&&n_tokens<=2&&qwen_app_route_is_decode()&&qwen_app::routing_policy')
 old=n['GDN_model_comparison']['scope'];scope=dict(old,candidate='shared-model-stateless-matched-MTP-target-verified',MTP_weights_loaded_in_both_arms=True,trained_MTP_layer=48,HC_elements=10240,
  original_trunk_CPU_Expert_cache_unchanged=True,MTP_Experts_resident_no_second_full_model=True,stateless_auxiliary_KV=True,MTP_prefix_quality_claim=False,only_target_verified_tokens_emitted=True)
 ec=n['compile_commands'][0];entry='#include "post_top2_mtp_causal.h"\nextern "C" void qwen_post_mtp_select(bool);\nextern "C" void qwen_post_mtp_stats(std::uint64_t*);\n'+Path(ec[ec.index('-c')+1]).read_text()
 entry=once(entry,literal(old),literal(scope));matches=re.findall(r'qwen_next_select\([^;]+\);',entry);require(len(matches)==1,'One actual Expert selector required');entry=once(entry,matches[0],'qwen_next_select(2);qwen_post_mtp_select(arm==1);')
 if 'qwen_post_submit_select(arm==1);'in entry:entry=once(entry,'qwen_post_submit_select(arm==1);','qwen_post_submit_select(true);')
 matches=re.findall(r'qwen_app::\w+CausalEngine causal\(\*engine,model,context,ordinal>=10(?:,[^;]*)?\);',entry);require(len(matches)==1,'One actual bounded causal controller required');old_class=matches[0].split(' causal')[0]
 entry=once(entry,matches[0],'qwen_app::PostTop2MtpCausalEngine causal(*engine,model,context,ordinal>=10,arm==1);');entry=entry.replace(old_class+'&','qwen_app::PostTop2MtpCausalEngine&')
 entry=once(entry,'            const auto perf=performance_snapshot(*engine);','            std::uint64_t mtp_before[5]{};qwen_post_mtp_stats(mtp_before);\n            const auto perf=performance_snapshot(*engine);')
 entry=once(entry,'            row["phase"]=phase;','            std::uint64_t mtp_after[5]{};qwen_post_mtp_stats(mtp_after);for(unsigned j=0;j<5;++j)mtp_after[j]-=mtp_before[j];row["MTP_calls_ns_contexts_finite_rows_not_ready"]=std::vector<std::uint64_t>(mtp_after,mtp_after+5);row["MTP_target_verified_proposals"]=causal.MTP_proposals;\n            row["phase"]=phase;')
 upstream=a.cache/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569';r,jobs,sources=link(a.parent,a.out,dict(entry=(ec+['-I',str(ROOT/'native/app')],entry),engine=(en+['-I',str(upstream/'src')],engine),graph=(gr,graph)),[Path(__file__),ROOT/'native/app/post_top2_mtp_causal.h',upstream/'src/llama-ext.h'])
 update_sources(r,jobs,sources);r['GDN_model_comparison']['scope']=scope;r['next_five_comparison'].update(scope=scope,actual_sources=sources,commands=jobs);r['post_top2_MTP']=dict(scope=scope,actual_sources=sources,commands=jobs)
 seal(r,a.workspace,a.cache,a.out);write_json(a.out/'core-safety.private.json',dict(completed=True,candidate=record(a.out/'receipt.private.json'),scope=scope,PS5_operations=0,learned_host_inference=False,CI_runs=0))
if __name__=='__main__':main()
