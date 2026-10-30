#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build producer-only completion delivery against the exact normal control."""
import argparse,json
from pathlib import Path
from build_speculative_batch_probe import once
from expert_q4 import require,record
from scoped_native_variant import link,seal
ROOT=Path(__file__).resolve().parents[1]

def reader_source(text):
    text=once(text,'const std::function<void(unsigned,const void*)>&consume){\n        require_completed_window();if(!read||!consume||(bytes!=537600&&bytes!=460800))return false;',
        '''const std::function<void(unsigned,const void*)>&consume,
            const std::function<std::array<std::int64_t,4>(const std::array<SourceReadRequest,4>&,const std::function<void(unsigned,std::int64_t)>&)>&ready={}){
        require_completed_window();if(!read||!consume||(bytes!=537600&&bytes!=460800))return false;''')
    text=once(text,'        try{std::array<std::int64_t,4>got{};{ProfileScope timing(stats_.read_ns);got=read(requests);}',
        '''        try{std::array<std::int64_t,4>got{};
            if(ready){
                const auto begun=ProfileClock::now();std::uint64_t consumer_ns=0;unsigned delivered=0;
                got=ready(requests,[&](unsigned i,std::int64_t count){
                    if(i>=4||count!=std::int64_t(requests[i].bytes)||ops_.identity(requests[i].fd)!=files_[files[i]].identity)
                        fail("Completion delivery was short or changed identity");
                    const auto start=ProfileClock::now();
                    consume(i,static_cast<unsigned char*>(requests[i].target)+skips[i]);
                    consumer_ns+=profile_elapsed_ns(start);++delivered;
                });
                const auto elapsed=profile_elapsed_ns(begun);
                if(delivered!=4||consumer_ns>elapsed)fail("Completed source timing or delivery did not reconcile");
                stats_.consumer_ns+=consumer_ns;stats_.read_ns+=elapsed-consumer_ns;
            }else{ProfileScope timing(stats_.read_ns);got=read(requests);}''')
    return once(text,'            for(unsigned i=0;i<4;++i)consume(i,static_cast<unsigned char*>(requests[i].target)+skips[i]);completed();return true;',
        '            if(!ready)for(unsigned i=0;i<4;++i)consume(i,static_cast<unsigned char*>(requests[i].target)+skips[i]);completed();return true;')

def owner_source(text):
    text=once(text,'#include <bounded_read_pool.h>','#include <completed_read_pool.h>')
    text=text.replace('qwen_app::BoundedReadPool','qwen_app::CompletedReadPool')
    text=once(text,'Q2_quad_batches=0,Q2_quad_peak=0;','Q2_quad_batches=0,Q2_quad_peak=0,Q2_ready_callbacks=0,Q2_ready_overlaps=0;')
    marker='    std::array<std::int64_t, 2> read_pair('
    at=text.index(marker)
    text=text[:at]+'''    std::array<std::int64_t,4> read_four_ready(const std::array<qwen_app::SourceReadRequest,4>&requests,
            const std::function<void(unsigned,std::int64_t)>&consume){
        if(!Q2_quad_mode||!selected_schedule_||!quad_)throw std::runtime_error("Completed-read owner is not admitted");
        std::array<qwen_app::BoundedReadRequest,4>jobs{};
        for(unsigned i=0;i<4;++i)jobs[i]={requests[i].fd,requests[i].target,requests[i].bytes,requests[i].offset};
        const auto result=quad_->read_each(jobs,[&](unsigned i,std::int64_t n){
            ++Q2_ready_callbacks;if(quad_->inflight())++Q2_ready_overlaps;consume(i,n);
        });Q2_quad_peak=std::max<std::uint64_t>(Q2_quad_peak,quad_->maximum_inflight());return result;
    }
'''+text[at:]
    text=once(text,'[&](unsigned i,const void*p){consume(opaque,i,p);});if(used)++Q2_quad_batches;return used;',
        '[&](unsigned i,const void*p){consume(opaque,i,p);},\n        [&](const auto&r,const auto&consumer){return ops.read_four_ready(r,consumer);});if(used)++Q2_quad_batches;return used;')
    return text+'''
extern "C" void qwen_app_completed_delivery_stats(std::uint64_t*out){
    if(!out)throw std::runtime_error("Missing completion counters");out[0]=Q2_ready_callbacks;out[1]=Q2_ready_overlaps;
}
'''

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('parent','source-header','workspace','cache','out'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();prior=json.loads(a.parent.read_text());a.out.mkdir(parents=True,exist_ok=False)
    header=a.out/'resident-mapped-source.private.h';header.write_text(reader_source(a.source_header.read_text()),newline='\n')
    # The qualified reservation header must precede the repository fallback.
    owner_cmd=prior['all_Q2_optimized_monitor']['commands'][1];oldowner=Path(owner_cmd[owner_cmd.index('-c')+1])
    budget=a.out/'device_buffer_budget.h';budget.write_bytes((oldowner.parent/'device_buffer_budget.h').read_bytes())
    entry_cmd=prior['compile_commands'][0];entry=Path(entry_cmd[entry_cmd.index('-c')+1]).read_text()
    entry='#include <cstdint>\nextern "C" void qwen_app_completed_delivery_stats(std::uint64_t*);\n'+entry
    entry=once(entry,'std::uint64_t io_before[4]{};', 'std::uint64_t ready_before[2]{};qwen_app_completed_delivery_stats(ready_before);\n            std::uint64_t io_before[4]{};')
    entry=once(entry,'            row["io_optimization"]=',
        '''            std::uint64_t ready_after[2]{};qwen_app_completed_delivery_stats(ready_after);
            row["completion_delivery"]={{"callbacks",ready_after[0]-ready_before[0]},{"callbacks_with_other_read_active",ready_after[1]-ready_before[1]},
                {"producer_only",true},{"CPU_read_workers",4},{"maximum_read_lanes",4}};
            row["io_optimization"]=''')
    variants={'entry':(entry_cmd,entry),'owner':(owner_cmd,owner_source(oldowner.read_text()))}
    result,commands,sources=link(a.parent,a.out,variants,[Path(__file__),a.source_header,header,budget,ROOT/'native/app/completed_read_pool.h',ROOT/'native/app/bounded_read_pool.h'])
    for key in ('normal_performance','output_Q8_normal'):
        result[key]['actual_sources'].update(sources);result[key]['commands'].update(commands)
    result['all_Q2_optimized_monitor']['actual_entry']=sources['entry']
    result['routing_winners_normal']['actual_entry']=sources['entry']
    result['completed_delivery']=dict(schema='ps5-qwen-completed-delivery-v1',actual_sources=sources,commands=commands,
        source_header=record(header),parent_header=record(a.source_header),CPU_read_workers=4,additional_CPU_workers=1,
        maximum_read_lanes=4,all_destination_leases_retained_until_drain=True,producer_only_GPU_callbacks=True,
        consumer_time_excluded_from_read_time=True,unchanged_physical_and_device_budgets=True,
        driver_revision='872cc1264ad8ba5d6b888b092968fa5858a38c58',driver_profile='cumulative-idle',native_verification_pending=True)
    seal(result,a.workspace,a.cache,a.out)
    print('Completion delivery built with unchanged GPU archives and original physical guards; native comparison pending.')

if __name__=='__main__':main()
