#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compare GPU greedy on the measured submission policy with full-row timings."""
import argparse,json,subprocess,sys
from pathlib import Path
from build_cache_capacity_1125 import literal
from build_next_five_comparison import update_sources
from build_post_top2_submission import gpu_source
from build_speculative_batch_probe import once
from expert_q4 import record,require,write_json
from scoped_native_variant import link,seal
ROOT=Path(__file__).resolve().parents[1]
READBACK=r'''
#include <algorithm>
#include <chrono>
#include <cstdint>
namespace {
std::uint64_t post_large_read[6]{};
struct PostLargeRead{
 const unsigned base;const bool selected;const std::uint64_t began;
 PostLargeRead(bool take,unsigned offset,std::uint64_t bytes):base(offset),selected(take),began(std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now().time_since_epoch()).count()){
  if(selected){++post_large_read[base];post_large_read[base+1]+=bytes;}
 }
 ~PostLargeRead(){if(selected)post_large_read[base+2]+=std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now().time_since_epoch()).count()-began;}
};
}
extern "C" void qwen_post_large_read_stats(std::uint64_t*out){std::copy_n(post_large_read,6,out);}
'''
VALIDATION=r'''
#include <chrono>
#include <cstdint>
extern "C" void qwen_post_large_read_stats(std::uint64_t*);
namespace {
std::uint64_t post_validation_ns=0;
struct PostValidationSpan{
 const std::chrono::steady_clock::time_point start=std::chrono::steady_clock::now();
 ~PostValidationSpan(){post_validation_ns+=std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now()-start).count();}
};
}
'''

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('parent','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();n=json.loads(a.parent.read_text());require('post_top2_GPU_greedy'in n,'Qualified finite/tie-correct GPU greedy parent required');a.out.mkdir(parents=True,exist_ok=False)
 gc=n['io_gpu_comparison']['GPU_command'];s=Path(gc[gc.index('-c')+1]).read_text();s=READBACK+gpu_source(s,40,256,256)
 marker='void ggml_backend_vk_buffer_get_tensor(ggml_backend_buffer_t buffer, const ggml_tensor * tensor, void * data, size_t offset, size_t size) {'
 s=once(s,marker,marker+'\n    PostLargeRead post_large(tensor->type==GGML_TYPE_F32&&tensor->ne[0]==248320,3,size);')
 marker='                                                size_t size, size_t n_copies, size_t stride_tensor, size_t stride_data) {\n    VK_LOG_DEBUG("ggml_backend_vk_get_tensor_2d_async('
 s=once(s,marker,'                                                size_t size, size_t n_copies, size_t stride_tensor, size_t stride_data) {\n    PostLargeRead post_large(tensor->type==GGML_TYPE_F32&&tensor->ne[0]==248320,0,size*n_copies);\n    VK_LOG_DEBUG("ggml_backend_vk_get_tensor_2d_async(')
 ec=n['compile_commands'][0];entry=VALIDATION+Path(ec[ec.index('-c')+1]).read_text();old=n['GDN_model_comparison']['scope'];scope=dict(old,
  candidate='GPU_greedy_common_node256_full_validation_profile',common_submission_node_cap=256,common_flop_divisor=40,
  complete_F32_transport_unchanged=True,full_vocabulary_get_and_validation_host_spans_recorded=True,
  async_get_caller_interval_is_not_GPU_duration=True,extra_GPU_payload_bytes=0)
 entry=once(entry,literal(old),literal(scope));entry=once(entry,'engine->set_logits_observer([&](const float*v,std::size_t count)noexcept{',
  'engine->set_logits_observer([&](const float*v,std::size_t count)noexcept{PostValidationSpan post_validate;')
 marker='            const auto perf=performance_snapshot(*engine);';entry=once(entry,marker,'            const auto validation_before=post_validation_ns;std::uint64_t read_before[6]{};qwen_post_large_read_stats(read_before);\n'+marker)
 marker='            row["phase"]=phase;';entry=once(entry,marker,'            std::uint64_t read_after[6]{};qwen_post_large_read_stats(read_after);for(unsigned i=0;i<6;++i)read_after[i]-=read_before[i];row["full_vocabulary_get_async_sync_calls_bytes_host_ns"]=std::vector<std::uint64_t>(read_after,read_after+6);row["full_F32_validation_host_ns"]=post_validation_ns-validation_before;\n'+marker)
 r,jobs,sources=link(a.parent,a.out,dict(entry=(ec,entry),gpu=(gc,s)),[Path(__file__),ROOT/'tools/build_post_top2_submission.py'])
 update_sources(r,jobs,sources);r['GDN_model_comparison']['scope']=scope;r['next_five_comparison'].update(scope=scope,actual_sources=sources,commands=jobs)
 r['io_gpu_comparison'].update(GPU_command=jobs['gpu'],GPU_source=sources['gpu']);r['post_top2_C1_profile']=dict(scope=scope,actual_sources=sources,commands=jobs)
 seed=a.out/'linked-seed.private.json';write_json(seed,r);subprocess.run([sys.executable,'-X','utf8','-B',str(ROOT/'tools/rebind_gpu_provenance.py'),'--linked',str(seed),'--out',str(a.out/'GPU-provenance')],check=True)
 r=json.loads((a.out/'GPU-provenance/receipt.private.json').read_text());seal(r,a.workspace,a.cache,a.out)
 write_json(a.out/'core-safety.private.json',dict(completed=True,kind='GPU_greedy_and_submission_with_full_validation_costs',candidate=record(a.out/'receipt.private.json'),
  all_full_F32_checks_retained=True,no_extra_GPU_payloads=True,actual_GPU_sampling_counter_preserved=True,PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()
