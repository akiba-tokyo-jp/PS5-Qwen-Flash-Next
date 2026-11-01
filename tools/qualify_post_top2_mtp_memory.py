#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Price MTP scheduler metadata from its actual head rather than the full trunk."""
import argparse,json
from pathlib import Path
from build_cache_capacity_1125 import literal,recipes
from build_next_five_comparison import update_sources
from build_speculative_batch_probe import once
from expert_q4 import record,require,write_json
from scoped_native_variant import link,seal
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in('parent','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();n=json.loads(a.parent.read_text());a.out.mkdir(parents=True,exist_ok=False)
 selected={c[c.index('-o')+1]:c for c in recipes(n)if '-c'in c and '-o'in c and c[c.index('-o')+1]in n['link_command']}
 found=[c for c in selected.values()if 'uint32_t llama_context::graph_max_nodes('in Path(c[c.index('-c')+1]).read_text()];require(len(found)==1,'Actual context provider required');cc=found[0];ctx=Path(cc[cc.index('-c')+1]).read_text()
 ctx=once(ctx,'uint32_t llama_context::graph_max_nodes(uint32_t n_tokens) const {','''uint32_t llama_context::graph_max_nodes(uint32_t n_tokens) const {
    // Use the same32-nodes-per-tensor rule, counting only this single MTP
    // head and the two shared embedding/output tensors. The trunk is idle.
    if(cparams.ctx_type==LLAMA_CONTEXT_TYPE_MTP&&model.arch==LLM_ARCH_QWEN4EXP&&
       cparams.n_seq_max==1&&cparams.n_ubatch==1&&!cparams.training&&model.loras.empty()){
        uint32_t active=2;for(const auto&item:model.tensors_by_name)if(item.first.rfind("blk.48.",0)==0)++active;
        if(active!=34||!sampling.samplers.empty())throw std::runtime_error("Exact32-tensor single MTP head required");
        return std::max<uint32_t>(n_tokens*40,32u*active);
    }
''')
 ctx=once(ctx,'void llama_context::sched_new(size_t max_nodes, bool parallel) {','void llama_context::sched_new(size_t max_nodes, bool parallel) {\n    sched.reset();')
 ctx=once(ctx,'    gf_res_reserve.reset(new llm_graph_result(max_nodes));\n    gf_res_prev_active = nullptr;','    gf_res_prev_active=nullptr;gf_res_reserve.reset();\n    gf_res_reserve.reset(new llm_graph_result(max_nodes));')
 found=[c for c in selected.values()if 'refuse("External shader storage exceeds the existing tracked CPU heap budget");'in Path(c[c.index('-c')+1]).read_text()];require(len(found)==1,'One shader heap provider required');hc=found[0];heap='#include <cstdio>\n'+Path(hc[hc.index('-c')+1]).read_text()
 heap=once(heap,'refuse("External shader storage exceeds the existing tracked CPU heap budget");','''{char detail[256];std::snprintf(detail,sizeof(detail),"MTP shader heap refusal mapped=%llu peak=%llu cap=%llu libc_fallbacks=%llu",(unsigned long long)heap.mapped_bytes,(unsigned long long)heap.peak_bytes,(unsigned long long)qwen_app::maximum_model_CPU_heap_bytes,(unsigned long long)heap.libc_fallbacks);refuse(detail);}''')
 old=n['GDN_model_comparison']['scope'];scope=dict(old,control_node_cap=256,candidate_node_cap=256,MTP_active_tensor_count=34,MTP_graph_capacity=1088,
  MTP_graph_rule='same32nodes_per_actual_head_tensor_plus_two_shared',obsolete_synchronized_scheduler_released_before_replacement=True,CPU_heap_cap_bytes=536870912,CPU_heap_cap_not_raised=True)
 ec=n['compile_commands'][0];entry=once(Path(ec[ec.index('-c')+1]).read_text(),literal(old),literal(scope));entry=once(entry,'arm==0?"Top2-flop-divisor40":"Top2-flop-divisor40";','arm==0?"same-loaded-model-history-only":"matched-stateless-MTP-fallback";')
 r,jobs,sources=link(a.parent,a.out,dict(entry=(ec,entry),context=(cc,ctx),heap_guard=(hc,heap)),[Path(__file__)])
 update_sources(r,jobs,sources)
 for row in r['CPU_metadata_scope']['changed_sources']:
  if row['object_path']==hc[hc.index('-o')+1]:row.update(source=sources['heap_guard'],object_path=jobs['heap_guard'][jobs['heap_guard'].index('-o')+1],command=jobs['heap_guard'])
 r['GDN_model_comparison']['scope']=scope;r['next_five_comparison'].update(scope=scope,actual_sources=sources,commands=jobs);r['post_top2_MTP_memory']=dict(scope=scope,actual_sources=sources,commands=jobs)
 seal(r,a.workspace,a.cache,a.out);write_json(a.out/'core-safety.private.json',dict(completed=True,candidate=record(a.out/'receipt.private.json'),CPU_quota_unchanged=True,actual_MTP_ops_not_removed=True,PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()
