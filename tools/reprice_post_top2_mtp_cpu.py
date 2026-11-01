#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Test actual MTP CPU consumption rather than mistake512MiB for a physical limit."""
import argparse,json
from pathlib import Path
from build_cache_capacity_1125 import literal,recipes
from build_next_five_comparison import update_sources
from build_speculative_batch_probe import once
from expert_q4 import require,write_json
from scoped_native_variant import link,seal
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in('parent','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();n=json.loads(a.parent.read_text());a.out.mkdir(parents=True,exist_ok=False)
 selected={c[c.index('-o')+1]:c for c in recipes(n)if'-c'in c and'-o'in c and c[c.index('-o')+1]in n['link_command']}
 old=n['GDN_model_comparison']['scope'];scope=dict(old,CPU_heap_cap_bytes=672<<20,CPU_heap_cap_not_raised=False,CPU_budget_basis='actual624.125MiB_already_mapped_before_old512MiB_shader_guard',physical_Direct_Flexible_and_OS_reserves_unchanged=True)
 variants={};providers=[]
 for c in selected.values():
  s=Path(c[c.index('-c')+1]).read_text()
  if 'maximum_model_CPU_heap_bytes'in s:
   s=s.replace('qwen_app::maximum_model_CPU_heap_bytes','(672ull<<20)');role='entry'if c==n['compile_commands'][0]else 'heap_budget'+str(len(providers));providers.append(str(Path(c[c.index('-c')+1])))
   if role=='entry':s=once(s,literal(old),literal(scope))
   variants[role]=(c,s)
 require(len(providers)==3 and'entry'in variants,'Exactly the three selected CPU budget checks must be repriced')
 ctx=[c for c in selected.values()if'uint32_t llama_context::graph_max_nodes('in Path(c[c.index('-c')+1]).read_text()];require(len(ctx)==1,'Actual head capacity provider required');cc=ctx[0];s=Path(cc[cc.index('-c')+1]).read_text()
 s='#include <cstdio>\nextern "C" void qwen_native_stage(const char*);\n'+s
 s=once(s,'        return std::max<uint32_t>(n_tokens*40,32u*active);','        const auto cap=std::max<uint32_t>(n_tokens*40,32u*active);char stage[192];std::snprintf(stage,sizeof(stage),"MTP_actual_graph_capacity nodes=%u active_tensors=%u n_tokens=%u no_aux_rollback=1",cap,active,n_tokens);qwen_native_stage(stage);return cap;')
 variants['context']=(cc,s);r,jobs,sources=link(a.parent,a.out,variants,[Path(__file__)]);update_sources(r,jobs,sources)
 for row in r['CPU_metadata_scope']['changed_sources']:
  for role,(c,_)in variants.items():
   if row['object_path']==c[c.index('-o')+1]:row.update(source=sources[role],object_path=jobs[role][jobs[role].index('-o')+1],command=jobs[role])
 r['GDN_model_comparison']['scope']=scope;r['next_five_comparison'].update(scope=scope,actual_sources=sources,commands=jobs);r['post_top2_MTP_CPU_budget']=dict(scope=scope,actual_sources=sources,commands=jobs,selected_check_providers=providers)
 seal(r,a.workspace,a.cache,a.out);write_json(a.out/'core-safety.private.json',dict(completed=True,old512MiB_not_physical_limit=True,new_test_cap_bytes=672<<20,original_OS_minimum_and_Direct_allocation_checks_preserved=True,no_libc_fallbacks_permitted=True,PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()
