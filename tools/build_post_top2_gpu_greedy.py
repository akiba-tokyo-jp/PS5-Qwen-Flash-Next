#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Integrate the qualified finite GPU argmax while retaining every full F32 row."""
import argparse,json,subprocess,sys
from pathlib import Path
from active_native_inputs import active_link_inputs
from build_cache_capacity_1125 import literal,recipes
from build_next_five_comparison import update_sources
from build_speculative_batch_probe import once
from expert_q4 import record,require,write_json
from multiple_shader_source import transform as multiple_assets
from qualify_post_top2_reporting import transform as reporting
from scoped_native_variant import link,seal
ROOT=Path(__file__).resolve().parents[1]

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('parent','fixture','proof','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();n=json.loads(a.parent.read_text());f=json.loads(a.fixture.read_text());proof=json.loads(a.proof.read_text())
 require(proof['completed']and proof['GPU_graphs']==110 and proof['all_integer_outputs_and_finite_status_exact']and proof['all_canaries_passed'],'Complete actual-vocabulary native finite/tie/canary proof required')
 require(f['post_top2_greedy_fixture']['scope']['workgroup_size']==256,'Qualified256-thread provider required')
 a.out.mkdir(parents=True,exist_ok=False);ec=n['compile_commands'][0];en=n['routing_sharing']['commands'][2];gc=f['io_gpu_comparison']['GPU_command'].copy()
 actual_gpu=n['io_gpu_comparison']['GPU_command'];gc[gc.index('-o')+1]=actual_gpu[actual_gpu.index('-o')+1]
 gpu=Path(gc[gc.index('-c')+1]).read_text();gpu=once(gpu,'void ggml_vk_argmax(ggml_backend_vk_context * ctx, vk_context& subctx, const ggml_tensor * src0, ggml_tensor * dst) {',
  'static std::uint64_t post_greedy_GPU_calls=0;\nextern "C" std::uint64_t qwen_post_greedy_GPU_calls(){return post_greedy_GPU_calls;}\nvoid ggml_vk_argmax(ggml_backend_vk_context * ctx, vk_context& subctx, const ggml_tensor * src0, ggml_tensor * dst) {\n    ++post_greedy_GPU_calls;')
 selected={c[c.index('-o')+1]:c for c in recipes(n)if '-c'in c and '-o'in c and c[c.index('-o')+1]in n['link_command']}
 choices=[c for c in selected.values()if 'extern "C" const void *qwen_app_prepare_shader_code('in Path(c[c.index('-c')+1]).read_text()];require(len(choices)==1,'One actual immutable registry required');ac=choices[0]
 assets=multiple_assets(Path(ac[ac.index('-c')+1]).read_text())
 engine=Path(en[en.index('-c')+1]).read_text()
 engine='namespace {bool post_gpu_greedy_enabled=false;}\nextern "C" void qwen_post_gpu_greedy_select(bool v){post_gpu_greedy_enabled=v;}\n'+engine
 engine=once(engine,'namespace qwen_app {','namespace qwen_app {\nnamespace {LlamaEngine*post_gpu_bound=nullptr;llama_sampler*post_gpu_chain=nullptr;}')
 engine=once(engine,'    qwen_app_route_phase(!inside_prefill_);', '''    if(!inside_prefill_&&post_gpu_greedy_enabled&&!post_gpu_bound){
        post_gpu_chain=llama_sampler_chain_init(llama_sampler_chain_default_params());
        if(!post_gpu_chain)throw std::runtime_error("GPU greedy chain allocation failed");
        llama_sampler_chain_add(post_gpu_chain,llama_sampler_init_greedy());
        if(!llama_set_sampler(context_,0,post_gpu_chain))throw std::runtime_error("GPU greedy backend binding failed; retain owner");
        post_gpu_bound=this;
    }
    qwen_app_route_phase(!inside_prefill_);''')
 engine=once(engine,'    llama_sampler_free(sampler_);', '''    if(post_gpu_bound==this){llama_set_sampler(context_,0,nullptr);llama_sampler_free(post_gpu_chain);post_gpu_chain=nullptr;post_gpu_bound=nullptr;}
    llama_sampler_free(sampler_);''')
 engine=once(engine,'if(!first||!second||llama_get_sampled_token_ith(context_,-1)!=LLAMA_TOKEN_NULL||',
  'if(!first||!second||(!post_gpu_greedy_enabled&&llama_get_sampled_token_ith(context_,-1)!=LLAMA_TOKEN_NULL)||')
 old_guard='if(llama_get_sampled_token_ith(context_,-1)!=LLAMA_TOKEN_NULL||llama_get_sampled_probs_ith'
 require(engine.count(old_guard)==2,'Both ordinary observation and checkpoint full-logit guards required')
 engine=engine.replace(old_guard,'if((!post_gpu_greedy_enabled&&llama_get_sampled_token_ith(context_,-1)!=LLAMA_TOKEN_NULL)||llama_get_sampled_probs_ith')
 engine=once(engine,'        }else pending_ = llama_sampler_sample(sampler_, context_, -1);', '''        }else {
            if(post_gpu_bound==this){const auto compact=llama_get_sampled_token_ith(context_,-1);if(compact<0||compact>=count)throw std::runtime_error("Finite GPU greedy token required before publication");}
            pending_=llama_sampler_sample(sampler_,context_,-1);
        }''')
 old=n['GDN_model_comparison']['scope'];scope=dict(old,schema='ps5-qwen-post-top2-GPU-greedy-v1',candidate='finite-GPU-greedy256-eager-full-evidence',candidate_id=1,
  control_Experts=2,candidate_Experts=2,full_F32_evidence_retained=True,evidence_is_still_eager=True,CPU_restored_and_width_two_reference_preserved=True,
  prefill_uses_original_CPU_sampler=True,GPU_sampler_bound_only_before_first_decode=True,additional_immutable_shaders=2)
 entry=Path(ec[ec.index('-c')+1]).read_text();entry='#include <cstdint>\nextern "C" void qwen_post_gpu_greedy_select(bool);\nextern "C" std::uint64_t qwen_post_greedy_GPU_calls();\n'+entry
 entry=once(entry,literal(old),literal(scope));entry=once(entry,'qwen_next_select(arm?2:0);','qwen_next_select(2);qwen_post_gpu_greedy_select(arm==1);')
 entry=once(entry,'arm==0?"Q4-cache3712-Top6":"Q4-cache3712-Top2";','arm==0?"CPU-greedy":"GPU-greedy256-full-F32-evidence";')
 entry=once(entry,'if(qwen_app_additional_shaders_verified()!=1)','if(qwen_app_additional_shaders_verified()!=2)')
 entry=once(entry,'            const auto perf=performance_snapshot(*engine);','            const auto post_greedy_before=qwen_post_greedy_GPU_calls();\n            const auto perf=performance_snapshot(*engine);')
 entry=once(entry,'            row["phase"]=phase;','            row["actual_GPU_argmax_calls"]=qwen_post_greedy_GPU_calls()-post_greedy_before;\n            row["phase"]=phase;')
 for before,after in [('compare&&arm==0&&rows!=io_rows[hash_arm]','compare&&rows!=io_rows[hash_arm]'),('compare&&arm==0&&(io_max_error!=0||bitwise_error)','compare&&(io_max_error!=0||bitwise_error)'),('if(compare&&arm==0&&!same_routes)','if(compare&&!same_routes)')]:entry=once(entry,before,after)
 entry=reporting(entry)
 r,jobs,sources=link(a.parent,a.out,dict(entry=(ec,entry),engine=(en,engine),gpu=(gc,gpu),assets=(ac,assets)),[Path(__file__),a.fixture,a.proof,ROOT/'tools/multiple_shader_source.py',ROOT/'tools/qualify_post_top2_reporting.py',*[Path(x['path'])for x in active_link_inputs(f)]])
 update_sources(r,jobs,sources);r['GDN_model_comparison']['scope']=scope;r['next_five_comparison'].update(scope=scope,actual_sources=sources,commands=jobs)
 for row in r['CPU_metadata_scope']['changed_sources']:
  if row['object_path']==ac[ac.index('-o')+1]:row.update(source=sources['assets'],object_path=jobs['assets'][jobs['assets'].index('-o')+1],command=jobs['assets'])
 r['io_gpu_comparison'].update(GPU_command=jobs['gpu'],GPU_source=sources['gpu']);r['post_top2_GPU_greedy']=dict(scope=scope,actual_sources=sources,commands=jobs,qualification=record(a.proof))
 seed=a.out/'linked-seed.private.json';write_json(seed,r)
 subprocess.run([sys.executable,'-X','utf8','-B',str(ROOT/'tools/rebind_gpu_provenance.py'),'--linked',str(seed),'--out',str(a.out/'GPU-provenance')],check=True)
 r=json.loads((a.out/'GPU-provenance/receipt.private.json').read_text());seal(r,a.workspace,a.cache,a.out)
 write_json(a.out/'core-safety.private.json',dict(completed=True,kind='finite_GPU_greedy_with_eager_full_F32',candidate=record(a.out/'receipt.private.json'),PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()
