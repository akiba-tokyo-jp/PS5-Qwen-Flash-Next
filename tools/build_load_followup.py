#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compare only serialized tail splitting on current outputQ4/node256, with nested CPU spans."""
import argparse,copy,json,re,subprocess,sys
from pathlib import Path
from active_native_inputs import active_link_inputs
from build_cache_capacity_1125 import literal,recipes
from build_next_five_comparison import update_sources
from build_speculative_batch_probe import once
from expert_q4 import record,require,write_json
from scoped_native_variant import link,seal
ROOT=Path(__file__).resolve().parents[1]
GPU_PREFIX=r'''
namespace {bool load_tail_selected=false;std::uint64_t load_gpu[16]{};
struct LoadGpuSpan {unsigned slot;std::uint64_t began;explicit LoadGpuSpan(unsigned s):slot(s+8*unsigned(load_tail_selected)),began(post_submit_now()){++load_gpu[slot];}~LoadGpuSpan(){load_gpu[slot+1]+=post_submit_now()-began;}};}
extern "C" void qwen_load_tail_select(bool v){load_tail_selected=v;}
extern "C" void qwen_load_gpu_stats(std::uint64_t*out){std::copy_n(load_gpu,16,out);}
'''
def engine_source(s):
 s='#include "load_followup_timing.h"\n'+s
 s=once(s,'        if(begin)begin();','        qwen_load::CpuSpan timing(qwen_load::epoch_begin);if(begin)begin();')
 s=once(s,'void complete() {if(complete_)complete_();completed_=true;}','void complete() {qwen_load::CpuSpan timing(qwen_load::epoch_complete);if(complete_)complete_();completed_=true;}')
 s=once(s,'        ProfileScope timing(timing_.process_ns);','        qwen_load::CpuSpan load_process(qwen_load::model_process);ProfileScope timing(timing_.process_ns);')
 s=once(s,'if(gpu_checkpoint_) { ProfileScope timing(timing_.checkpoint_ns); gpu_checkpoint_(); }','if(gpu_checkpoint_) { qwen_load::CpuSpan load_checkpoint(qwen_load::checkpoint);ProfileScope timing(timing_.checkpoint_ns); gpu_checkpoint_(); }')
 s=once(s,'else pending_ = llama_sampler_sample(sampler_, context_, -1);','else {qwen_load::CpuSpan sampling(qwen_load::sampler);pending_ = llama_sampler_sample(sampler_, context_, -1);}')
 s=once(s,'        if(restored_logits_active_) {','        if(restored_logits_active_) {qwen_load::CpuSpan sampling(qwen_load::sampler);')
 # Time logit access/guards without changing the public engine layout.
 for signature,category in [('const float * LlamaEngine::effective_logits() const {','logit_access'),('void LlamaEngine::guard() {','work_guard')]:
  if signature in s:s=once(s,signature,signature+'qwen_load::CpuSpan timing(qwen_load::'+category+');')
 return s
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in('parent','normal','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();n=json.loads(a.parent.read_text());normal=json.loads(a.normal.read_text());require(n['post_top2_output_Q4']['scope']['output_weight_type']=='Q4_0'and normal['post_top2_normal']['scope']['submission_node_cap']==256,'Actual current outputQ4/node256 parents required');a.out.mkdir(parents=True,exist_ok=False)
 seed=copy.deepcopy(n);oldgpu=n['lossless_shader_storage']['vulkan_object'];newgpu=normal['lossless_shader_storage']['vulkan_object'];seed['link_command']=[newgpu['path']if x==oldgpu['path']else x for x in seed['link_command']]
 for key in('lossless_shader_storage','shader_resource_manifest','io_gpu_comparison'):seed[key]=copy.deepcopy(normal[key])
 selected={c[c.index('-o')+1]:c for c in recipes(n)if'-c'in c and'-o'in c and c[c.index('-o')+1]in n['link_command']}
 # Reuse the qualified current context and memory objects, not old overlap or padding policies.
 for role,needle in [('context','void llama_context::sched_new(size_t max_nodes, bool parallel)'),('memory','return limit_probe.required(free,minimum,reserved,legacy)-minimum;')]:
  matches=[c for c in selected.values()if needle in Path(c[c.index('-c')+1]).read_text()];require(len(matches)==1,'One current comparison '+role+' provider required');old=matches[0];new=normal['post_top2_normal']['commands'][role];seed['link_command']=[new[new.index('-o')+1]if x==old[old.index('-o')+1]else x for x in seed['link_command']]
  for row in seed['CPU_metadata_scope']['changed_sources']:
   if row['object_path']==old[old.index('-o')+1]:row.update(source=normal['post_top2_normal']['actual_sources'][role],object_path=new[new.index('-o')+1],command=new)
 merged={r['path']:r for r in seed['inputs_before']};merged.update({r['path']:r for r in active_link_inputs(normal)});seed['inputs_before']=list(merged.values())
 gc=normal['io_gpu_comparison']['GPU_command'];gpu=Path(gc[gc.index('-c')+1]).read_text();anchor='extern "C" void qwen_post_submit_stats(std::uint64_t*out){std::copy_n(post_submit_stats,22,out);}'
 gpu=once(gpu,anchor,anchor+GPU_PREFIX);gpu=once(gpu,'post_submit_selected.load(std::memory_order_relaxed)?256:16','256')
 gpu=once(gpu,'(almost_ready && !ctx->almost_ready_fence_pending);','((!load_tail_selected||!ctx->device->serialize_submissions)&&almost_ready && !ctx->almost_ready_fence_pending);')
 gpu=once(gpu,'                auto res = ctx->device->device.waitForFences({ ctx->fence }, true, UINT64_MAX);','                LoadGpuSpan measured_fence(2);auto res = ctx->device->device.waitForFences({ ctx->fence }, true, UINT64_MAX);')
 require(gpu.count('        queue.submit(submits, fence);')==2,'Both actual queue APIs must be counted');gpu=gpu.replace('        queue.submit(submits, fence);','        LoadGpuSpan measured_queue(0);queue.submit(submits, fence);')
 ec=n['compile_commands'][0];entry=Path(ec[ec.index('-c')+1]).read_text();old=n['GDN_model_comparison']['scope'];scope=dict(old,schema='ps5-qwen-load-followup-v1',candidate='serialized-almost-ready-tail-only',both_arms_node_cap=256,both_arms_flop_divisor=40,both_arms_attempt_cap=6,output_weight_type='Q4_0',all_F32_routes_tokens_exact=True,nested_CPU_spans_in_both_arms=True,actual_queue_and_serialized_wait_spans=True,serialized_fences_and_dependencies_preserved=True)
 entry=once(entry,literal(old),literal(scope));entry='''#include "load_followup_timing.h"
#include "native_failure_journal.h"
extern "C" void qwen_load_tail_select(bool);
extern "C" void qwen_load_gpu_stats(std::uint64_t*);
extern "C" void qwen_post_submit_select(bool);
extern "C" void qwen_post_submit_stats(std::uint64_t*);
extern "C" void qwen_post_loading_reserve_select(bool);
extern "C" void qwen_post_loading_reserve_stats(std::uint64_t*);
'''+entry
 entry=once(entry,'        const auto policy = Json::parse(policy_file);','        qwen_app::install_native_assertion_journal();\n        const auto policy = Json::parse(policy_file);')
 loading=normal['post_top2_loading_reserved']['scope'];entry=once(entry,'        qwen_limit_probe_stage(1);','        if(policy.at("native_post_top2_loading_reserved")!=Json::parse('+literal(loading)+'))throw std::runtime_error("Exact current loading206 scope required");qwen_limit_probe_stage(1);qwen_post_loading_reserve_select(true);');entry=once(entry,'        qwen_limit_probe_stage(2);','        qwen_post_loading_reserve_select(false);qwen_limit_probe_stage(2);')
 entry=once(entry,'qwen_next_select(2);','qwen_next_select(2);qwen_load_tail_select(arm==1);qwen_post_submit_select(arm==1);qwen_load::enabled=true;')
 entry=once(entry,'static void observed_inference_stage(const char *phase) {','static void observed_inference_stage(const char *phase) {qwen_load::CpuSpan measured(qwen_load::stage);')
 entry=once(entry,'engine->set_logits_observer([&](const float*v,std::size_t count)noexcept{','engine->set_logits_observer([&](const float*v,std::size_t count)noexcept{qwen_load::CpuSpan measured(qwen_load::full_validation);')
 entry=once(entry,'                    publish(event);','                    {qwen_load::CpuSpan measured(qwen_load::publication);publish(event);}')
 marker='            const auto perf=performance_snapshot(*engine);';entry=once(entry,marker,'            const auto cpu_before=qwen_load::snapshot();std::uint64_t gpu_before[16]{},submission_before[22]{};qwen_load_gpu_stats(gpu_before);qwen_post_submit_stats(submission_before);\n'+marker)
 for before,after in [('compare&&arm==0&&rows!=io_rows[hash_arm]','compare&&rows!=io_rows[hash_arm]'),('compare&&arm==0&&(io_max_error!=0||bitwise_error)','compare&&(io_max_error!=0||bitwise_error)'),('else if(arm==0&&(result.token_ids!=speed_ids[hash_arm][task]||result.output_bytes!=speed_bytes[hash_arm][task]))','else if(result.token_ids!=speed_ids[hash_arm][task]||result.output_bytes!=speed_bytes[hash_arm][task])'),('if(compare&&arm==0&&!same_routes)','if(compare&&!same_routes)')]:
  if before in entry:entry=once(entry,before,after)
 marker='            row["phase"]=phase;';entry=once(entry,marker,'''            const auto cpu_after=qwen_load::snapshot();Json cpu_delta=Json::array();for(unsigned i=0;i<cpu_after.size();++i)cpu_delta.push_back(cpu_after[i]-cpu_before[i]);
            std::uint64_t gpu_after[16]{},submission_after[22]{};qwen_load_gpu_stats(gpu_after);qwen_post_submit_stats(submission_after);Json gpu_delta=Json::array(),submission_delta=Json::array();for(unsigned i=0;i<16;++i)gpu_delta.push_back(gpu_after[i]-gpu_before[i]);for(unsigned i=0;i<22;++i)submission_delta.push_back(i==12||i==13||i==16||i==17?Json(nullptr):Json(submission_after[i]-submission_before[i]));
            row["CPU_nested_calls_inclusive_exclusive_ns"]=cpu_delta;row["actual_queue_and_serial_wait_delta"]=gpu_delta;row["submission_counters_delta"]=submission_delta;row["submission_counters_after"]=std::vector<std::uint64_t>(submission_after,submission_after+22);row["actual_submission_node_cap"]=256;row["serialized_tail_disabled"]=arm==1;
'''+marker)
 enginecmd=n['routing_sharing']['commands'][2];seedpath=a.out/'comparison-seed.private.json';write_json(seedpath,seed)
 r,jobs,sources=link(seedpath,a.out,dict(entry=(ec+['-I',str(ROOT/'native/app')],entry),engine=(enginecmd+['-I',str(ROOT/'native/app')],engine_source(Path(enginecmd[enginecmd.index('-c')+1]).read_text())),gpu=(gc,gpu)),[Path(__file__),a.parent,a.normal,ROOT/'native/app/load_followup_timing.h',ROOT/'native/app/native_failure_journal.h'])
 update_sources(r,jobs,sources);r['GDN_model_comparison']['scope']=scope;r['next_five_comparison'].update(scope=scope,actual_sources=sources,commands=jobs);r['io_gpu_comparison'].update(GPU_source=sources['gpu'],GPU_command=jobs['gpu']);r['post_top2_loading_reserved']=copy.deepcopy(normal['post_top2_loading_reserved']);r['load_followup']=dict(scope=scope,actual_sources=sources,commands=jobs,normal_control=record(a.normal),CPU_categories=['epoch_begin','epoch_complete','checkpoint','stage','logit_access','sampler','finite_scan','full_validation','token_render','token_persistence','publication','model_process','work_guard','request_run'])
 unsealed=a.out/'linked-seed.private.json';write_json(unsealed,r);subprocess.run([sys.executable,'-X','utf8','-B',str(ROOT/'tools/rebind_gpu_provenance.py'),'--linked',str(unsealed),'--out',str(a.out/'GPU-provenance')],check=True);r=json.loads((a.out/'GPU-provenance/receipt.private.json').read_text());seal(r,a.workspace,a.cache,a.out)
 write_json(a.out/'core-safety.private.json',dict(completed=True,original_fences_and_math_preserved=True,only_tail_predicate_changes_in_candidate=True,CPU_timers_are_nested_wall_not_CPU_cycles=True,PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()
