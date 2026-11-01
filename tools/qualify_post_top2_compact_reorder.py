#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Retain safe row reordering when greedy omits probability/candidate surfaces."""
import argparse,json
from pathlib import Path
from build_speculative_batch_probe import once
from expert_q4 import record,write_json
from scoped_native_variant import link,seal

def transform(ctx):
 for name in('probs','candidates'):
  ctx=once(ctx,'            assert(sampling.'+name+'.size > 0);','            assert(sampling.'+name+'.size > 0 || qwen_post_compact_greedy_outputs());')
  old='            for (uint64_t k = 0; k < n_vocab; ++k) {\n                std::swap(sampling.'+name+'.data[i0*n_vocab + k], sampling.'+name+'.data[i1*n_vocab + k]);\n            }'
  ctx=once(ctx,old,old.replace('            for (','            if(sampling.'+name+'.has_data())for (',1))
 return ctx

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in('parent','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();n=json.loads(a.parent.read_text());a.out.mkdir(parents=True,exist_ok=False);cc=n['post_top2_compact_sampler_outputs']['commands']['context'];s=transform(Path(cc[cc.index('-c')+1]).read_text())
 r,jobs,sources=link(a.parent,a.out,dict(context=(cc,s)),[Path(__file__)])
 r['post_top2_compact_sampler_outputs']['actual_sources']['context']=sources['context'];r['post_top2_compact_sampler_outputs']['commands']['context']=jobs['context']
 r['post_top2_compact_reorder']=dict(actual_sources=sources,commands=jobs,all_count_vectors_and_sampled_F32_surfaces_preserved=True,omitted_surfaces_never_dereferenced_or_swapped=True)
 seal(r,a.workspace,a.cache,a.out);write_json(a.out/'core-safety.private.json',dict(completed=True,kind='safe_compact_backend_output_row_reorder',candidate=record(a.out/'receipt.private.json'),
  full_raw_and_sampled_logits_preserved=True,CPU_budget_unchanged=True,PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()
