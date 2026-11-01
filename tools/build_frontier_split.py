#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Measure HC split-K 4 or 8 against the qualified shape-limited split-K 2."""
import argparse,json,subprocess,sys
from pathlib import Path
from build_cache_capacity_1125 import literal
from build_next_five_comparison import update_sources
from build_speculative_batch_probe import once
from expert_q4 import write_json
from scoped_native_variant import link,seal
ROOT=Path(__file__).resolve().parents[1]

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in('parent','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 p.add_argument('--reuse-gpu',action='store_true');p.add_argument('--split',type=int,choices=[4,8],required=True);p.add_argument('--base-frontier-mode',type=int,required=True);a=p.parse_args();n=json.loads(a.parent.read_text());a.out.mkdir(parents=True,exist_ok=False)
 old=n['GDN_model_comparison']['scope'];bit=4 if a.split==4 else 8;scope=dict(old,candidate='frontier-3-HC-split-'+str(a.split),control_frontier_mode=a.base_frontier_mode,candidate_frontier_mode=a.base_frontier_mode|bit,HC_split_K_control=2,HC_split_K_candidate=a.split)
 ec=n['compile_commands'][0];entry=Path(ec[ec.index('-c')+1]).read_text();entry=once(entry,literal(old),literal(scope));entry=once(entry,'qwen_frontier::mode=arm?'+str(old['candidate_frontier_mode'])+':'+str(old['control_frontier_mode'])+';','qwen_frontier::mode=arm?'+str(a.base_frontier_mode|bit)+':'+str(a.base_frontier_mode)+';')
 gc=n['io_gpu_comparison']['GPU_command'];gpu=Path(gc[gc.index('-c')+1]).read_text();gpu=('#include "frontier_options.h"\n'+gpu)if not a.reuse_gpu else gpu
 gpu=gpu if a.reuse_gpu else once(gpu,'{split_k=2;++service_gpu_stats[6];}','{const auto frontier=qwen_frontier::mode.load(std::memory_order_relaxed);split_k=(frontier&8)?8:((frontier&4)?4:2);++service_gpu_stats[6];}')
 r,jobs,sources=link(a.parent,a.out,dict(entry=(ec,entry),**({}if a.reuse_gpu else dict(gpu=(gc,gpu)))),[Path(__file__),ROOT/'native/app/frontier_options.h']);update_sources(r,jobs,sources);r['GDN_model_comparison']['scope']=scope;r['next_five_comparison'].update(scope=scope,actual_sources=sources,commands=jobs);r['io_gpu_comparison'].update(GPU_source=sources.get('gpu',n['io_gpu_comparison']['GPU_source']),GPU_command=jobs.get('gpu',gc));r['service_GPU']['actual_sources'].update(sources);r['service_GPU']['commands'].update(jobs);r['frontier'].update(scope=scope);r['frontier']['actual_sources'].update(sources);r['frontier']['commands'].update(jobs)
 raw=a.out/'linked-seed.private.json';write_json(raw,r);subprocess.run([sys.executable,'-X','utf8','-B',ROOT/'tools/rebind_gpu_provenance.py','--linked',raw,'--out',a.out/'GPU-provenance'],check=True);r=json.loads((a.out/'GPU-provenance/receipt.private.json').read_text());seal(r,a.workspace,a.cache,a.out);write_json(a.out/'core-safety.private.json',dict(completed=True,scope=scope,existing_pipeline_assets_only=True,workspace_and_device_budgets_unchanged=True,positive_completion_and_owner_validation_preserved=True,PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()
