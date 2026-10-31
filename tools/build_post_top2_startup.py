#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Replace the unconditional settle interval with bounded observed admission."""
import argparse,json
from pathlib import Path
from build_speculative_batch_probe import once
from expert_q4 import record,require,write_json
from scoped_native_variant import link,seal
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('parent','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--observations',type=Path,nargs='+',required=True);a=p.parse_args()
    observed=[]
    for path in a.observations:
        r=json.loads(path.read_text());s=r['samples']
        require(r['completed']and len(s)==51 and len({x['Flexible_available_bytes']for x in s})==1,'Complete existing settle observations required')
        observed.append(max(x['kernel_free_pages']for x in s)-min(x['kernel_free_pages']for x in s))
    delta=max(observed);require(delta<=1,'This candidate is bound to the current one-page observation variation')
    n=json.loads(a.parent.read_text());a.out.mkdir(parents=True,exist_ok=False)
    ec=n['compile_commands'][0];source=Path(ec[ec.index('-c')+1]);entry=source.read_text()
    old='''        Json settle=Json::array();
        for(unsigned i=0;i<51;++i) {
            const auto m=qwen_app::admit_native_system_memory();
            settle.push_back({{"ordinal",i},{"kernel_free_pages",m.kernel_free},{"Flexible_available_bytes",m.flexible_available}});
            if(i!=50&&usleep(100000))throw std::runtime_error("Startup settle interval did not return");
        }'''
    new='''        Json settle=Json::array();bool post_settle_quiet=false;
        std::uint64_t post_previous_free=0,post_previous_flexible=0;
        for(unsigned i=0;i<51;++i) {
            const auto m=qwen_app::admit_native_system_memory();
            settle.push_back({{"ordinal",i},{"kernel_free_pages",m.kernel_free},{"Flexible_available_bytes",m.flexible_available}});
            if(i){const auto delta=m.kernel_free>post_previous_free?m.kernel_free-post_previous_free:post_previous_free-m.kernel_free;
                post_settle_quiet=delta<=1&&m.flexible_available==post_previous_flexible;
                if(post_settle_quiet)break;}
            post_previous_free=m.kernel_free;post_previous_flexible=m.flexible_available;
            if(i!=50&&usleep(100000))throw std::runtime_error("Startup settle interval did not return");
        }'''
    entry=once(entry,old,new)
    entry=once(entry,'{"GPU_calls",0},{"IO_payload_reads",0},{"kernel_reclaim_calls",0},{"inactive_pages_counted_as_available",false}});',
        '{"condition_based",true},{"two_admitted_observations_quiet",post_settle_quiet},{"maximum_observation_count",51},'+
        '{"GPU_calls",0},{"IO_payload_reads",0},{"kernel_reclaim_calls",0},{"inactive_pages_counted_as_available",false}});')
    r,jobs,sources=link(a.parent,a.out,dict(entry=(ec,entry)),[Path(__file__),*a.observations])
    for k,v in r.items():
        if isinstance(v,dict)and isinstance(v.get('actual_sources'),dict)and 'entry'in v['actual_sources']:
            v['actual_sources']['entry']=sources['entry']
            if isinstance(v.get('commands'),dict)and 'entry'in v['commands']:v['commands']['entry']=jobs['entry']
    r['all_Q2_optimized_monitor']['actual_entry']=sources['entry'];r['all_Q2_optimized_monitor']['commands'][0]=jobs['entry']
    r['routing_winners_normal']['actual_entry']=sources['entry']
    r['post_top2_startup']=dict(scope=dict(schema='ps5-qwen-observed-startup-v1',minimum_observations=2,
        maximum_observations=51,pause_us=100000,observed_kernel_variation_pages=delta,
        all_original_physical_and_kernel_predicates_preserved=True,early_exit_requires_two_admitted_observations=True,
        unchanged_five_second_maximum_fallback=True,claim_is_startup_latency_not_decode_speed=True),
        original_entry=record(source),observations=[record(x)for x in a.observations],actual_sources=sources,commands=jobs,native_pending=True)
    seal(r,a.workspace,a.cache,a.out)
    write_json(a.out/'core-safety.private.json',dict(completed=True,kind='observed_startup_settle',candidate=record(a.out/'receipt.private.json'),
        original_GPU_driver_weights_and_model_operation_counts_unchanged=True,additional_native_API_calls=False,PS5_operations=0,CI_runs=0))

if __name__=='__main__':main()
