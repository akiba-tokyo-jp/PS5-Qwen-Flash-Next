#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Qualify observation on synthetic GPU graphs before loading model weights."""
import argparse,json
from pathlib import Path
from build_speculative_batch_probe import once
from build_cache_capacity_1125 import literal
from scoped_native_variant import link,seal
from expert_q4 import record,write_json
ROOT=Path(__file__).resolve().parents[1]

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('parent','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();n=json.loads(a.parent.read_text());a.out.mkdir(parents=True,exist_ok=False)
 original=ROOT/'native/app/synchronization_fixture.h';text=original.read_text()
 text=once(text,'namespace qwen_app {namespace synchronization_fixture {','extern "C" void qwen_ps5_timing_select(unsigned);\nextern "C" void qwen_ps5_timing_snapshot(std::uint64_t*);\nnamespace qwen_app {namespace synchronization_fixture {')
 text=once(text,'qwen_throughput::mode=base|(candidate?8:0);','qwen_throughput::mode=base;qwen_ps5_timing_select(candidate);std::uint64_t timing_before[48]{};qwen_ps5_timing_snapshot(timing_before);')
 text=once(text,'const auto selected=qwen_throughput::stats[11]-before;','const auto selected=qwen_throughput::stats[11]-before;std::uint64_t timing_after[48]{};qwen_ps5_timing_snapshot(timing_after);Json delta=Json::array();for(unsigned i=0;i<47;++i)delta.push_back(timing_after[i]-timing_before[i]);')
 # The math/readback oracle is unchanged; no WAR-policy experiment is enabled.
 text=once(text,'need(candidate?selected>0:selected==0,"Execution-only barrier fixture path coverage differs");','need(selected==0,"Original synchronization policy must remain active");need(candidate?timing_after[10]>timing_before[10]:timing_after[10]==timing_before[10],"Observation arm submit count differs");')
 text=once(text,'{"mode",base|(candidate?8:0)}','{"mode",base},{"observation_enabled",candidate},{"driver_timing_delta",delta}')
 header=a.out/'observer-fixture.private.h';header.write_text(text,newline='\n')
 scope=dict(schema='ps5-qwen-submission-observer-fixture-v1',model_loads=0,requests=0,GPU_graphs=36,scenarios=3,maximum_seconds=180,observation_arms=[False,True,True,False],all_original_synchronization_and_ownership_preserved=True,HTTP_requests=0,VideoOut_starts=0,CI_runs=0)
 ec=n['compile_commands'][0];entry='#include '+json.dumps(header.resolve().as_posix())+'\n'+Path(ec[ec.index('-c')+1]).read_text();entry=once(entry,literal(n['GDN_model_comparison']['scope']),literal(scope))
 branch='''        qwen_app::enforce_native_model_compute_limits();
        if(qwen_app::native_model_device_stats().live)throw std::runtime_error("Empty observer fixture ledger required");
        qwen_service::mode=69;qwen_frontier::mode=7;
        auto checked=qwen_app::synchronization_fixture::run(5,qwen_native_driver_checkpoint,qwen_native_stage,require_model_CPU_budget);
        qwen_native_driver_complete();qwen_app::stop_native_model_sources();
        const auto live=qwen_app::native_model_device_stats();if(live.live)throw std::runtime_error("Observer fixture ledger remains live");
        const auto&owner=policy.at("native_first_generation_validation");
        checked.update({{"schema","ps5-qwen-submission-observer-fixture-result-v1"},{"completed",true},{"pid",getpid()},
            {"run_id",owner.at("run_id")},{"candidate_SELF_sha256",owner.at("candidate_SELF_sha256")},
            {"model_loaded",false},{"requests",Json::array()},{"HTTP_requests",0},{"VideoOut_starts",0},
            {"all_model_source_device_owners_positively_retired",true},{"all_owners_positively_retired",true},
            {"device_ledger_live_bytes",live.live},{"device_ledger_peak_bytes",live.peak},
            {"driver_revision",owner.at("driver_revision")},{"profile",owner.at("profile")}});
        write_fresh_report(startup.admission_report,checked);qwen_native_stage("submission_fixture_complete_waiting_for_ordinary_close");
        for(;;)std::this_thread::sleep_for(std::chrono::seconds(1));
'''
 entry=once(entry,'        screen.state="loading original BF16 model";',branch+'        screen.state="loading original BF16 model";')
 r,jobs,sources=link(a.parent,a.out,dict(entry=(ec,entry)),[Path(__file__),original,header]);r['GDN_model_comparison']['scope']=scope;r['next_five_comparison']['scope']=scope
 r['submission_fixture']=dict(scope=scope,actual_sources=sources,commands=jobs);seal(r,a.workspace,a.cache,a.out)
 write_json(a.out/'core-safety.private.json',dict(completed=True,scope=scope,host_source_and_link_checks_only=True,model_loads=0,synthetic_full_output_and_canary_oracle=True,positive_retirement_required=True,native_qualification_claimed=False,PS5_operations=0,CI_runs=0))
 print(json.dumps(dict(completed=True,model_loads=0,graphs=36)))
if __name__=='__main__':main()
