#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Remove unused auxiliary rollback snapshots; preserve complete target rollback."""
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
 a=p.parse_args();n=json.loads(a.parent.read_text());a.out.mkdir(parents=True,exist_ok=False);en=n['routing_sharing']['commands'][2];engine=Path(en[en.index('-c')+1]).read_text();engine=once(engine,'p.n_ctx=256;p.n_batch=p.n_ubatch=16;p.n_seq_max=p.n_rs_seq=1;','p.n_ctx=256;p.n_batch=p.n_ubatch=1;p.n_seq_max=1;p.n_rs_seq=0;')
 selected={c[c.index('-o')+1]:c for c in recipes(n)if '-c'in c and '-o'in c and c[c.index('-o')+1]in n['link_command']};cs=[c for c in selected.values()if 'uint32_t llama_context::graph_max_nodes('in Path(c[c.index('-c')+1]).read_text()];require(len(cs)==1,'One actual MTP-aware context required');cc=cs[0];ctx=once(Path(cc[cc.index('-c')+1]).read_text(),'cparams.n_seq_max==1&&cparams.n_ubatch==16&&!cparams.training','cparams.n_seq_max==1&&cparams.n_ubatch==1&&!cparams.training')
 old=n['GDN_model_comparison']['scope'];scope=dict(old,MTP_batch_and_ubatch_capacity=1,MTP_auxiliary_rollback_snapshots=0,target_rollback_snapshots=1,
  hybrid_tail_source='llama-memory-hybrid.cpp:n_rs_seq>0?n_rs_seq+1:0',single_token_auxiliary_needs_no_rollback=True,auxiliary_KV_cleared_each_proposal=True)
 ec=n['compile_commands'][0];entry=once(Path(ec[ec.index('-c')+1]).read_text(),literal(old),literal(scope));r,jobs,sources=link(a.parent,a.out,dict(entry=(ec,entry),engine=(en,engine),context=(cc,ctx)),[Path(__file__)])
 update_sources(r,jobs,sources);r['GDN_model_comparison']['scope']=scope;r['next_five_comparison'].update(scope=scope,actual_sources=sources,commands=jobs);r['post_top2_MTP_stateless']=dict(scope=scope,actual_sources=sources,commands=jobs)
 seal(r,a.workspace,a.cache,a.out);write_json(a.out/'core-safety.private.json',dict(completed=True,candidate=record(a.out/'receipt.private.json'),target_complete_rollback_and_verification_unchanged=True,CPU_GPU_OS_caps_unchanged=True,PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()
