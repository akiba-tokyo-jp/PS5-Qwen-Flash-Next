#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Stream known Q2 demands across projection roles using four existing leases."""
import argparse,json
from pathlib import Path
from build_speculative_batch_probe import once
from build_cache_capacity_1125 import literal
from expert_q4 import require,record,write_json
from scoped_native_variant import link,seal
from audit_expert_all_q2_safety import body
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('parent','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();prior=json.loads(a.parent.read_text());require(prior['cold_request']['scope']['mode']=='profile','Exact current timing control required');a.out.mkdir(parents=True,exist_ok=False)
    commands=dict(entry=prior['compile_commands'][0],cache=prior['routing_sharing']['commands'][1],owner=prior['all_Q2_optimized_monitor']['commands'][1])
    src={k:Path(c[c.index('-c')+1]).read_text()for k,c in commands.items()}
    owner=src['owner'];owner=once(owner,'#include <bounded_read_pool.h>','#include <streaming_read_pool.h>')
    owner=owner.replace('qwen_app::BoundedReadPool','qwen_app::StreamingReadPool')
    marker='    std::array<std::int64_t,4> read_four('
    at=owner.index(marker)
    owner=owner[:at]+'''    void stream(const std::array<qwen_app::SourceReadRequest,12>&requests,unsigned count,const std::array<void*,4>&leases,
            const std::function<void(unsigned)>&before,const std::function<void(unsigned,const void*,std::int64_t)>&consume){
        if(!Q2_quad_mode||!selected_schedule_||!quad_)throw std::runtime_error("Streaming source owner is not admitted");
        std::array<qwen_app::BoundedReadRequest,12>jobs{};for(unsigned i=0;i<count;++i)jobs[i]={requests[i].fd,nullptr,requests[i].bytes,requests[i].offset};
        quad_->run(jobs.data(),count,leases,before,consume);Q2_quad_peak=std::max<std::uint64_t>(Q2_quad_peak,quad_->maximum_inflight());
    }
'''+owner[at:]
    owner+='''
namespace {std::uint64_t Q2_stream_groups=0,Q2_stream_reads=0;}
extern "C" void qwen_app_Q2_stream_stats(std::uint64_t*out){out[0]=Q2_stream_groups;out[1]=Q2_stream_reads;}
extern "C" bool qwen_app_try_Q2_stream(const void*const*addresses,const std::size_t*sizes,unsigned count,void*opaque,void(*consume)(void*,unsigned,const void*)){
    if(!Q2_quad_mode)return false;required().require_completed_window();ops.require_metadata_idle();
    if(!addresses||!sizes||!opaque||!consume||!count||count>12)throw std::runtime_error("Missing known streaming demand ownership");
    std::array<std::uintptr_t,12>at{};std::array<std::size_t,12>bytes{};for(unsigned i=0;i<count;++i){at[i]=reinterpret_cast<std::uintptr_t>(addresses[i]);bytes[i]=sizes[i];}
    const bool used=required().upload_Q2_stream(at,bytes,count,[&](const auto&r,unsigned n,const auto&leases,const auto&before,const auto&use){ops.stream(r,n,leases,before,use);},
        [&](unsigned i,const void*p){consume(opaque,i,p);});if(used){++Q2_stream_groups;Q2_stream_reads+=count;++Q2_quad_batches;}return used;
}
'''
    # Select the exact compiled source header, rather than the repository's
    # historical reader without the qualified Q2 delivery methods.
    dep=Path(commands['owner'][commands['owner'].index('-c')+1]).with_name('owner.private.d')
    if not dep.exists():dep=Path(prior['source_parent']['path']).parent/'owner.private.d'
    text=dep.read_text().replace('\\\n',' ')
    matches=[x.strip().rstrip('\\')for x in text.split()if x.endswith('/resident-mapped-source.private.h')]
    require(len(set(matches))==1,'One exact selected source-reader header required');parent_header=Path(matches[0])
    source_header=parent_header.read_text();marker='    bool borrowed_window_contains('
    source_header=once(source_header,marker,(ROOT/'native/app/streaming_q2_source.inc').read_text()+'\n'+marker)
    header=a.out/'resident-mapped-source.private.h';header.write_text(source_header,newline='\n')
    cache=src['cache'];cache='#include <cstddef>\nextern "C" bool qwen_app_try_Q2_stream(const void*const*,const std::size_t*,unsigned,void*,void(*)(void*,unsigned,const void*));\n'+cache
    marker='\n        for (size_t ip = 0; ip < l.experts.size(); ++ip) {'
    cache=once(cache,marker,(ROOT/'native/app/streaming_q2_cache.inc').read_text()+'\n'+marker)
    scope=dict(prior['cold_request']['scope'],mode='continuous_four_roles',additional_CPU_workers=1,maximum_parallel_source_reads=4,scratch_bytes=8<<20,
        maximum_known_reads_per_group=12,quad_counter_semantics='legacy_four_or_streaming_projection_group',legacy_quad_timing_excludes_streaming_groups=True)
    normal=dict(prior['all_Q2_optimized_monitor']['scope'],additional_source_workers=4)
    entry=src['entry'];entry=once(entry,literal(prior['cold_request']['scope']),literal(scope));entry=once(entry,literal(prior['all_Q2_optimized_monitor']['scope']),literal(normal))
    entry='#include <cstdint>\nextern "C" void qwen_app_Q2_stream_stats(std::uint64_t*);\n'+entry
    entry=once(entry,'            const auto perf=performance_snapshot(*engine);','            std::uint64_t stream_before[2]{};qwen_app_Q2_stream_stats(stream_before);\n            const auto perf=performance_snapshot(*engine);')
    entry=once(entry,'            row["cold_request_timing"]=',
        '            std::uint64_t stream_after[2]{};qwen_app_Q2_stream_stats(stream_after);row["streaming_delivery"]={{"groups",stream_after[0]-stream_before[0]},{"physical_reads",stream_after[1]-stream_before[1]},{"maximum_inflight",4},{"existing_scratch_bytes",8u<<20},{"extra_GPU_buffers",0},{"legacy_quad_timing_excludes_streaming_groups",true}};\n            row["cold_request_timing"]=')
    sources=dict(entry=entry,cache=cache,owner=owner)
    result,jobs,actual=link(a.parent,a.out,{k:(commands[k],v)for k,v in sources.items()},[Path(__file__),parent_header,header,ROOT/'native/app/streaming_read_pool.h',ROOT/'native/app/streaming_q2_source.inc',ROOT/'native/app/streaming_q2_cache.inc'])
    for key in ('normal_performance','output_Q8_normal'):
        result[key]['actual_sources'].update(actual);result[key]['commands'].update(jobs);result[key]['scope']=normal
    for key in ('all_Q2_optimized_monitor','routing_winners_normal'):
        result[key].update(scope=normal,actual_entry=actual['entry'])
    result['all_Q2_optimized_monitor']['commands'][0]=jobs['entry'];result['routing_sharing']['scope']=normal
    checks=[]
    for name in ('observed_system_headroom','require_model_CPU_budget','wait_for_initial_model_CPU_budget','model_file_identity','model_directory_identity','resident_reset_empty_context'):
        require(body(src['entry'],name)==body(entry,name),'Original identity or memory guard changed: '+name);checks.append(name)
    for marker in ('qwen_native_driver_complete()','qwen_app::stop_native_model_sources()','qwen_app::admit_native_system_memory()','qwen_app::enforce_native_model_compute_limits()'):
        require(entry.count(marker)==src['entry'].count(marker)>0,'Original GPU boundary changed');checks.append(marker)
    result['cold_request']=dict(scope=scope,actual_sources=actual,commands=jobs,normal_validation_pending=True,production_adopted=False,original_driver_physical_kernel_heap_ledger_completion_guards=True,
        guard_checks=checks,source_header=record(header),original_source_header=record(parent_header),maximum_source_lanes=4,CPU_worker_delta=1,new_GPU_buffers=0,new_scratch_bytes=0)
    seal(result,a.workspace,a.cache,a.out)
    write_json(a.out/'core-safety.private.json',dict(completed=True,kind='streaming_known_demand_guard_audit',driver_and_original_physical_reserves_preserved=True,unchanged_guard_functions=checks,candidate=record(a.out/'receipt.private.json'),PS5_operations=0,CI_runs=0))
    print(json.dumps(dict(built=True,known_demands_only=True,source_lanes=4,new_scratch_bytes=0,extra_CPU_workers=1)))
if __name__=='__main__':main()
