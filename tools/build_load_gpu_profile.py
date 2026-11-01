#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Measure bounded operator timestamp ranges without changing graph batching or adding waits."""
import argparse,json,subprocess,sys
from pathlib import Path
from build_cache_capacity_1125 import literal
from build_next_five_comparison import update_sources
from build_speculative_batch_probe import once
from expert_q4 import record,require,write_json
from scoped_native_variant import link,seal
ROOT=Path(__file__).resolve().parents[1]
GROUPS=['Expert_Q2_matmul_with_unpack','other_Q4_matmul','other_Q8_matmul','router_F32','HC_Q8','shared_Expert_Q8','output_Q4','GDN_SSM_ranges','other_matrix']
PROBE=r'''
namespace {
bool load_query_enabled=false;
struct LoadQueryState {ggml_backend_vk_context*owner;vk::QueryPool pool;unsigned intervals=0,bits;double period;
 std::array<unsigned,4096>groups{};std::array<std::uint64_t,8192>results{};};
std::unique_ptr<LoadQueryState>load_query;
std::uint64_t load_query_stats[26]{};
int load_query_begin(ggml_backend_vk_context*ctx,vk_context compute,const ggml_tensor*n){
 if(!load_query_enabled)return -1;const auto*w=n->src[0];const char*name=n->name,*weight=w?w->name:"";
 const bool matrix=n->op==GGML_OP_MUL_MAT||n->op==GGML_OP_MUL_MAT_ID;
 const bool ssm=n->op==GGML_OP_GATED_DELTA_NET||n->op==GGML_OP_SSM_SCAN||n->op==GGML_OP_SSM_CONV;
 if(!matrix&&!ssm)return -1;
 if(!load_query){const auto families=ctx->device->physical_device.getQueueFamilyProperties();const auto family=ctx->device->compute_queue->queue_family_index;
  if(family>=families.size()||!families[family].timestampValidBits||families[family].timestampValidBits>64||!std::isfinite(ctx->device->properties.limits.timestampPeriod)||ctx->device->properties.limits.timestampPeriod<=0)throw std::runtime_error("Selected physical queue lacks valid timestamps");
  load_query=std::make_unique<LoadQueryState>();load_query->owner=ctx;load_query->bits=families[family].timestampValidBits;load_query->period=ctx->device->properties.limits.timestampPeriod;
  vk::QueryPoolCreateInfo ci;ci.queryType=vk::QueryType::eTimestamp;ci.queryCount=8192;load_query->pool=ctx->device->device.createQueryPool(ci);++load_query_stats[18];load_query_stats[22]=load_query->bits;load_query_stats[23]=std::uint64_t(load_query->period*1000.0);}
 if(load_query->owner!=ctx||load_query->intervals>=4096)throw std::runtime_error("One bounded query owner and4096 ranges per completed model call required");
 unsigned group=8;if(ssm)group=7;else if(std::strstr(weight,"ffn_gate_inp"))group=3;else if(std::strstr(weight,"output.weight")||std::strstr(name,"result_output"))group=6;
 else if(w&&(w->type==GGML_TYPE_Q2_0||w->type==GGML_TYPE_Q2_K))group=0;else if(std::strstr(weight,"hc_"))group=4;else if(std::strstr(weight,"shexp"))group=5;else if(w&&w->type==GGML_TYPE_Q4_0)group=1;else if(w&&w->type==GGML_TYPE_Q8_0)group=2;
 const unsigned i=load_query->intervals++;load_query->groups[i]=group;const auto slot=i*2;
 compute->s->buffer->buf.resetQueryPool(load_query->pool,slot,2);compute->s->buffer->buf.writeTimestamp(vk::PipelineStageFlagBits::eAllCommands,load_query->pool,slot);load_query_stats[24]=load_query->intervals;return int(slot);
}
void load_query_end(vk_context compute,int slot){if(slot>=0)compute->s->buffer->buf.writeTimestamp(vk::PipelineStageFlagBits::eAllCommands,load_query->pool,unsigned(slot)+1);}
void load_query_release(ggml_backend_vk_context*ctx){if(!load_query||load_query->owner!=ctx)return;if(load_query->intervals)throw std::runtime_error("Completed query drain required before owner teardown");ctx->device->device.destroyQueryPool(load_query->pool);load_query.reset();++load_query_stats[19];}
}
extern "C" void qwen_load_gpu_probe_select(bool v){if(load_query&&load_query->intervals)throw std::runtime_error("Cannot switch a pending query scope");load_query_enabled=v;}
extern "C" void qwen_load_gpu_probe_stats(std::uint64_t*out){std::copy_n(load_query_stats,26,out);}
// Called only after the existing positive device-completion checkpoint. No WAIT,
// extra fence, queue submission or polling is introduced by result retrieval.
extern "C" void qwen_load_gpu_probe_drain(){if(!load_query||!load_query->intervals)return;auto&q=*load_query;const auto count=q.intervals*2;
 const auto status=q.owner->device->device.getQueryPoolResults(q.pool,0,count,count*sizeof(std::uint64_t),q.results.data(),sizeof(std::uint64_t),vk::QueryResultFlagBits::e64);
 if(status!=vk::Result::eSuccess)throw std::runtime_error("Query results unavailable after positive device completion");const auto mask=q.bits==64?UINT64_MAX:(std::uint64_t(1)<<q.bits)-1;
 for(unsigned i=0;i<q.intervals;++i){const auto ns=std::uint64_t(double((q.results[i*2+1]-q.results[i*2])&mask)*q.period);if(ns>60000000000ull)throw std::runtime_error("Timestamp range exceeds60 seconds");load_query_stats[q.groups[i]*2]+=ns;++load_query_stats[q.groups[i]*2+1];}
 ++load_query_stats[20];load_query_stats[21]+=q.intervals;q.intervals=0;load_query_stats[24]=0;
}
'''
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in('parent','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 p.add_argument('--tail-disabled',type=int,choices=(0,1),required=True);a=p.parse_args();n=json.loads(a.parent.read_text());a.out.mkdir(parents=True,exist_ok=False)
 gc=n['load_followup']['commands']['gpu'];gpu=Path(gc[gc.index('-c')+1]).read_text();anchor='bool ggml_vk_build_graph(ggml_backend_vk_context * ctx, ggml_cgraph * cgraph, int node_idx, ggml_tensor *node_begin, int node_idx_begin, bool last_node, bool almost_ready, bool submit){';gpu=once(gpu,anchor,PROBE+'\n'+anchor)
 gpu=once(gpu,'    ggml_vk_debug_label dbg(compute_ctx, cgraph, node_idx, ctx->num_additional_fused_ops);','    ggml_vk_debug_label dbg(compute_ctx, cgraph, node_idx, ctx->num_additional_fused_ops);\n    const int measured_slot=load_query_begin(ctx,compute_ctx,node);')
 gpu=once(gpu,'    // the submit path below can end the command buffer, so close the region first','    load_query_end(compute_ctx,measured_slot);\n    // the submit path below can end the command buffer, so close the region first')
 marker='    ggml_vk_cleanup(ctx);\n\n    delete ctx;';gpu=once(gpu,marker,'    ggml_vk_cleanup(ctx);load_query_release(ctx);\n\n    delete ctx;')
 ec=n['compile_commands'][0];entry=Path(ec[ec.index('-c')+1]).read_text();old=n['GDN_model_comparison']['scope'];scope=dict(old,candidate='unchanged-batches-bounded-GPU-operator-timestamps',tail_disabled_in_both_arms=bool(a.tail_disabled),GPU_timestamps_candidate_only=True,query_count=8192,query_ranges_maximum_per_completed_call=4096,no_new_fence_or_queue_wait=True,ordinary_speed_comparison_valid=False)
 entry='''#include <array>
#include <cstdint>
extern "C" void qwen_load_gpu_probe_select(bool);
extern "C" void qwen_load_gpu_probe_stats(std::uint64_t*);
static std::array<std::uint64_t,26>probe_report(){std::array<std::uint64_t,26>v{};qwen_load_gpu_probe_stats(v.data());return v;}
'''+entry
 entry=once(entry,literal(old),literal(scope));entry=once(entry,'qwen_load_tail_select(arm==1);','qwen_load_tail_select('+('true'if a.tail_disabled else'false')+');qwen_load_gpu_probe_select(arm==1);')
 entry=once(entry,'row["serialized_tail_disabled"]=arm==1;','row["serialized_tail_disabled"]='+('true'if a.tail_disabled else'false')+';')
 marker='            const auto cpu_before=qwen_load::snapshot();';entry=once(entry,marker,'            const auto probe_before=probe_report();Json probe_tokens=Json::array();\n'+marker)
 marker='            },[&](const auto &token,const auto &m){';entry=once(entry,marker,marker+'qwen_load::CpuSpan measured_persistence(qwen_load::token_persistence);probe_tokens.push_back({{"generated_tokens",m.generated_tokens},{"counters",probe_report()}});')
 marker='            const auto &result=trial.run(request,';entry=once(entry,marker,'            qwen_load::CpuSpan measured_run(qwen_load::request_run);\n'+marker)
 marker='            qwen_checkpoint_trial_stats(checkpoint_after);';entry=once(entry,marker,'            measured_run.end();\n'+marker)
 marker='            row["phase"]=phase;';entry=once(entry,marker,'            row["GPU_probe_before"]=probe_before;row["GPU_probe_after"]=probe_report();row["GPU_probe_token_boundaries"]=probe_tokens;row["GPU_timestamp_diagnostic"]=true;\n'+marker)
 # Actual lifetime proof is captured after the model/context owners retire.
 marker='{"all_model_source_device_owners_positively_retired",true},{"device_ledger_live_bytes",0}';entry=once(entry,marker,marker+',{ "GPU_probe_final",probe_report()}')
 en=n['routing_sharing']['commands'][2];engine=Path(en[en.index('-c')+1]).read_text();engine='extern "C" void qwen_load_gpu_probe_drain();\n'+engine
 marker='if(gpu_checkpoint_) { qwen_load::CpuSpan load_checkpoint(qwen_load::checkpoint);ProfileScope timing(timing_.checkpoint_ns); gpu_checkpoint_(); }';engine=once(engine,marker,marker+'\n    qwen_load_gpu_probe_drain();')
 signature='const float *LlamaEngine::effective_logits()const {';engine=once(engine,signature,signature+'qwen_load::CpuSpan measured(qwen_load::logit_access);')
 r,jobs,sources=link(a.parent,a.out,dict(entry=(ec,entry),engine=(en,engine),gpu=(gc,gpu)),[Path(__file__),ROOT/'native/app/load_followup_timing.h']);update_sources(r,jobs,sources);r['GDN_model_comparison']['scope']=scope;r['next_five_comparison'].update(scope=scope,actual_sources=sources,commands=jobs);r['io_gpu_comparison'].update(GPU_source=sources['gpu'],GPU_command=jobs['gpu']);r['load_followup'].update(scope=scope,actual_sources=sources,commands=jobs);r['load_GPU_probe']=dict(groups=GROUPS,scope=scope,actual_sources=sources,commands=jobs,fused_ranges_not_pure_individual_shader_time=True)
 raw=a.out/'linked-seed.private.json';write_json(raw,r);subprocess.run([sys.executable,'-X','utf8','-B',str(ROOT/'tools/rebind_gpu_provenance.py'),'--linked',str(raw),'--out',str(a.out/'GPU-provenance')],check=True);r=json.loads((a.out/'GPU-provenance/receipt.private.json').read_text());seal(r,a.workspace,a.cache,a.out);write_json(a.out/'core-safety.private.json',dict(completed=True,graph_batch_predicates_and_existing_waits_unchanged=True,result_retrieval_follows_existing_positive_device_completion=True,query_WAIT_flag=False,GPU_ranges_are_diagnostic=True,PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()
