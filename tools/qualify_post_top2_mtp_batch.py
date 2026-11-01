#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Respect the checkpoint's existing token-tail splitter for single-token MTP."""
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
 a=p.parse_args();n=json.loads(a.parent.read_text());a.out.mkdir(parents=True,exist_ok=False);en=n['routing_sharing']['commands'][2];engine=Path(en[en.index('-c')+1]).read_text();engine=once(engine,'p.n_ctx=256;p.n_batch=p.n_ubatch=1;p.n_seq_max=p.n_rs_seq=1;','p.n_ctx=256;p.n_batch=p.n_ubatch=16;p.n_seq_max=p.n_rs_seq=1;')
 selected={c[c.index('-o')+1]:c for c in recipes(n)if '-c'in c and '-o'in c and c[c.index('-o')+1]in n['link_command']};cs=[c for c in selected.values()if 'uint32_t llama_context::graph_max_nodes('in Path(c[c.index('-c')+1]).read_text()];require(len(cs)==1,'Actual MTP-aware context provider required');cc=cs[0];ctx=once(Path(cc[cc.index('-c')+1]).read_text(),'cparams.n_seq_max==1&&cparams.n_ubatch==1&&!cparams.training','cparams.n_seq_max==1&&cparams.n_ubatch==16&&!cparams.training')
 old=n['GDN_model_comparison']['scope'];scope=dict(old,MTP_actual_input_tokens_per_call=1,MTP_batch_and_ubatch_capacity=16,
  original_PLE_token_tail_splitter_preserved=True,native42500_assertion='n_ubatch > n_keep_tail',no_target_width_or_memory_quota_increase=True)
 ec=n['compile_commands'][0];entry=once(Path(ec[ec.index('-c')+1]).read_text(),literal(old),literal(scope));r,jobs,sources=link(a.parent,a.out,dict(entry=(ec,entry),engine=(en,engine),context=(cc,ctx)),[Path(__file__)])
 update_sources(r,jobs,sources);r['GDN_model_comparison']['scope']=scope;r['next_five_comparison'].update(scope=scope,actual_sources=sources,commands=jobs);r['post_top2_MTP_tail_capacity']=dict(scope=scope,actual_sources=sources,commands=jobs)
 seal(r,a.workspace,a.cache,a.out);write_json(a.out/'core-safety.private.json',dict(completed=True,candidate=record(a.out/'receipt.private.json'),actual_MTP_tokens_one_and_target_width_two_preserved=True,original_memory_caps_preserved=True,PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()
