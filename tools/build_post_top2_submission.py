#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Measure actual graph submissions and compare a Top2-specific flop divisor."""
import argparse,json,subprocess,sys
from pathlib import Path
from build_cache_capacity_1125 import literal
from build_next_five_comparison import update_sources
from build_speculative_batch_probe import once
from expert_q4 import record,require,write_json
from qualify_post_top2_reporting import transform as reporting
from scoped_native_variant import link,seal
ROOT=Path(__file__).resolve().parents[1]
PREFIX=r'''
#include <algorithm>
#include <atomic>
#include <chrono>
#include <cstdint>
namespace {
std::atomic<bool>post_submit_selected{false};std::uint64_t post_submit_stats[22]{};
std::uint64_t post_submit_now(){return std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now().time_since_epoch()).count();}
struct PostSubmitRecord{
 const unsigned arm;const bool synchronize;const std::uint64_t began;
 PostSubmitRecord(bool sync,unsigned nodes):arm(post_submit_selected.load(std::memory_order_relaxed)),synchronize(sync),began(post_submit_now()){
  ++post_submit_stats[(sync?20:0)+arm];if(!sync)post_submit_stats[4+arm]+=nodes;
 }
 ~PostSubmitRecord(){post_submit_stats[(synchronize?18:2)+arm]+=post_submit_now()-began;}
};
}
extern "C" void qwen_post_submit_select(bool v){post_submit_selected.store(v,std::memory_order_relaxed);}
extern "C" void qwen_post_submit_stats(std::uint64_t*out){std::copy_n(post_submit_stats,22,out);}
'''
def gpu_source(text,divisor,node_cap=None,control_node_cap=1):
    text=once(text,'static ggml_status ggml_backend_vk_graph_compute(ggml_backend_t backend, ggml_cgraph * cgraph) {',
        'static ggml_status ggml_backend_vk_graph_compute(ggml_backend_t backend, ggml_cgraph * cgraph) {\n    PostSubmitRecord post_record(false,unsigned(cgraph->n_nodes));')
    text=once(text,'static void ggml_backend_vk_synchronize(ggml_backend_t backend) {',
        'static void ggml_backend_vk_synchronize(ggml_backend_t backend) {\n    PostSubmitRecord post_record(true,0);')
    if node_cap:
        anchor='    ggml_backend_vk_context * ctx = (ggml_backend_vk_context *)backend->context;'
        start=text.index('static ggml_status ggml_backend_vk_graph_compute(');at=text.index(anchor,start)
        code='''
    struct PostScopedNodeCap {
        uint32_t&current;const uint32_t saved;
        PostScopedNodeCap(uint32_t&v):current(v),saved(v){
            GGML_ASSERT(saved==1);current=post_submit_selected.load(std::memory_order_relaxed)?NODE_CAP:CONTROL_NODE_CAP;
        }
        ~PostScopedNodeCap(){current=saved;}
    } post_scoped_node_cap(ctx->device->max_nodes_per_submit);
'''.replace('CONTROL_NODE_CAP',str(control_node_cap)).replace('NODE_CAP',str(node_cap))
        text=text[:at]+text[at:].replace(anchor,anchor+code,1)
    text=once(text,'ctx->last_total_flops / 40u','ctx->last_total_flops / (post_submit_selected.load(std::memory_order_relaxed)?'+str(divisor)+'u:40u)')
    text=once(text,'    auto const submit_after = [&](int start, int end) {',
        '''    auto const submit_after = [&](int start, int end) {
        const unsigned post_arm=post_submit_selected.load(std::memory_order_relaxed);
        ++post_submit_stats[10+post_arm];post_submit_stats[14+post_arm]+=batch_flops;
        post_submit_stats[12+post_arm]=std::max(post_submit_stats[12+post_arm],std::uint64_t(end-start+1));
        post_submit_stats[16+post_arm]=std::max(post_submit_stats[16+post_arm],batch_flops);''')
    text=once(text,'if (flops_per_submit != 0 && submitted_nodes > 0 && batch_flops + node_flops >= flops_per_submit) {',
        'if (flops_per_submit != 0 && submitted_nodes > 0 && batch_flops + node_flops >= flops_per_submit) {\n                ++post_submit_stats[6+unsigned(post_submit_selected.load(std::memory_order_relaxed))];')
    text=once(text,'        if (submit && enqueued) {',
        '''        if (submit && enqueued) {
            const unsigned post_arm=post_submit_selected.load(std::memory_order_relaxed);
            if(submitted_nodes>=ctx->device->max_nodes_per_submit)++post_submit_stats[8+post_arm];
            if(flops_per_submit!=0&&batch_flops>=flops_per_submit)++post_submit_stats[6+post_arm];''')
    return PREFIX+text

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('parent','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--divisor',type=int,choices=(40,10,1),default=10)
    p.add_argument('--node-cap',type=int,choices=(4,16,256));p.add_argument('--control-node-cap',type=int,choices=(1,16,256),default=1);a=p.parse_args()
    require(a.node_cap is not None or a.control_node_cap==1,'A nondefault control requires an explicit candidate cap')
    n=json.loads(a.parent.read_text());old=n['GDN_model_comparison']['scope']
    require(old['candidate']=='Q4-cache3712-Top2'and n['lossless_shader_storage']['vulkan_object']['sha256']=='17cb982ec26903fcee469639592d5acd761acd6f883bc35135b9d665fc4b6ad2','Actual Top2/original GPU parent required')
    a.out.mkdir(parents=True,exist_ok=False)
    scope=dict(old,schema='ps5-qwen-post-top2-submission-v1',candidate='flop-divisor-'+str(a.divisor),candidate_id=1,
        control_Experts=2,candidate_Experts=2,control_flop_divisor=40,candidate_flop_divisor=a.divisor,
        original_driver_flop_cap_and_node_cap_preserved=True,original_fence_and_positive_completion_preserved=True,
        shader_math_unchanged=True,additional_GPU_timestamp_queries=False)
    if a.node_cap:scope.update(candidate='actual-node-cap'+str(a.control_node_cap)+'-to'+str(a.node_cap),control_node_cap=a.control_node_cap,candidate_node_cap=a.node_cap,
        original_driver_flop_cap_and_node_cap_preserved=False,original_driver_flop_cap_preserved=True,
        software_node_cap_temporarily_overridden_in_explicit_graph_scope=True,original_device_node_cap_restored_after_graph=True,
        initial_environment_node_cap_preserved=1,additional_GPU_memory_bytes=0)
    ec=n['compile_commands'][0];gc=n['io_gpu_comparison']['GPU_command'];entry=Path(ec[ec.index('-c')+1]).read_text()
    entry='#include <cstdint>\nextern "C" void qwen_post_submit_select(bool);\nextern "C" void qwen_post_submit_stats(std::uint64_t*);\n'+entry
    entry=once(entry,literal(old),literal(scope));entry=once(entry,'qwen_next_select(arm?2:0);','qwen_next_select(2);qwen_post_submit_select(arm==1);')
    entry=once(entry,'arm==0?"Q4-cache3712-Top6":"Q4-cache3712-Top2";',
        'arm==0?"Top2-flop-divisor40":"Top2-flop-divisor'+str(a.divisor)+'";')
    entry=once(entry,'            const auto perf=performance_snapshot(*engine);',
        '            std::uint64_t post_submit_before[22]{};qwen_post_submit_stats(post_submit_before);\n            const auto perf=performance_snapshot(*engine);')
    entry=once(entry,'            row["phase"]=phase;',
        '            std::uint64_t post_submit_after[22]{};qwen_post_submit_stats(post_submit_after);Json submission_delta=Json::array();for(unsigned i=0;i<22;++i)submission_delta.push_back(i==12||i==13||i==16||i==17?Json(nullptr):Json(post_submit_after[i]-post_submit_before[i]));row["submission_counters_delta"]=submission_delta;row["submission_counters_after"]=std::vector<std::uint64_t>(post_submit_after,post_submit_after+22);row["submission_flop_divisor"]=arm?'+str(a.divisor)+':40;\n            row["phase"]=phase;')
    if a.node_cap:entry=once(entry,'            row["phase"]=phase;','            row["actual_submission_node_cap"]=arm?'+str(a.node_cap)+':'+str(a.control_node_cap)+';\n            row["phase"]=phase;')
    for before,after in [('compare&&arm==0&&rows!=io_rows[hash_arm]','compare&&rows!=io_rows[hash_arm]'),
        ('compare&&arm==0&&(io_max_error!=0||bitwise_error)','compare&&(io_max_error!=0||bitwise_error)'),
        ('else if(arm==0&&(result.token_ids!=speed_ids[hash_arm][task]||result.output_bytes!=speed_bytes[hash_arm][task]))','else if(result.token_ids!=speed_ids[hash_arm][task]||result.output_bytes!=speed_bytes[hash_arm][task])'),
        ('if(compare&&arm==0&&!same_routes)','if(compare&&!same_routes)')]:entry=once(entry,before,after)
    entry=reporting(entry)
    gp=Path(gc[gc.index('-c')+1]);gpu=gpu_source(gp.read_text(),a.divisor,a.node_cap,a.control_node_cap)
    r,jobs,sources=link(a.parent,a.out,dict(entry=(ec,entry),gpu=(gc,gpu)),[Path(__file__),ROOT/'tools/qualify_post_top2_reporting.py'])
    update_sources(r,jobs,sources);r['io_gpu_comparison'].update(GPU_command=jobs['gpu'],GPU_source=sources['gpu'])
    r['GDN_model_comparison']['scope']=scope;r['next_five_comparison'].update(scope=scope,actual_sources=sources,commands=jobs,production_adopted=False)
    r['post_top2_submission']=dict(scope=scope,actual_sources=sources,commands=jobs,
        additive_counter_pairs=['graph_calls','graph_record_host_ns','graph_nodes','flop_boundary_events','node_boundary_events','submission_batches',
            'maximum_nodes_nonadditive','estimated_submitted_node_flops','maximum_estimated_flops_nonadditive','synchronize_host_ns','synchronize_calls'])
    seed=a.out/'linked-seed.private.json';write_json(seed,r)
    subprocess.run([sys.executable,'-X','utf8','-B',str(ROOT/'tools/rebind_gpu_provenance.py'),'--linked',str(seed),'--out',str(a.out/'GPU-provenance')],check=True)
    r=json.loads((a.out/'GPU-provenance/receipt.private.json').read_text());seal(r,a.workspace,a.cache,a.out)
    write_json(a.out/'core-safety.private.json',dict(completed=True,kind='Top2_submission_policy_comparison',scope=scope,
        candidate=record(a.out/'receipt.private.json'),original_shader_driver_flop_cap_and_completion_preserved=True,
        original_node_cap_preserved=a.node_cap is None,explicit_candidate_node_cap=a.node_cap,PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()
