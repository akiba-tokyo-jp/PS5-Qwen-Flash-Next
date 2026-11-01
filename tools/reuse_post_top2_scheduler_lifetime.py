#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Retire synchronized obsolete scheduler metadata before replacement allocation."""
import argparse,json
from pathlib import Path
from build_cache_capacity_1125 import literal
from build_next_five_comparison import update_sources
from build_speculative_batch_probe import once
from expert_q4 import record,write_json
from scoped_native_variant import link,seal
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in('parent','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();n=json.loads(a.parent.read_text());a.out.mkdir(parents=True,exist_ok=False);cc=n['post_top2_compact_sampler_outputs']['commands']['context'];ctx=Path(cc[cc.index('-c')+1]).read_text()
 ctx='''#include <algorithm>
#include <ps5platform/heap.h>
#include <cstdint>
namespace {std::uint64_t post_scheduler_lifetime[7]{};}
extern "C" void qwen_post_scheduler_lifetime_stats(std::uint64_t*out){std::copy_n(post_scheduler_lifetime,7,out);}
'''+ctx
 ctx=once(ctx,'void llama_context::sched_new(size_t max_nodes, bool parallel) {','''void llama_context::sched_new(size_t max_nodes, bool parallel) {
    // sched_reserve synchronizes before rebuilding; its obsolete scheduler
    // must not overlap the replacement's large CPU graph scratch allocation.
    if(sched){struct ps5_heap_stats before{},after{};ps5_heap_stats(&before);sched.reset();ps5_heap_stats(&after);
        ++post_scheduler_lifetime[0];post_scheduler_lifetime[1]=max_nodes;post_scheduler_lifetime[2]=before.mapped_bytes;post_scheduler_lifetime[3]=after.mapped_bytes;}
''')
 ctx=once(ctx,'    ggml_backend_sched_set_copy_callback(sched.get(), sched_copy_experts, this);','''    {struct ps5_heap_stats observed{};ps5_heap_stats(&observed);post_scheduler_lifetime[4]=observed.mapped_bytes;post_scheduler_lifetime[5]=observed.peak_bytes;}
    ggml_backend_sched_set_copy_callback(sched.get(), sched_copy_experts, this);''')
 ctx=once(ctx,'    gf_res_reserve.reset(new llm_graph_result(max_nodes));\n    gf_res_prev_active = nullptr;','''    gf_res_prev_active = nullptr;
    if(gf_res_reserve){gf_res_reserve.reset();++post_scheduler_lifetime[6];}
    gf_res_reserve.reset(new llm_graph_result(max_nodes));''')
 old=n['GDN_model_comparison']['scope'];scope=dict(old,obsolete_synchronized_scheduler_released_before_replacement=True,obsolete_reserve_graph_released_before_replacement=True,all_CPU_GPU_OS_caps_unchanged=True)
 ec=n['compile_commands'][0];entry='#include <cstdint>\nextern "C" void qwen_post_scheduler_lifetime_stats(std::uint64_t*);\n'+Path(ec[ec.index('-c')+1]).read_text();entry=once(entry,literal(old),literal(scope))
 entry=once(entry,'            row["phase"]=phase;','            std::uint64_t lifetime[7]{};qwen_post_scheduler_lifetime_stats(lifetime);row["scheduler_lifetime_rebuilds_nodes_before_after_new_peak_graphs"]=std::vector<std::uint64_t>(lifetime,lifetime+7);\n            row["phase"]=phase;')
 r,jobs,sources=link(a.parent,a.out,dict(entry=(ec,entry),context=(cc,ctx)),[Path(__file__)])
 update_sources(r,jobs,sources);r['post_top2_compact_sampler_outputs']['actual_sources']['context']=sources['context'];r['post_top2_compact_sampler_outputs']['commands']['context']=jobs['context'];r['GDN_model_comparison']['scope']=scope;r['next_five_comparison'].update(scope=scope,actual_sources=sources,commands=jobs)
 r['post_top2_C4_scheduler_lifetime']=dict(scope=scope,actual_sources=sources,commands=jobs,measured_prior_mapped_bytes=503382016,measured_prior_peak_bytes=671219712,CPU_heap_limit_bytes=536870912)
 seal(r,a.workspace,a.cache,a.out);write_json(a.out/'core-safety.private.json',dict(completed=True,candidate=record(a.out/'receipt.private.json'),GPU_completion_dependencies_and_math_unchanged=True,CPU_quota_not_increased=True,PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()
