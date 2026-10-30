#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build isolated cold-request candidates with bounded aggregate CPU/I/O timing."""
import argparse,json
from pathlib import Path
from build_speculative_batch_probe import once
from build_cache_capacity_1125 import literal
from expert_q4 import require,record,write_json
from scoped_native_variant import link,seal
from audit_expert_all_q2_safety import body
ROOT=Path(__file__).resolve().parents[1]

def timed_pool(text):
    text=once(text,'    void lane() noexcept {','    std::array<std::uint64_t,4>begins_{},ends_{};std::array<std::uint64_t,4>timing_{};std::uint64_t begun_=0;\n    static std::uint64_t stamp(){return std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now().time_since_epoch()).count();}\n    void lane() noexcept {')
    text=once(text,'            std::int64_t result=-1;std::exception_ptr error;','            begins_[index]=stamp();\n            std::int64_t result=-1;std::exception_ptr error;')
    text=once(text,'            active_.fetch_sub(1);lock.lock();','            ends_[index]=stamp();active_.fetch_sub(1);lock.lock();')
    text=once(text,'requests_=requests;results_.fill(-1);','begun_=stamp();requests_=requests;results_.fill(-1);')
    text=once(text,'        pending_=false;','        const auto last=*std::max_element(ends_.begin(),ends_.end());++timing_[0];timing_[2]+=last-begun_;for(unsigned i=0;i<4;++i){timing_[1]+=begins_[i]-begun_;timing_[3]+=last-ends_[i];}\n        pending_=false;')
    return once(text,'    unsigned maximum_inflight()const noexcept','    void timing(std::uint64_t*out){require_completed();std::copy(timing_.begin(),timing_.end(),out);}\n    unsigned maximum_inflight()const noexcept')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('parent','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--mode',choices=('profile','indexed','prefill32'),required=True)
    a=p.parse_args();prior=json.loads(a.parent.read_text());a.out.mkdir(parents=True,exist_ok=False)
    require(prior['shared_cache1381']['active_slots']==1381,'Exact qualified1381 control required')
    commands=dict(entry=prior['compile_commands'][0],cache=prior['routing_sharing']['commands'][1],owner=prior['all_Q2_optimized_monitor']['commands'][1],engine=prior['routing_sharing']['commands'][2])
    src={k:Path(c[c.index('-c')+1]).read_text()for k,c in commands.items()}
    scope=dict(schema='ps5-qwen-cold-request-candidate-v1',mode=a.mode,active_cache_slots=1381,prefill_tokens=32 if a.mode=='prefill32' else 16,
        additional_GPU_operations=0,queue_timing='four_job_dispatch_and_tail_capacity_not_exclusive_wall',source_latency='syscall_inclusive_overlapping_not_raw_SSD',CPU_heap_limit_bytes=512<<20,workspace_limit_bytes=64<<20,
        driver_unchanged=True,persistent_caches=False,automatic_retries=0,production_adopted=False)
    # Require the exact candidate metadata at the original policy parse boundary.
    src['entry']=once(src['entry'],'        const auto policy = Json::parse(policy_file);','        const auto policy = Json::parse(policy_file);\n        if(policy.at("native_cold_request").at("scope")!=Json::parse('+literal(scope)+'))throw std::runtime_error("Exact cold-request candidate required");')
    cache=src['cache'];cache='#include "profile_clock.h"\nnamespace {std::uint64_t cold_plan_ns=0,cold_plan_calls=0;}\nextern "C" void qwen_app_cold_plan_timing(std::uint64_t*out){out[0]=cold_plan_calls;out[1]=cold_plan_ns;}\n'+cache
    cache=once(cache,'        if (!g.slru.plan(il, ids.data(), ids.size(), fills, n_hit)) {','        bool planned=false;{qwen_app::ProfileScope timer(cold_plan_ns);++cold_plan_calls;planned=g.slru.plan(il,ids.data(),ids.size(),fills,n_hit);}\n        if (!planned) {')
    if a.mode=='indexed':
        cache=once(cache,'#include <expert_temporal_probation.h>','#include <expert_temporal_probation.h>\n#include "indexed_probation_policy.h"')
        cache=once(cache,'    qwen_app::TemporalProbationPolicy policy;','    qwen_app::IndexedProbationPolicy policy;')
        cache=once(cache,'            key_of[s] = il*n_expert + e;','            if(adaptive)policy.replaced(s,key_of[s],il*n_expert+e);\n            key_of[s] = il*n_expert + e;')
        cache=once(cache,'        g.slru.key_of[slot]=(il+1)*512+expert;','        g.slru.policy.replaced(slot,old,(il+1)*512+expert);\n        g.slru.key_of[slot]=(il+1)*512+expert;')
    src['cache']=cache
    (a.out/'bounded_read_pool.h').write_text(timed_pool((ROOT/'native/app/bounded_read_pool.h').read_text()),newline='\n')
    owner=once(src['owner'],'    void require_metadata_idle()','    void cold_timing(std::uint64_t*out){if(!quad_)throw std::runtime_error("Missing completed quad owner");quad_->timing(out);}\n    void require_metadata_idle()')
    src['owner']=owner+'\nextern "C" void qwen_app_cold_quad_timing(std::uint64_t*out){ops.cold_timing(out);}\n'
    declarations='#include "source_read_latency.h"\nextern "C" void qwen_app_cold_plan_timing(std::uint64_t*);\nextern "C" void qwen_app_cold_quad_timing(std::uint64_t*);\n'
    src['entry']=declarations+src['entry']
    src['entry']=once(src['entry'],'            const auto perf=performance_snapshot(*engine);','            std::uint64_t cold_plan_before[2]{},cold_quad_before[4]{};qwen_app_cold_plan_timing(cold_plan_before);qwen_app_cold_quad_timing(cold_quad_before);\n            qwen_app::SourceReadLatency::Snapshot cold_reads_before{};qwen_app_source_read_latency(cold_reads_before.data(),cold_reads_before.size());\n            const auto perf=performance_snapshot(*engine);')
    src['entry']=once(src['entry'],'            row["actual_graph_reuses"]=','            std::uint64_t cold_plan_after[2]{},cold_quad_after[4]{};qwen_app_cold_plan_timing(cold_plan_after);qwen_app_cold_quad_timing(cold_quad_after);qwen_app::SourceReadLatency::Snapshot cold_reads_after{};qwen_app_source_read_latency(cold_reads_after.data(),cold_reads_after.size());\n            Json read_delta=Json::array();for(unsigned i=0;i<cold_reads_after.size();++i)read_delta.push_back(cold_reads_after[i]-cold_reads_before[i]);\n            row["cold_request_timing"]={{"plan_calls",cold_plan_after[0]-cold_plan_before[0]},{"plan_wall_ns",cold_plan_after[1]-cold_plan_before[1]},\n                {"quad_batches",cold_quad_after[0]-cold_quad_before[0]},{"quad_dispatch_sum_ns",cold_quad_after[1]-cold_quad_before[1]},{"quad_batch_wall_ns",cold_quad_after[2]-cold_quad_before[2]},{"quad_tail_idle_capacity_ns",cold_quad_after[3]-cold_quad_before[3]},\n                {"read_latency_delta",read_delta},{"read_latency_bin_ns",qwen_app::SourceReadLatency::bin_ns},{"read_latency_overflow_bin",qwen_app::SourceReadLatency::bins-1},{"read_latency_size_bin_bytes",qwen_app::SourceReadLatency::size_bin_bytes},{"read_wall_intervals_overlap",true},{"raw_SSD_latency_claimed",false}};\n            row["actual_graph_reuses"]=')
    if a.mode=='prefill32':
        originals=[prior['all_Q2_optimized_monitor']['scope'],prior['expert_q2_model']['scope'],prior['output_Q8_normal']['probation_scope']]
        updated=[dict(x,prefill_tokens=32)for x in originals]
        for old,new in zip(originals,updated):src['entry']=once(src['entry'],literal(old),literal(new))
        src['entry']=once(src['entry'],'llama_n_batch(context)!=16||','llama_n_batch(context)!=32||')
        src['entry']=once(src['entry'],'p.at("tokens").get<std::uint64_t>() > 16','p.at("tokens").get<std::uint64_t>() > 32')
        src['entry']=once(src['entry'],'prefill_tokens != 4 && prefill_tokens != 16','prefill_tokens != 4 && prefill_tokens != 16 && prefill_tokens != 32')
        src['entry']=once(src['entry'],'engine=std::make_unique<qwen_app::LlamaEngine>(model,context,16);','engine=std::make_unique<qwen_app::LlamaEngine>(model,context,32);')
        src['engine']=once(src['engine'],'tokens != 4 && tokens != 16','tokens != 4 && tokens != 16 && tokens != 32')
        src['engine']=src['engine'].replace('(prefill_tokens_!=4&&prefill_tokens_!=16)','(prefill_tokens_!=4&&prefill_tokens_!=16&&prefill_tokens_!=32)')
        causal=Path(prior['prefill16_normal']['causal_header']['path']).read_text()
        (a.out/'causal_expert_sharing.h').write_text(causal,newline='\n')
        (a.out/'prefill16_policy.h').write_text((ROOT/'native/app/prefill16_policy.h').read_text().replace('width==4||width==16','width==4||width==16||width==32'),newline='\n')
        capture_command=prior['routing_sharing']['commands'][3];capture_path=Path(capture_command[capture_command.index('-c')+1]);header=capture_path.with_name('completed_expert_routes.h')
        (a.out/header.name).write_text(header.read_text().replace('uint16_t,160>','uint16_t,320>'),newline='\n')
        capture=capture_path.read_text();require('tokens>16'in capture or 'tokens > 16'in capture,'Explicit original capture width guard required')
        capture=capture.replace('tokens>16','tokens>32').replace('tokens > 16','tokens > 32')
        src['cache']=src['cache'].replace(',160>',',320>');src['capture']=capture;commands['capture']=capture_command
        for name in ('engine','entry'):src[name]=src[name].replace('Bounded prefill requires 1, 2, 4 or 16 tokens','Bounded prefill requires 1, 2, 4, 16 or 32 tokens')
    else:updated=None;src.pop('engine');commands.pop('engine')
    result,jobs,sources=link(a.parent,a.out,{k:(commands[k],v)for k,v in src.items()},[Path(__file__),ROOT/'native/app/indexed_probation_policy.h',*a.out.glob('*.h')])
    for key in ('normal_performance','output_Q8_normal'):
        result[key]['actual_sources'].update(sources);result[key]['commands'].update(jobs)
    for key in ('all_Q2_optimized_monitor','routing_winners_normal'):
        result[key]['actual_entry']=sources['entry']
    result['all_Q2_optimized_monitor']['commands'][0]=jobs['entry']
    if updated:
        normal,model,probation=updated
        for key in ('normal_performance','output_Q8_normal','routing_sharing','routing_winners_normal'):result[key].update(scope=normal,model_scope=model)
        result['output_Q8_normal']['probation_scope']=probation;result['expert_q2_model']['scope']=model;result['all_Q2_optimized_monitor']['scope']=normal
        result['all_Q2_optimized_monitor'].update(actual_engine=sources['engine']);result['all_Q2_optimized_monitor']['commands'][2]=jobs['engine'];result['routing_sharing']['commands'][3]=jobs['capture']
        result['routing_sharing']['actual_sources']['capture']=sources['capture']
    checks=[]
    original=Path(prior['compile_commands'][0][prior['compile_commands'][0].index('-c')+1]).read_text()
    for name in ('observed_system_headroom','require_model_CPU_budget','wait_for_initial_model_CPU_budget','model_file_identity','model_directory_identity','resident_reset_empty_context'):
        expected=body(original,name)
        if a.mode=='prefill32'and name=='resident_reset_empty_context':expected=expected.replace('llama_n_batch(context)!=16||','llama_n_batch(context)!=32||')
        require(expected==body(src['entry'],name),'Original resource or identity guard changed: '+name);checks.append(name)
    for marker in ('qwen_native_driver_complete()','qwen_app::stop_native_model_sources()','qwen_app::admit_native_system_memory()','qwen_app::enforce_native_model_compute_limits()','if(ledger.live)throw std::runtime_error("Additional model owners remain live")'):
        require(original.count(marker)==src['entry'].count(marker)>0,'Positive completion boundary changed');checks.append(marker)
    result['cold_request']=dict(scope=scope,actual_sources=sources,commands=jobs,normal_validation_pending=True,production_adopted=False,
        original_driver_physical_kernel_heap_ledger_completion_guards=True,guard_checks=checks,profile_overhead_requires_matched_comparison=True)
    seal(result,a.workspace,a.cache,a.out)
    write_json(a.out/'core-safety.private.json',dict(completed=True,kind='cold_request_guard_audit',unchanged_guard_functions=checks,driver_and_original_physical_reserves_preserved=True,candidate=record(a.out/'receipt.private.json'),PS5_operations=0,CI_runs=0))
    print(json.dumps(dict(built=True,mode=a.mode,PS5_operations=0,additional_GPU_operations=0)))
if __name__=='__main__':main()
