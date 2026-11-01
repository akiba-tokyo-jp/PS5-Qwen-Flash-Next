#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Report the exact mapped/peak/fallback term at the existing shader heap guard."""
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
 selected={c[c.index('-o')+1]:c for c in recipes(n)if '-c'in c and '-o'in c and c[c.index('-o')+1]in n['link_command']};needle='refuse("External shader storage exceeds the existing tracked CPU heap budget");'
 found=[c for c in selected.values()if needle in Path(c[c.index('-c')+1]).read_text()];require(len(found)==1,'One actual linked shader-heap guard required');c=found[0];s='#include <cstdio>\n'+Path(c[c.index('-c')+1]).read_text()
 s=once(s,needle,'''{char detail[256];std::snprintf(detail,sizeof(detail),"External shader heap refusal mapped=%llu peak=%llu cap=%llu libc_fallbacks=%llu",
 static_cast<unsigned long long>(heap.mapped_bytes),static_cast<unsigned long long>(heap.peak_bytes),
 static_cast<unsigned long long>(qwen_app::maximum_model_CPU_heap_bytes),static_cast<unsigned long long>(heap.libc_fallbacks));refuse(detail);}''')
 old=n['GDN_model_comparison']['scope'];scope=dict(old,shader_heap_refusal_details=True,diagnostic_fields=['mapped_bytes','peak_bytes','cap_bytes','libc_fallbacks'],original_CPU_GUARD_predicate_unchanged=True)
 ec=n['compile_commands'][0];entry=once(Path(ec[ec.index('-c')+1]).read_text(),literal(old),literal(scope))
 r,jobs,sources=link(a.parent,a.out,dict(entry=(ec,entry),heap_guard=(c,s)),[Path(__file__)]);update_sources(r,jobs,sources)
 for row in r['CPU_metadata_scope']['changed_sources']:
  if row['object_path']==c[c.index('-o')+1]:row.update(source=sources['heap_guard'],object_path=jobs['heap_guard'][jobs['heap_guard'].index('-o')+1],command=jobs['heap_guard'])
 r['GDN_model_comparison']['scope']=scope;r['next_five_comparison'].update(scope=scope,actual_sources=sources,commands=jobs);r['post_top2_heap_diagnostic']=dict(scope=scope,actual_sources=sources,commands=jobs)
 seal(r,a.workspace,a.cache,a.out);write_json(a.out/'core-safety.private.json',dict(completed=True,kind='exact_CPU_heap_guard_diagnostic',candidate=record(a.out/'receipt.private.json'),
  guard_not_weakened=True,fixed_stack_diagnostic_bytes=256,extra_GPU_calls=0,PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()
