#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise actual HC-prefill parallelism after the split-removal null result."""
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
 p.add_argument('--service-mode',type=int,required=True);a=p.parse_args();n=json.loads(a.parent.read_text());a.out.mkdir(parents=True,exist_ok=False);old=n['GDN_model_comparison']['scope'];scope=dict(old,candidate='service-kernel-4-HC-prefill-split-two',control_service_mode=a.service_mode,candidate_service_mode=a.service_mode|64,HC_K_minimum=2048,HC_M_maximum=512,HC_N_range=[16,32],all_existing_workspace_and_device_budgets_preserved=True);ec=n['compile_commands'][0];entry=Path(ec[ec.index('-c')+1]).read_text();entry=once(entry,literal(old),literal(scope));entry=once(entry,'qwen_service::mode=arm?'+str(old['candidate_service_mode'])+':'+str(old['control_service_mode'])+';','qwen_service::mode=arm?'+str(a.service_mode|64)+':'+str(a.service_mode)+';')
 gc=n['io_gpu_comparison']['GPU_command'];gpu=Path(gc[gc.index('-c')+1]).read_text();marker='service_gpu_stats[3]+=split_k;';gpu=once(gpu,marker,'if((qwen_service::mode.load(std::memory_order_relaxed)&64)&&split_k==1&&src0->ne[0]>=2048&&src0->ne[1]<=512&&src1->ne[1]<=32){split_k=2;++service_gpu_stats[6];}'+marker)
 r,jobs,sources=link(a.parent,a.out,dict(entry=(ec,entry),gpu=(gc,gpu)),[Path(__file__),ROOT/'native/app/service_options.h']);update_sources(r,jobs,sources);r['GDN_model_comparison']['scope']=scope;r['next_five_comparison'].update(scope=scope,actual_sources=sources,commands=jobs);r['io_gpu_comparison'].update(GPU_source=sources['gpu'],GPU_command=jobs['gpu']);r['service_GPU']['scope']=scope;r['service_GPU']['actual_sources'].update(sources);r['service_GPU']['commands'].update(jobs);raw=a.out/'linked-seed.private.json';write_json(raw,r);subprocess.run([sys.executable,'-X','utf8','-B',ROOT/'tools/rebind_gpu_provenance.py','--linked',raw,'--out',a.out/'GPU-provenance'],check=True);r=json.loads((a.out/'GPU-provenance/receipt.private.json').read_text());seal(r,a.workspace,a.cache,a.out);write_json(a.out/'core-safety.private.json',dict(completed=True,scope=scope,existing_pipeline_assets_only=True,workspace_and_device_budgets_unchanged=True,positive_completion_and_ownership_preserved=True,PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()
