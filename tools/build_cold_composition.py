#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Combine native-tested prefill32/workspace48, indexed policy and streaming."""
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
    for k in ('parent','streaming','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();prior=json.loads(a.parent.read_text());stream=json.loads(a.streaming.read_text())
    require(prior['cold_request']['scope']['mode']=='prefill32_workspace48'and stream['cold_request']['scope']['mode']=='continuous_four_roles','Exact separately tested components required')
    for case in (10870,10910,10930):
        folder=a.cache/f'hardware-first-generation-{case}';r=json.loads((folder/'native-model-terminal.private.json').read_text());close=json.loads((folder/'ordinary-close/complete.private.json').read_text());restore=json.loads((folder/'restored-complete.private.json').read_text())
        require(r['completed']and r['all_model_source_device_owners_positively_retired']and close['normal_OS_close_accepted'],'Positive native component retirement required')
    a.out.mkdir(parents=True,exist_ok=False)
    commands=dict(entry=prior['compile_commands'][0],cache=prior['routing_sharing']['commands'][1],owner=prior['all_Q2_optimized_monitor']['commands'][1])
    stream_owner=stream['all_Q2_optimized_monitor']['commands'][1]
    entry=Path(commands['entry'][commands['entry'].index('-c')+1]).read_text();cache=Path(commands['cache'][commands['cache'].index('-c')+1]).read_text();owner=Path(stream_owner[stream_owner.index('-c')+1]).read_text()
    budget=Path(prior['cold_request']['tightened_workspace_header']['path']);(a.out/'device_buffer_budget.h').write_bytes(budget.read_bytes())
    source_header=Path(stream['cold_request']['source_header']['path']);reader=source_header.read_text()
    # Remove producer CPU admission/identity work from the streaming wait
    # counter. These remain required checks; the ordinary read/copy math stays.
    reader=once(reader,'pending_windows_=count;std::uint64_t consumer_ns=0;','pending_windows_=count;std::uint64_t consumer_ns=0,metadata_ns=0;')
    reader=once(reader,'const auto before=[&](unsigned i){ProfileScope timing(stats_.headroom_ns);','const auto before=[&](unsigned i){ProfileScope metadata(metadata_ns);ProfileScope timing(stats_.headroom_ns);')
    marker='''                if(i>=count||got!=std::int64_t(requests[i].bytes)||ops_.identity(requests[i].fd)!=files_[files[i]].identity)
                    fail("Streaming demand was short or changed source identity");'''
    reader=once(reader,marker,'                {ProfileScope metadata(metadata_ns);\n'+marker+'}\n')
    reader=once(reader,'if(consumed!=count||consumer_ns>total)','if(consumed!=count||consumer_ns>total||metadata_ns>total-consumer_ns)')
    reader=once(reader,'stats_.read_ns+=total-consumer_ns;','stats_.read_ns+=total-consumer_ns-metadata_ns;')
    (a.out/source_header.name).write_text(reader,newline='\n')
    cache=once(cache,'#include <expert_temporal_probation.h>','#include <expert_temporal_probation.h>\n#include "indexed_probation_policy.h"')
    cache=once(cache,'    qwen_app::TemporalProbationPolicy policy;','    qwen_app::IndexedProbationPolicy policy;')
    cache=once(cache,'            key_of[s] = il*n_expert + e;','            if(adaptive)policy.replaced(s,key_of[s],il*n_expert+e);\n            key_of[s] = il*n_expert + e;')
    cache=once(cache,'        g.slru.key_of[slot]=(il+1)*512+expert;','        g.slru.policy.replaced(slot,old,(il+1)*512+expert);\n        g.slru.key_of[slot]=(il+1)*512+expert;')
    cache='#include <cstddef>\nextern "C" bool qwen_app_try_Q2_stream(const void*const*,const std::size_t*,unsigned,void*,void(*)(void*,unsigned,const void*));\n'+cache
    marker='\n        for (size_t ip = 0; ip < l.experts.size(); ++ip) {'
    cache=once(cache,marker,(ROOT/'native/app/streaming_q2_cache.inc').read_text()+'\n'+marker)
    # A finite headless comparison may disable the new path only at an idle
    # source boundary. Normal production starts enabled and exposes no control.
    owner=once(owner,'namespace {std::uint64_t Q2_stream_groups=0,Q2_stream_reads=0;}','namespace {std::uint64_t Q2_stream_groups=0,Q2_stream_reads=0;bool Q2_stream_selected=true;}')
    owner=once(owner,'    if(!Q2_quad_mode)return false;required().require_completed_window();ops.require_metadata_idle();\n    if(!addresses||!sizes',
        '    if(!Q2_quad_mode||!Q2_stream_selected)return false;required().require_completed_window();ops.require_metadata_idle();\n    if(!addresses||!sizes')
    owner+='\nextern "C" void qwen_app_cold_stream_select(bool enabled){required().require_completed_window();ops.require_metadata_idle();Q2_stream_selected=enabled;}\n'
    scope=dict(prior['cold_request']['scope'],mode='prefill32_indexed_streaming',additional_CPU_workers=1,maximum_parallel_source_reads=4,scratch_bytes=8<<20,
        maximum_known_reads_per_group=12,quad_counter_semantics='legacy_four_or_streaming_projection_group',legacy_quad_timing_excludes_streaming_groups=True,
        source_wait_excludes_streaming_consumer_and_producer_metadata=True,indexed_probation_exact_victims=True)
    normal=dict(prior['all_Q2_optimized_monitor']['scope'],additional_source_workers=4)
    entry=once(entry,literal(prior['cold_request']['scope']),literal(scope));entry=once(entry,literal(prior['all_Q2_optimized_monitor']['scope']),literal(normal))
    entry='#include <cstdint>\nextern "C" void qwen_app_Q2_stream_stats(std::uint64_t*);\n'+entry
    entry=once(entry,'            const auto perf=performance_snapshot(*engine);','            std::uint64_t stream_before[2]{};qwen_app_Q2_stream_stats(stream_before);\n            const auto perf=performance_snapshot(*engine);')
    entry=once(entry,'            row["cold_request_timing"]=',
        '            std::uint64_t stream_after[2]{};qwen_app_Q2_stream_stats(stream_after);row["streaming_delivery"]={{"groups",stream_after[0]-stream_before[0]},{"physical_reads",stream_after[1]-stream_before[1]},{"existing_scratch_bytes",8u<<20},{"extra_GPU_buffers",0},{"legacy_quad_timing_excludes_streaming_groups",true},{"producer_metadata_excluded_from_source_wait",true}};\n            row["cold_request_timing"]=')
    actual_sources=dict(entry=entry,cache=cache,owner=owner)
    result,jobs,actual=link(a.parent,a.out,{k:(commands[k],v)for k,v in actual_sources.items()},[Path(__file__),a.streaming,budget,source_header,ROOT/'native/app/indexed_probation_policy.h',ROOT/'native/app/streaming_read_pool.h',ROOT/'native/app/streaming_q2_cache.inc',*a.out.glob('*.h')])
    for key in ('normal_performance','output_Q8_normal'):
        result[key]['actual_sources'].update(actual);result[key]['commands'].update(jobs);result[key]['scope']=normal
    for key in ('all_Q2_optimized_monitor','routing_winners_normal'):result[key].update(scope=normal,actual_entry=actual['entry'])
    result['all_Q2_optimized_monitor']['commands'][0]=jobs['entry'];result['routing_sharing']['scope']=normal
    checks=[]
    original=Path(commands['entry'][commands['entry'].index('-c')+1]).read_text()
    for name in ('observed_system_headroom','require_model_CPU_budget','wait_for_initial_model_CPU_budget','model_file_identity','model_directory_identity','resident_reset_empty_context'):
        require(body(entry,name)==body(original,name),'Original resource/identity guard changed: '+name);checks.append(name)
    for marker in ('qwen_native_driver_complete()','qwen_app::stop_native_model_sources()','qwen_app::admit_native_system_memory()','qwen_app::enforce_native_model_compute_limits()'):
        require(entry.count(marker)==original.count(marker)>0,'Original completion boundary changed');checks.append(marker)
    result['cold_request']=dict(scope=scope,actual_sources=actual,commands=jobs,normal_validation_pending=True,production_adopted=False,original_driver_physical_kernel_heap_ledger_completion_guards=True,
        guard_checks=checks,workspace_bytes=48<<20,device_ledger_cap_bytes=2480332800,source_header=record(a.out/source_header.name),tightened_workspace_header=record(a.out/'device_buffer_budget.h'),native_components=[10870,10910,10930])
    seal(result,a.workspace,a.cache,a.out)
    write_json(a.out/'core-safety.private.json',dict(completed=True,kind='combined_cold_request_guard_audit',driver_and_original_physical_reserves_preserved=True,unchanged_guard_functions=checks,candidate=record(a.out/'receipt.private.json'),PS5_operations=0,CI_runs=0))
    print(json.dumps(dict(built=True,prefill=32,indexed=True,streaming=True,workspace_MiB=48,new_GPU_buffers=0,new_scratch_bytes=0)))
if __name__=='__main__':main()
