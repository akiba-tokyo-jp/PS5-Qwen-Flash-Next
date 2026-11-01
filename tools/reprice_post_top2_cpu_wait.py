#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Allow bounded recovery of a valid unchanged pre-GPU CPU-integrity floor."""
import argparse,json
from pathlib import Path
from build_cache_capacity_1125 import recipes
from build_speculative_batch_probe import once
from expert_q4 import record,require,write_json
from scoped_native_variant import link,seal

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('parent','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();n=json.loads(a.parent.read_text());a.out.mkdir(parents=True,exist_ok=False)
 selected={c[c.index('-o')+1]:c for c in recipes(n)if '-c'in c and '-o'in c and c[c.index('-o')+1]in n['link_command']}
 candidates=[c for c in selected.values()if 'int qwen_resident_hash_SELF_at_main_entry(void)'in Path(c[c.index('-c')+1]).read_text()]
 extra=[]
 if not candidates:
  source=Path(n['resident_main_SELF']['pure_C_source']['path']);origin=source.parent/'receipt.private.json';base=json.loads(origin.read_text())
  candidates=[c for c in base['compile_commands']if '-c'in c and c[c.index('-c')+1]==str(source)and c[c.index('-o')+1]in n['link_command']];extra=[origin,source]
 require(len(candidates)==1,'One actually linked pure-C main-SELF provider required');c=candidates[0].copy();s=Path(c[c.index('-c')+1]).read_text();c[1:1]=['-x','c']
 s=once(s,'static int sample(void){','static int current_observation_valid;\nstatic int sample_once(void){\n    current_observation_valid=0;')
 s=once(s,'result.free_after=free;return free>=result.selected_floor;','result.free_after=free;current_observation_valid=1;return free>=result.selected_floor;')
 anchor='static int identity(int fd,uint64_t out[10]){'
 s=once(s,anchor,'''static int sample(void){
    const uint64_t began=now();if(!began)return 0;
    if(sample_once())return 1;
    if(!current_observation_valid)return 0;
    qwen_native_stage("main_SELF_valid_low_free_CPU_observation_bounded_wait GPU_calls=0 floor_unchanged=1 maximum_wait_ms=5000");
    for(unsigned observed=0;observed<500;++observed){
        const uint64_t stamp=now();if(!stamp||stamp<began||stamp-began>=UINT64_C(5000000000))return 0;
        struct timespec delay={0,10000000};if(nanosleep(&delay,NULL))return 0;
        if(sample_once()){
            qwen_native_stage("main_SELF_CPU_floor_recovered_within_bound GPU_calls=0 floor_unchanged=1");return 1;
        }
        if(!current_observation_valid)return 0;
    }
    return 0;
}
'''+anchor)
 r,jobs,sources=link(a.parent,a.out,dict(cpu_integrity=(c,s)),[Path(__file__),*extra])
 r['resident_main_SELF']['pure_C_source']=sources['cpu_integrity'];r['resident_main_SELF']['command']=jobs['cpu_integrity']
 r['post_top2_CPU_integrity_wait']=dict(scope=dict(valid_current_OS_observations_only=True,unchanged_CPU_floor='OS_minimum_plus21',
  maximum_wait_milliseconds=5000,poll_milliseconds=10,maximum_samples=500,whole_SELF_SHA_and_identity_and_EOF_preserved=True,
  original_30_second_read_deadline_preserved=True,invalid_observations_fail_closed=True,GPU_calls_before_integrity=0),actual_sources=sources,commands=jobs)
 seal(r,a.workspace,a.cache,a.out)
 write_json(a.out/'core-safety.private.json',dict(completed=True,kind='bounded_recovery_of_same_preGPU_CPU_floor',candidate=record(a.out/'receipt.private.json'),
  no_threshold_reduction=True,no_extra_GPU_calls_or_buffers=True,known_returned_reads_only=True,PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()
