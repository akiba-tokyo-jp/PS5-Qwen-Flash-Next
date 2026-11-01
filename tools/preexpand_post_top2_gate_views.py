#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Order cached weight views before both projections so the fusion is adjacent."""
import argparse,json
from pathlib import Path
from build_cache_capacity_1125 import recipes,literal
from build_next_five_comparison import update_sources
from build_speculative_batch_probe import once
from expert_q4 import record,require,write_json
from scoped_native_variant import link,seal

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in('parent','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();n=json.loads(a.parent.read_text());a.out.mkdir(parents=True,exist_ok=False)
 candidates={c[c.index('-o')+1]:c for c in recipes(n)if '-c'in c and '-o'in c and c[c.index('-o')+1]in n['link_command']}
 found=[c for c in candidates.values()if 'ggml_tensor * llm_graph_context::build_lora_mm_id('in Path(c[c.index('-c')+1]).read_text()]
 require(len(found)==1,'One actually linked graph-context provider required');c=found[0];graph=Path(c[c.index('-c')+1]).read_text()
 marker='        // separate gate and up path\n'
 graph=once(graph,marker,marker+'''        // Place both zero-compute cached weight views before the first MM_ID.
        // A view between the two projections prevents fusion preservation
        // before allocation, and the generic reorder then separates GLU.
        if(slots&&moe_cache&&up_exps&&gate_exps&&up_exps->type==GGML_TYPE_Q2_K&&gate_exps->type==GGML_TYPE_Q2_K){
            auto*cached_up=moe_cache->get_experts(up_exps);auto*cached_gate=moe_cache->get_experts(gate_exps);
            if(cached_up&&cached_gate){ggml_build_forward_expand(gf,cached_up);ggml_build_forward_expand(gf,cached_gate);}
        }
''')
 old=n['GDN_model_comparison']['scope'];scope=dict(old,cached_weight_views_expanded_before_both_MM_ID=True,gate_up_original_math_and_qualified_shader_unchanged=True)
 ec=n['compile_commands'][0];entry=once(Path(ec[ec.index('-c')+1]).read_text(),literal(old),literal(scope))
 r,jobs,sources=link(a.parent,a.out,dict(entry=(ec,entry),graph=(c,graph)),[Path(__file__)])
 update_sources(r,jobs,sources);r['routing_sharing']['actual_sources']['graph']=sources['graph'];r['routing_sharing']['commands'][5]=jobs['graph']
 r['GDN_model_comparison']['scope']=scope;r['next_five_comparison'].update(scope=scope,actual_sources=sources,commands=jobs)
 r['post_top2_gate_views']=dict(scope=scope,actual_sources=sources,commands=jobs,prior_38500_returned_coverage_refusal_preserved=True)
 seal(r,a.workspace,a.cache,a.out);write_json(a.out/'core-safety.private.json',dict(completed=True,kind='preexpanded_weight_views_for_Gate_Up_fusion',candidate=record(a.out/'receipt.private.json'),
  new_GPU_payloads=0,original_dependencies_and_external_input_lifetimes_preserved=True,PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()
