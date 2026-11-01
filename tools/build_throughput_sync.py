#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Retain pending writes while narrowing proven WAR hazards to execution ordering."""
import argparse,json,subprocess,sys
from pathlib import Path
from build_throughput_owner import entry_scope
from build_next_five_comparison import update_sources
from build_cache_capacity_1125 import literal
from build_speculative_batch_probe import once
from expert_q4 import record,require,write_json
from scoped_native_variant import link,seal
ROOT=Path(__file__).resolve().parents[1]

def transform(source):
 source='#include "throughput_options.h"\n'+source
 source=once(source,'    VK_LOG_DEBUG("ggml_vk_sync_buffers()");','    VK_LOG_DEBUG("ggml_vk_sync_buffers()");\n    ++qwen_throughput::stats[10];')
 helper='''static void ggml_vk_war_execution_barrier(vk_context&subctx){
    ++qwen_throughput::stats[10];++qwen_throughput::stats[11];
    // WAR needs execution ordering, while unrelated unpublished writes remain
    // in unsynced_nodes_written until a later full availability/visibility barrier.
    const vk::MemoryBarrier execution_only{};
    subctx->s->buffer->buf.pipelineBarrier(subctx->p->q->stage_flags,subctx->p->q->stage_flags,{}, {execution_only}, {}, {});
}

'''
 source=once(source,'static void ggml_vk_reset_event(vk_context& ctx, vk::Event& event) {',helper+'static void ggml_vk_reset_event(vk_context& ctx, vk::Event& event) {')
 first=source.index('        // This logic detects dependencies between modes in the graph');last=source.index('        // Add all fused nodes to the unsynchronized lists.',first);part=source[first:last]
 part=once(part,'        bool need_sync = false;','        bool need_sync=false,war_hazard=false,write_hazard=false;')
 start=part.index('        for (int32_t i = 0; i < ctx->num_additional_fused_ops + 1 && !need_sync; ++i) {');end=part.index('\n        if (need_sync) {',start);original=part[start:end]
 classified='''        if(qwen_throughput::mode.load(std::memory_order_relaxed)&8){
            for(int32_t i=0;i<ctx->num_additional_fused_ops+1&&!write_hazard;++i){
                const auto*cur_node=cgraph->nodes[node_idx+i];
                if(ctx->fused_ops_write_mask&(1<<i)){
                    war_hazard|=overlaps_unsynced(cur_node,ctx->unsynced_nodes_read);
                    write_hazard|=overlaps_unsynced(cur_node,ctx->unsynced_nodes_written);
                }
                for(uint32_t j=0;j<GGML_MAX_SRC&&!write_hazard;++j)
                    if(cur_node->src[j])write_hazard|=overlaps_unsynced(cur_node->src[j],ctx->unsynced_nodes_written);
            }
            need_sync=war_hazard||write_hazard;
        }else{
'''+original+'''
        }
'''
 part=part[:start]+classified+part[end:]
 old='''            ctx->unsynced_nodes_written.clear();
            ctx->unsynced_nodes_read.clear();
            ggml_vk_sync_buffers(ctx, compute_ctx);'''
 new='''            const bool execution_only=(qwen_throughput::mode.load(std::memory_order_relaxed)&8)&&war_hazard&&!write_hazard&&
                !ctx->prealloc_x_need_sync&&!ctx->prealloc_y_need_sync&&!ctx->prealloc_split_k_need_sync;
            ctx->unsynced_nodes_read.clear();
            if(execution_only){
                // Clearing pending writes here would lose a later RAW dependency.
                ggml_vk_war_execution_barrier(compute_ctx);
            }else{
                ctx->unsynced_nodes_written.clear();
                ggml_vk_sync_buffers(ctx,compute_ctx);
            }'''
 part=once(part,old,new);return source[:first]+part+source[last:]

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in('parent','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 p.add_argument('--base-throughput-mode',type=int,default=0);a=p.parse_args();n=json.loads(a.parent.read_text());a.out.mkdir(parents=True,exist_ok=False)
 ec,entry,old=entry_scope(n,8,a.base_throughput_mode);scope=dict(old,candidate='throughput-4-proven-WAR-execution-only',pending_independent_writes_retained=True,RAW_WAW_transfer_and_preallocated_workspace_dependencies_preserved=True,original_execution_stages_fences_and_queue_completion=True)
 entry=once(entry,literal(old),literal(scope));gc=n['frontier']['commands']['gpu'];require(gc[gc.index('-o')+1]in n['link_command'],'Actual selected GPU provider required');gpu=transform(Path(gc[gc.index('-c')+1]).read_text())
 r,jobs,sources=link(a.parent,a.out,dict(entry=(ec,entry),gpu=(gc+['-I',str(ROOT/'native/app')],gpu)),[Path(__file__),ROOT/'tools/build_throughput_owner.py',ROOT/'native/app/throughput_options.h']);update_sources(r,jobs,sources)
 r['GDN_model_comparison']['scope']=scope;r['next_five_comparison'].update(scope=scope,actual_sources=sources,commands=jobs);r['frontier']['scope']=scope;r['frontier']['actual_sources'].update(sources);r['frontier']['commands'].update(jobs);r['throughput']=dict(scope=scope,actual_sources=sources,commands=jobs)
 r['io_gpu_comparison'].update(GPU_command=jobs['gpu'],GPU_source=sources['gpu']);unsealed=a.out/'unsealed.private.json';write_json(unsealed,r)
 run=subprocess.run([sys.executable,'-X','utf8','-B',str(ROOT/'tools/rebind_gpu_provenance.py'),'--linked',str(unsealed),'--out',str(a.out/'GPU-provenance')],capture_output=True,timeout=600);(a.out/'GPU-provenance.private.log').write_bytes(run.stdout+run.stderr);require(run.returncode==0,run.stderr.decode(errors='replace')[-3000:]);r=json.loads((a.out/'GPU-provenance/receipt.private.json').read_text());seal(r,a.workspace,a.cache,a.out)
 write_json(a.out/'core-safety.private.json',dict(completed=True,scope=scope,shared_driver_unchanged=True,all_original_shader_assets_unchanged=True,availability_and_visibility_required_for_pending_writes=True,standalone_native_fixture_required_before_full_model=True,positive_completion_and_owner_validation_preserved=True,PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()
