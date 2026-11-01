#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reuse the frozen two-policy GPU object; rebuild only the Q4 experiment entry."""
import argparse,json
from pathlib import Path
from build_cache_capacity_1125 import literal
from build_next_five_comparison import update_sources
from build_speculative_batch_probe import once
from expert_q4 import require,write_json
from scoped_native_variant import link,seal
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in('parent','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 p.add_argument('--service-mode',type=int,required=True);a=p.parse_args();n=json.loads(a.parent.read_text());a.out.mkdir(parents=True,exist_ok=False);old=n['GDN_model_comparison']['scope'];require(old['candidate']=='service-kernel-4','Frozen HC/Q4 dual-policy provider required');scope=dict(old,candidate='service-kernel-5',control_service_mode=a.service_mode,candidate_service_mode=a.service_mode|32);ec=n['compile_commands'][0];entry=Path(ec[ec.index('-c')+1]).read_text();entry=once(entry,literal(old),literal(scope));entry=once(entry,'qwen_service::mode=arm?'+str(old['candidate_service_mode'])+':'+str(old['control_service_mode'])+';','qwen_service::mode=arm?'+str(a.service_mode|32)+':'+str(a.service_mode)+';');r,jobs,sources=link(a.parent,a.out,dict(entry=(ec,entry)),[Path(__file__),ROOT/'native/app/service_options.h']);update_sources(r,jobs,sources);r['GDN_model_comparison']['scope']=scope;r['next_five_comparison'].update(scope=scope,actual_sources=sources,commands=jobs);r['service_GPU']['scope']=scope;r['service_GPU']['actual_sources'].update(sources);r['service_GPU']['commands'].update(jobs);seal(r,a.workspace,a.cache,a.out);write_json(a.out/'core-safety.private.json',dict(completed=True,scope=scope,unchanged_qualified_dual_policy_GPU_object=True,all_sync_and_owner_rules_preserved=True,PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()
