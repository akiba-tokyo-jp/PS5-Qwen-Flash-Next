#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compare bounded, owned secondary command reuse for fixed resident decode projections."""
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
 p.add_argument('--base-frontier-mode',type=int,required=True);a=p.parse_args();n=json.loads(a.parent.read_text());a.out.mkdir(parents=True,exist_ok=False)
 old=n['GDN_model_comparison']['scope'];scope=dict(old,candidate='frontier-4-static-resident-secondary-commands',control_frontier_mode=a.base_frontier_mode,candidate_frontier_mode=a.base_frontier_mode|16,command_cache_entries=256,separate_owned_descriptor_sets=True,all_barriers_and_completion_waits_preserved=True)
 ec=n['compile_commands'][0];entry=Path(ec[ec.index('-c')+1]).read_text();entry='#include <cstdint>\nextern "C" void qwen_frontier_command_stats(std::uint64_t*);\n'+entry;entry=once(entry,literal(old),literal(scope));entry=once(entry,'qwen_frontier::mode=arm?'+str(old['candidate_frontier_mode'])+':'+str(old['control_frontier_mode'])+';','qwen_frontier::mode=arm?'+str(a.base_frontier_mode|16)+':'+str(a.base_frontier_mode)+';');entry=once(entry,'if(compare&&arm==0&&(io_max_error!=0||bitwise_error))','if(compare&&(io_max_error!=0||bitwise_error))');entry=once(entry,'if(compare&&arm==0&&!same_routes)','if(compare&&!same_routes)')
 marker='            row["service_mode"]=qwen_service::mode.load();';entry=once(entry,marker,'            std::uint64_t commands[8]{};qwen_frontier_command_stats(commands);row["frontier_command_totals"]=std::vector<std::uint64_t>(commands,commands+8);\n'+marker)
 gc=n['io_gpu_comparison']['GPU_command'];gpu=Path(gc[gc.index('-c')+1]).read_text();gpu=once(gpu,'#include "ggml-vulkan-common.h"','#include "ggml-vulkan-common.h"\n#include "frontier_command_cache.inc"');a0=gpu.index('void ggml_vk_mul_mat(');b=gpu.index('    VK_LOG_DEBUG(',a0);gpu=gpu[:b]+'    FrontierCommandScope command_scope(src1->ne[1]==1 && src0->buffer && ggml_backend_buffer_get_usage(src0->buffer)==GGML_BACKEND_BUFFER_USAGE_WEIGHTS && src0->name[0] && !std::strstr(src0->name,"exps"));\n'+gpu[b:]
 a0=gpu.index('void ggml_vk_synchronize(');b=gpu.index('\n}',a0);gpu=gpu[:b]+'\n    frontier_retire_stale_tapes(ctx);'+gpu[b:]
 a0=gpu.index('void ggml_vk_cleanup(');b=gpu.index('    ggml_vk_synchronize(ctx);',a0)+len('    ggml_vk_synchronize(ctx);');gpu=gpu[:b]+'\n    frontier_clear_tapes(ctx);'+gpu[b:]
 r,jobs,sources=link(a.parent,a.out,dict(entry=(ec,entry),gpu=(gc,gpu)),[Path(__file__),ROOT/'native/app/frontier_options.h',ROOT/'native/app/command_cache_key.h',ROOT/'native/app/frontier_command_cache.inc']);update_sources(r,jobs,sources);r['GDN_model_comparison']['scope']=scope;r['next_five_comparison'].update(scope=scope,actual_sources=sources,commands=jobs);r['io_gpu_comparison'].update(GPU_source=sources['gpu'],GPU_command=jobs['gpu']);r['service_GPU']['actual_sources'].update(sources);r['service_GPU']['commands'].update(jobs);r['frontier'].update(scope=scope);r['frontier']['actual_sources'].update(sources);r['frontier']['commands'].update(jobs)
 raw=a.out/'linked-seed.private.json';write_json(raw,r);subprocess.run([sys.executable,'-X','utf8','-B',ROOT/'tools/rebind_gpu_provenance.py','--linked',raw,'--out',a.out/'GPU-provenance'],check=True);r=json.loads((a.out/'GPU-provenance/receipt.private.json').read_text());seal(r,a.workspace,a.cache,a.out);write_json(a.out/'core-safety.private.json',dict(completed=True,scope=scope,shared_driver_unchanged=True,all_barriers_and_positive_completion_preserved=True,descriptor_sets_owned_until_positive_cleanup=True,no_inflight_eviction=True,PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()
