#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Preserve WAR visibility obligations through every compute submission boundary."""
import argparse,json,subprocess,sys
from pathlib import Path
from build_throughput_sync import transform as classify
from build_throughput_owner import entry_scope
from build_next_five_comparison import update_sources
from build_cache_capacity_1125 import literal
from build_speculative_batch_probe import once
from expert_q4 import record,require,write_json
from scoped_native_variant import link,seal
ROOT=Path(__file__).resolve().parents[1]

def transform(source):
 source=classify(source)
 state='''namespace {
struct ThroughputWarScope;
thread_local ThroughputWarScope*throughput_war_scope=nullptr;
std::uint64_t throughput_war_tail_flush_count=0;
struct ThroughputWarScope{
    ggml_backend_vk_context*owner;bool pending=false;ThroughputWarScope*previous;
    explicit ThroughputWarScope(ggml_backend_vk_context*p):owner(p),previous(throughput_war_scope){throughput_war_scope=this;}
    ~ThroughputWarScope(){throughput_war_scope=previous;}
};
}
extern "C" std::uint64_t qwen_throughput_sync_tail_flushes(){return throughput_war_tail_flush_count;}

'''
 source=once(source,'void ggml_vk_sync_buffers(ggml_backend_vk_context* ctx, vk_context& subctx) {',state+'void ggml_vk_sync_buffers(ggml_backend_vk_context* ctx, vk_context& subctx) {')
 source=once(source,'    const bool transfer_queue = subctx->p->q->transfer_only;','    const bool transfer_queue = subctx->p->q->transfer_only;\n    if(!transfer_queue&&throughput_war_scope&&throughput_war_scope->owner==ctx)throughput_war_scope->pending=false;')
 helper='''static void ggml_vk_publish_pending_war(ggml_backend_vk_context*ctx,vk_context&subctx){
    if(throughput_war_scope&&throughput_war_scope->owner==ctx&&throughput_war_scope->pending){
        // A later graph starts with empty dependency lists. Publish unrelated
        // writes before ending this submission, even if no later RAW exists.
        ++throughput_war_tail_flush_count;ggml_vk_sync_buffers(ctx,subctx);
        ctx->unsynced_nodes_written.clear();ctx->unsynced_nodes_read.clear();
    }
}

'''
 source=once(source,'static void ggml_vk_reset_event(vk_context& ctx, vk::Event& event) {',helper+'static void ggml_vk_reset_event(vk_context& ctx, vk::Event& event) {')
 source=once(source,'const bool execution_only=(qwen_throughput::mode.load(std::memory_order_relaxed)&8)&&war_hazard&&!write_hazard&&','const bool execution_only=(qwen_throughput::mode.load(std::memory_order_relaxed)&8)&&throughput_war_scope&&throughput_war_scope->owner==ctx&&war_hazard&&!write_hazard&&')
 source=once(source,'                ggml_vk_war_execution_barrier(compute_ctx);','                throughput_war_scope->pending|=!ctx->unsynced_nodes_written.empty();\n                ggml_vk_war_execution_barrier(compute_ctx);')
 source=once(source,'    if (submit || last_node) {\n        ggml_vk_ctx_end(compute_ctx);','    if (submit || last_node) {\n        ggml_vk_publish_pending_war(ctx,compute_ctx);\n        ggml_vk_ctx_end(compute_ctx);')
 start=source.index('static ggml_status ggml_backend_vk_graph_compute(');end=source.index('\nvoid ggml_vk_graph_optimize(',start);body=source[start:end]
 body=once(body,'    ggml_backend_vk_context * ctx = (ggml_backend_vk_context *)backend->context;','    ggml_backend_vk_context * ctx = (ggml_backend_vk_context *)backend->context;\n    ThroughputWarScope throughput_recording(ctx);')
 body=once(body,'                ggml_vk_ctx_end(flush_ctx);','                ggml_vk_publish_pending_war(ctx,flush_ctx);\n                ggml_vk_ctx_end(flush_ctx);')
 body=once(body,'        ggml_vk_ctx_end(compute_ctx);','        ggml_vk_publish_pending_war(ctx,compute_ctx);\n        ggml_vk_ctx_end(compute_ctx);')
 body=once(body,'    ctx->last_total_flops = total_flops;','    GGML_ASSERT(!throughput_recording.pending);\n    ctx->last_total_flops = total_flops;')
 return source[:start]+body+source[end:]

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in('parent','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 p.add_argument('--base-throughput-mode',type=int,default=0);a=p.parse_args();n=json.loads(a.parent.read_text());a.out.mkdir(parents=True,exist_ok=False)
 ec,entry,old=entry_scope(n,8,a.base_throughput_mode);scope=dict(old,candidate='throughput-4-proven-WAR-with-cross-submit-visibility',pending_independent_writes_retained=True,pending_writes_published_before_every_compute_batch_end=True,RAW_WAW_transfer_and_workspace_dependencies_preserved=True,original_execution_stages_fences_and_queue_completion=True)
 entry=once(entry,literal(old),literal(scope));entry='#include <cstdint>\nextern "C" std::uint64_t qwen_throughput_sync_tail_flushes();\n'+entry
 marker='            row["service_mode"]=qwen_service::mode.load();';entry=once(entry,marker,'            row["throughput_sync_tail_flushes"]=qwen_throughput_sync_tail_flushes();\n'+marker)
 gc=n['frontier']['commands']['gpu'];require(gc[gc.index('-o')+1]in n['link_command'],'Actual selected GPU provider required');gpu=transform(Path(gc[gc.index('-c')+1]).read_text())
 r,jobs,sources=link(a.parent,a.out,dict(entry=(ec,entry),gpu=(gc+['-I',str(ROOT/'native/app')],gpu)),[Path(__file__),ROOT/'tools/build_throughput_sync.py',ROOT/'tools/build_throughput_owner.py',ROOT/'native/app/throughput_options.h']);update_sources(r,jobs,sources)
 r['GDN_model_comparison']['scope']=scope;r['next_five_comparison'].update(scope=scope,actual_sources=sources,commands=jobs);r['frontier']['scope']=scope;r['frontier']['actual_sources'].update(sources);r['frontier']['commands'].update(jobs);r['throughput']=dict(scope=scope,actual_sources=sources,commands=jobs)
 r['io_gpu_comparison'].update(GPU_command=jobs['gpu'],GPU_source=sources['gpu']);unsealed=a.out/'unsealed.private.json';write_json(unsealed,r)
 run=subprocess.run([sys.executable,'-X','utf8','-B',str(ROOT/'tools/rebind_gpu_provenance.py'),'--linked',str(unsealed),'--out',str(a.out/'GPU-provenance')],capture_output=True,timeout=600);(a.out/'GPU-provenance.private.log').write_bytes(run.stdout+run.stderr);require(run.returncode==0,run.stderr.decode(errors='replace')[-3000:]);r=json.loads((a.out/'GPU-provenance/receipt.private.json').read_text());seal(r,a.workspace,a.cache,a.out)
 write_json(a.out/'core-safety.private.json',dict(completed=True,scope=scope,shared_driver_and_shader_assets_unchanged=True,per_recording_thread_and_nested_context_visibility_scope=True,unpublished_writes_never_dropped_at_submit_or_graph_end=True,standalone_same_graph_and_cross_graph_oracles_required=True,PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()
