#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compare cap6 with cap8/12 using the actual selected single-latest policy."""
import argparse,json
from pathlib import Path
from build_cache_capacity_1125 import literal
from build_next_five_comparison import update_sources
from build_speculative_batch_probe import once
from expert_q4 import record,require,write_json
from scoped_native_variant import link,seal
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('parent','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--cap',type=int,choices=(8,12),required=True);a=p.parse_args()
    n=json.loads(a.parent.read_text());old=n['GDN_model_comparison']['scope']
    require(old['candidate']=='Q4-cache3712-Top2','Actual Q4/Top2 comparison parent required');a.out.mkdir(parents=True,exist_ok=False)
    scope=dict(old,schema='ps5-qwen-post-top2-causal-v1',candidate='single-latest-cap'+str(a.cap),candidate_id=1,
        control_Experts=2,candidate_Experts=2,control_attempt_cap=6,candidate_attempt_cap=a.cap,
        proposal_policy='selected_normal_single_latest',verification_width=2,all_state_rollback_checks_preserved=True)
    ec=n['compile_commands'][0];entry=Path(ec[ec.index('-c')+1]).read_text()
    entry='#include "post_top2_causal.h"\n'+entry
    entry=once(entry,literal(old),literal(scope));entry=once(entry,'qwen_next_select(arm?2:0);','qwen_next_select(2);')
    entry=once(entry,'arm==0?"Q4-cache3712-Top6":"Q4-cache3712-Top2";',
               'arm==0?"single-latest-cap6":"single-latest-cap'+str(a.cap)+'";')
    require(entry.count('qwen_app::NextFiveCausalEngine causal')==1,'One admitted causal controller required')
    entry=once(entry,'qwen_app::NextFiveCausalEngine causal(*engine,model,context,ordinal>=10);',
        'qwen_app::PostTop2CausalEngine causal(*engine,model,context,ordinal>=10,arm?'+str(a.cap)+':6);')
    entry=entry.replace('qwen_app::NextFiveCausalEngine&','qwen_app::PostTop2CausalEngine&')
    marker='            row["phase"]=phase;'
    entry=once(entry,marker,'            row["causal_attempt_cap"]=arm?'+str(a.cap)+':6;row["proposal_policy"]="single_latest";\n'+marker)
    r,jobs,sources=link(a.parent,a.out,dict(entry=(ec+['-I',str(ROOT/'native/app')],entry)),[Path(__file__),ROOT/'native/app/post_top2_causal.h'])
    update_sources(r,jobs,sources);r['GDN_model_comparison']['scope']=scope
    r['next_five_comparison'].update(scope=scope,actual_sources=sources,commands=jobs,production_adopted=False)
    r['post_top2_causal']=dict(scope=scope,actual_sources=sources,commands=jobs)
    seal(r,a.workspace,a.cache,a.out)
    write_json(a.out/'core-safety.private.json',dict(completed=True,kind='current_single_latest_cap_comparison',scope=scope,
        candidate=record(a.out/'receipt.private.json'),original_GPU_and_model_unchanged=True,PS5_operations=0,CI_runs=0))

if __name__=='__main__':main()
