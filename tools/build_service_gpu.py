#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compare existing HC split-K and Q4 small-row pipeline choices on current PS5."""
import argparse,json,subprocess,sys
from pathlib import Path
from build_cache_capacity_1125 import literal
from build_next_five_comparison import update_sources
from build_speculative_batch_probe import once
from expert_q4 import record,require,write_json
from scoped_native_variant import link,seal
ROOT=Path(__file__).resolve().parents[1]
GPU_PREFIX='''#include <algorithm>
#include <cstring>
#include "service_options.h"
namespace {std::uint64_t service_gpu_stats[8]{};}
extern "C" void qwen_service_gpu_stats(std::uint64_t*out){std::copy_n(service_gpu_stats,8,out);}
'''
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in('parent','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 p.add_argument('--stage',type=int,choices=(4,5),required=True);p.add_argument('--service-mode',type=int,required=True);a=p.parse_args();n=json.loads(a.parent.read_text());a.out.mkdir(parents=True,exist_ok=False);old=n['GDN_model_comparison']['scope'];flag=16 if a.stage==4 else 32;scope=dict(old,candidate='service-kernel-'+str(a.stage),control_service_mode=a.service_mode,candidate_service_mode=a.service_mode|flag,storage_precision_unchanged=True,shader_assets_unchanged=True,cross_arm_full_F32_bit_equality_required=False,independent_candidate_full_F32_SHA256_required=True,candidate_tokens_equal_to_control_required=True)
 ec=n['compile_commands'][0];entry=Path(ec[ec.index('-c')+1]).read_text();entry='#include <cstdint>\nextern "C" {\n#include "hash/sha256/sha256.h"\n}\nextern "C" void qwen_service_gpu_stats(std::uint64_t*);\n'+entry;entry=once(entry,literal(old),literal(scope));entry=once(entry,'qwen_service::mode=arm?'+str(old['candidate_service_mode'])+':'+str(old['control_service_mode'])+';','qwen_service::mode=arm?'+str(a.service_mode|flag)+':'+str(a.service_mode)+';')
 marker='        std::array<std::vector<float>,2>io_reference;';entry=once(entry,marker,'        std::array<std::array<unsigned char,32>,2>candidate_digest{};\n'+marker)
 entry=once(entry,'if(compare&&(io_max_error!=0||bitwise_error))','if(compare&&arm==0&&(io_max_error!=0||bitwise_error))');entry=once(entry,'if(compare&&!same_routes)','if(compare&&arm==0&&!same_routes)')
 marker='            row["service_mode"]=qwen_service::mode.load();';code='''            bool candidate_repeat_exact=false;std::array<unsigned char,32>digest{};
            if(ordinal<10){sha256_t hash;sha256_init(&hash);sha256_update(&hash,reinterpret_cast<const unsigned char*>(io_current.data()),rows*columns*sizeof(float));sha256_final(&hash,digest.data());if(arm==1){if(ordinal<6)candidate_digest[hash_arm]=digest;else{candidate_repeat_exact=digest==candidate_digest[hash_arm]&&completed_route_report(routes.at(ordinal)).at("records")==completed_route_report(routes.at(ordinal-2)).at("records");if(!candidate_repeat_exact)throw std::runtime_error("Independent candidate full F32 or ordered routes differ");}}}
            std::uint64_t service_gpu[8]{};qwen_service_gpu_stats(service_gpu);row["service_GPU_totals"]=std::vector<std::uint64_t>(service_gpu,service_gpu+8);row["candidate_independent_full_F32_and_routes_exact"]=candidate_repeat_exact;row["cross_control_ordered_routes_exact"]=same_routes;
''';entry=once(entry,marker,code+marker)
 gc=n['io_gpu_comparison']['GPU_command'];gpu=Path(gc[gc.index('-c')+1]).read_text();gpu=GPU_PREFIX+gpu
 marker='    const uint32_t split_k = ggml_vk_guess_split_k(ctx, ne01, ne11, ne10, disable_split_k, pipeline);'
 code='''
    if(src0->type==GGML_TYPE_Q8_0&&src1->ne[1]>=16&&(std::strstr(src0->name,"hc_")||std::strstr(dst->name,"hc_"))){++service_gpu_stats[0];service_gpu_stats[2]+=split_k;if((qwen_service::mode.load(std::memory_order_relaxed)&16)&&split_k>1){split_k=1;++service_gpu_stats[1];}service_gpu_stats[3]+=split_k;}
''';gpu=once(gpu,marker,marker.replace('const uint32_t','uint32_t')+code)
 start=gpu.index('static vk_pipeline ggml_vk_get_dequantize_mul_mat_vec(');end=gpu.index('static vk_pipeline ggml_vk_get_dequantize_mul_mat_vec_id(',start);part=gpu[start:end];marker='    if (b_type == GGML_TYPE_Q8_1) {';at=part.rfind(marker);require(at>=0,'Final Q8 input pipeline selection required');part=part[:at]+'''    if(a_type==GGML_TYPE_Q4_0&&num_cols<=4&&m<=8192&&k>=1024){++service_gpu_stats[4];if(qwen_service::mode.load(std::memory_order_relaxed)&32){dmmv_wg=DMMV_WG_SIZE_LARGE;++service_gpu_stats[5];}}
'''+part[at:];gpu=gpu[:start]+part+gpu[end:]
 r,jobs,sources=link(a.parent,a.out,dict(entry=(ec,entry),gpu=(gc+['-I',str(ROOT/'native/app')],gpu)),[Path(__file__),ROOT/'native/app/service_options.h']);update_sources(r,jobs,sources);r['GDN_model_comparison']['scope']=scope;r['next_five_comparison'].update(scope=scope,actual_sources=sources,commands=jobs);r['io_gpu_comparison'].update(GPU_source=sources['gpu'],GPU_command=jobs['gpu']);r['service_GPU']=dict(scope=scope,actual_sources=sources,commands=jobs);raw=a.out/'linked-seed.private.json';write_json(raw,r);subprocess.run([sys.executable,'-X','utf8','-B',ROOT/'tools/rebind_gpu_provenance.py','--linked',raw,'--out',a.out/'GPU-provenance'],check=True);r=json.loads((a.out/'GPU-provenance/receipt.private.json').read_text());seal(r,a.workspace,a.cache,a.out);write_json(a.out/'core-safety.private.json',dict(completed=True,scope=scope,shared_driver_unchanged=True,existing_shader_assets_only=True,all_sync_and_owner_rules_preserved=True,PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()
