#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Avoid unused probability/candidate arrays for the isolated greedy-only chain."""
import argparse,json
from pathlib import Path
from build_cache_capacity_1125 import literal,recipes
from build_next_five_comparison import update_sources
from build_speculative_batch_probe import once
from expert_q4 import record,require,write_json
from scoped_native_variant import link,seal
from qualify_post_top2_compact_reorder import transform as qualify_reorder

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in('parent','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();n=json.loads(a.parent.read_text());a.out.mkdir(parents=True,exist_ok=False)
 selected={c[c.index('-o')+1]:c for c in recipes(n)if '-c'in c and '-o'in c and c[c.index('-o')+1]in n['link_command']}
 found=[c for c in selected.values()if 'uint32_t llama_context::output_reserve(int32_t n_outputs)'in Path(c[c.index('-c')+1]).read_text()]
 require(len(found)==1,'One actual linked context/pooled-checkpoint provider required');cc=found[0];ctx=Path(cc[cc.index('-c')+1]).read_text()
 prefix='''#include <algorithm>
#include <cstdint>
extern "C" bool qwen_post_compact_greedy_outputs();
namespace {std::uint64_t post_compact_reserves=0,post_compact_saved_max=0;}
extern "C" void qwen_post_compact_output_stats(std::uint64_t*out){out[0]=post_compact_reserves;out[1]=post_compact_saved_max;}
'''
 ctx=prefix+ctx;ctx=once(ctx,'    const bool has_sampling = !sampling.samplers.empty();',
  '    const bool has_sampling = !sampling.samplers.empty();\n    const bool post_compact=has_sampling&&qwen_post_compact_greedy_outputs();\n    if(post_compact){++post_compact_reserves;post_compact_saved_max=std::max(post_compact_saved_max,std::uint64_t(2*n_vocab*n_outputs_max*sizeof(float)));}')
 ctx=once(ctx,'backend_float_count = 2 * n_vocab * n_outputs_max;', 'backend_float_count = (post_compact?1:2) * n_vocab * n_outputs_max;')
 ctx=once(ctx,'backend_token_count = (1 + n_vocab) * n_outputs_max;', 'backend_token_count = (1 + (post_compact?0:n_vocab)) * n_outputs_max;')
 ctx=once(ctx,'sampling.probs = {(float *) (base + offset), (size_t)(n_vocab*n_outputs_max)};',
  'sampling.probs = post_compact?buffer_view<float>{nullptr,0}:buffer_view<float>{(float *) (base + offset), (size_t)(n_vocab*n_outputs_max)};')
 ctx=once(ctx,'sampling.candidates = {(llama_token *) (base + offset), (size_t)(n_vocab*n_outputs_max)};',
  'sampling.candidates = post_compact?buffer_view<llama_token>{nullptr,0}:buffer_view<llama_token>{(llama_token *) (base + offset), (size_t)(n_vocab*n_outputs_max)};')
 # Fail explicitly if a future sampler requests an omitted surface. The
 # greedy-only graph retains full logits and emits neither other surface.
 marker='    if (!dst.has_data()) {\n        return;\n    }\n\n    for (size_t i = 0; i < tensors.size(); ++i) {'
 ctx=once(ctx,marker,'    if (!dst.has_data()) {\n        for(auto*t:tensors)if(t)throw std::runtime_error("A compact greedy graph requested an omitted output surface");\n        return;\n    }\n\n    for (size_t i = 0; i < tensors.size(); ++i) {')
 en=n['routing_sharing']['commands'][2];engine=Path(en[en.index('-c')+1]).read_text()
 require('namespace {bool post_gpu_greedy_enabled=false;}'in engine,'Exact isolated greedy-only engine required')
 engine+='\nextern "C" bool qwen_post_compact_greedy_outputs(){return post_gpu_greedy_enabled;}\n'
 old=n['GDN_model_comparison']['scope'];scope=dict(old,unused_backend_probs_and_candidates_not_allocated_for_isolated_greedy=True,
  all_raw_and_sampled_F32_logits_preserved=True,existing_CPU_heap_cap_bytes=512<<20,CPU_heap_cap_not_raised=True,omitted_surface_requests_fail_explicitly=True)
 ec=n['compile_commands'][0];entry=Path(ec[ec.index('-c')+1]).read_text();entry='#include <cstdint>\nextern "C" void qwen_post_compact_output_stats(std::uint64_t*);\n'+entry
 entry=once(entry,literal(old),literal(scope));entry=once(entry,'            row["phase"]=phase;',
  '            std::uint64_t compact[2]{};qwen_post_compact_output_stats(compact);row["compact_output_reserves_and_maximum_bytes_saved"]=std::vector<std::uint64_t>(compact,compact+2);\n            row["phase"]=phase;')
 ctx=qualify_reorder(ctx)
 r,jobs,sources=link(a.parent,a.out,dict(entry=(ec,entry),engine=(en,engine),context=(cc,ctx)),[Path(__file__),Path(__file__).with_name('qualify_post_top2_compact_reorder.py')])
 update_sources(r,jobs,sources);r['GDN_model_comparison']['scope']=scope;r['next_five_comparison'].update(scope=scope,actual_sources=sources,commands=jobs)
 r['post_top2_compact_sampler_outputs']=dict(scope=scope,actual_sources=sources,commands=jobs,prior38900_CPU_guard_refusal_preserved=True,
  actual_model_context_checkpoint_pool_replaced=True)
 seal(r,a.workspace,a.cache,a.out);write_json(a.out/'core-safety.private.json',dict(completed=True,kind='remove_unused_greedy_output_surfaces',candidate=record(a.out/'receipt.private.json'),
  all_F32_and_checkpoint_checks_preserved=True,CPU_GPU_OS_caps_unchanged=True,no_extra_GPU_payloads=True,PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()
