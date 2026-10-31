#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Test routing reduction inside the faster-TTFT Q4/3712 memory composition."""
import argparse,json
from pathlib import Path
from build_next_five_comparison import update_sources
from build_cache_capacity_1125 import literal
from build_speculative_batch_probe import once
from expert_q4 import require,record,write_json
from scoped_native_variant import link,seal

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('parent','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 p.add_argument('--experts',type=int,choices=(2,4),default=4)
 a=p.parse_args();n=json.loads(a.parent.read_text());a.out.mkdir(parents=True,exist_ok=False);ec=n['compile_commands'][0];entry=Path(ec[ec.index('-c')+1]).read_text();old=n['GDN_model_comparison']['scope'];require(old['physical_cache_planes']==3713,'Measured3713-plane Q4 parent required');variant=2 if a.experts==2 else 1
 scope=dict(old,candidate='Q4-cache3712-Top'+str(a.experts),candidate_id=variant,active_cache_slots=[3712,3712],control_Experts=6,candidate_Experts=a.experts,cache_capacity_identical_in_both_arms=True)
 entry=once(entry,literal(old),literal(scope));entry=once(entry,'qwen_next_select(0);','qwen_next_select(arm?'+str(variant)+':0);');entry=once(entry,'qwen_app_select_output_Q8_slots(arm?3712:3072);','qwen_app_select_output_Q8_slots(3712);')
 entry=once(entry,'arm==0?"Q4-cache3072":"Q4-cache3712";','arm==0?"Q4-cache3712-Top6":"Q4-cache3712-Top'+str(a.experts)+'";');entry=once(entry,'{"active_slots",i<10&&(i/2==2||i/2==3)||i>=10?3712:3072}','{"active_slots",3712}')
 r,jobs,sources=link(a.parent,a.out,dict(entry=(ec,entry)),[Path(__file__)]);update_sources(r,jobs,sources);r['GDN_model_comparison']['scope']=scope;r['next_five_comparison'].update(scope=scope,actual_sources=sources,commands=jobs)
 seal(r,a.workspace,a.cache,a.out);write_json(a.out/'core-safety.private.json',dict(completed=True,kind='Q4_cache3712_routing_combination',scope=scope,candidate=record(a.out/'receipt.private.json'),PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()
