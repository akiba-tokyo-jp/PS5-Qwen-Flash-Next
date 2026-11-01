#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Add bounded GPU role timestamps to the request-bound submit observation."""
import argparse,json,subprocess,sys
from pathlib import Path
from build_load_gpu_profile import PROBE,GROUPS
from build_speculative_batch_probe import once
from build_throughput_current import command
from build_cache_capacity_1125 import literal
from scoped_native_variant import link,seal
from expert_q4 import record,write_json
ROOT=Path(__file__).resolve().parents[1]

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('parent','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();n=json.loads(a.parent.read_text());a.out.mkdir(parents=True,exist_ok=False)
 gc=command(n,n['lossless_shader_storage']['vulkan_object']['path']);gpu=Path(gc[gc.index('-c')+1]).read_text()
 anchor='bool ggml_vk_build_graph(ggml_backend_vk_context * ctx, ggml_cgraph * cgraph, int node_idx, ggml_tensor *node_begin, int node_idx_begin, bool last_node, bool almost_ready, bool submit){'
 gpu=once(gpu,anchor,PROBE+'\n'+anchor)
 gpu=once(gpu,'    ggml_vk_debug_label dbg(compute_ctx, cgraph, node_idx, ctx->num_additional_fused_ops);','    ggml_vk_debug_label dbg(compute_ctx, cgraph, node_idx, ctx->num_additional_fused_ops);\n    const int measured_slot=load_query_begin(ctx,compute_ctx,node);')
 gpu=once(gpu,'    // the submit path below can end the command buffer, so close the region first','    load_query_end(compute_ctx,measured_slot);\n    // the submit path below can end the command buffer, so close the region first')
 gpu=once(gpu,'    ggml_vk_cleanup(ctx);\n\n    delete ctx;','    ggml_vk_cleanup(ctx);load_query_release(ctx);\n\n    delete ctx;')
 ec=n['compile_commands'][0];entry='''#include <array>
#include <cstdint>
extern "C" void qwen_load_gpu_probe_select(bool);
extern "C" void qwen_load_gpu_probe_stats(std::uint64_t*);
static std::array<std::uint64_t,26>submission_query_stats(){std::array<std::uint64_t,26>v{};qwen_load_gpu_probe_stats(v.data());return v;}
'''+Path(ec[ec.index('-c')+1]).read_text()
 entry=once(entry,'qwen_ps5_timing_select(arm);','qwen_ps5_timing_select(arm);qwen_load_gpu_probe_select(arm);')
 entry=once(entry,'            const auto cpu_before=qwen_load::snapshot();','            const auto query_before=submission_query_stats();Json query_tokens=Json::array();\n            const auto cpu_before=qwen_load::snapshot();')
 entry=once(entry,'            },[&](const auto &token,const auto &m){','            },[&](const auto &token,const auto &m){query_tokens.push_back({{"generated_tokens",m.generated_tokens},{"counters",submission_query_stats()}});')
 entry=once(entry,'            row["phase"]=phase;','            row["GPU_probe_before"]=query_before;row["GPU_probe_after"]=submission_query_stats();row["GPU_probe_token_boundaries"]=query_tokens;\n            row["phase"]=phase;')
 marker='{"all_model_source_device_owners_positively_retired",true},{"device_ledger_live_bytes",0}'
 entry=once(entry,marker,marker+',{ "GPU_probe_final",submission_query_stats()}')
 en=command(n,next(x for x in n['link_command']if Path(x).name=='engine.o'));engine='extern "C" void qwen_load_gpu_probe_drain();\n'+Path(en[en.index('-c')+1]).read_text()
 marker='if(gpu_checkpoint_) { qwen_load::CpuSpan load_checkpoint(qwen_load::checkpoint);ProfileScope timing(timing_.checkpoint_ns); gpu_checkpoint_(); }'
 engine=once(engine,marker,marker+'\n    qwen_load_gpu_probe_drain();')
 old=n['GDN_model_comparison']['scope'];scope=dict(old,GPU_timestamp_diagnostic=True,no_new_GPU_wait=True,ordinary_speed_comparison_valid=False)
 entry=once(entry,literal(old),literal(scope))
 r,jobs,sources=link(a.parent,a.out,dict(entry=(ec,entry),engine=(en,engine),gpu=(gc,gpu)),[Path(__file__),ROOT/'tools/build_load_gpu_profile.py'])
 r['GDN_model_comparison']['scope']=scope;r['next_five_comparison']['scope']=scope
 r['io_gpu_comparison'].update(GPU_source=sources['gpu'],GPU_command=jobs['gpu'])
 r['submission_GPU_diagnostic']=dict(groups=GROUPS,scope=scope,actual_sources=sources,commands=jobs,existing_positive_completion_before_query_retrieval=True)
 seed=a.out/'linked-seed.private.json';write_json(seed,r)
 subprocess.run([sys.executable,'-X','utf8','-B',str(ROOT/'tools/rebind_gpu_provenance.py'),'--linked',str(seed),'--out',str(a.out/'GPU-provenance')],check=True)
 r=json.loads((a.out/'GPU-provenance/receipt.private.json').read_text());seal(r,a.workspace,a.cache,a.out)
 write_json(a.out/'core-safety.private.json',dict(completed=True,scope=scope,host_source_and_link_checks_only=True,query_result_retrieval_requires_existing_positive_completion=True,new_queue_waits=0,original_weight_bits_and_routing_policy_preserved=True,native_qualification_claimed=False,PS5_operations=0,CI_runs=0))
 print(json.dumps(dict(completed=True,GPU_role_groups=len(GROUPS),new_queue_waits=0)))
if __name__=='__main__':main()
