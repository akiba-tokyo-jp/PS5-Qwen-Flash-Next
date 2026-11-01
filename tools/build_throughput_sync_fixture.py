#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Put the standalone synthetic synchronization oracle before model loading."""
import argparse,json
from pathlib import Path
from build_next_five_comparison import update_sources
from build_cache_capacity_1125 import literal
from build_speculative_batch_probe import once
from expert_q4 import record,write_json
from scoped_native_variant import link,seal
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in('parent','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 p.add_argument('--base-throughput-mode',type=int,default=0);a=p.parse_args();n=json.loads(a.parent.read_text());a.out.mkdir(parents=True,exist_ok=False)
 old=n['GDN_model_comparison']['scope'];scope=dict(schema='ps5-qwen-throughput-sync-fixture-v1',model_loads=0,requests=0,GPU_graphs=36,scenarios=3,modes=[a.base_throughput_mode,a.base_throughput_mode|8,a.base_throughput_mode|8,a.base_throughput_mode],samples_per_arm=3,maximum_seconds=180,complete_F32_bytes_and_canaries_exact=True,independent_pending_write_followed_by_RAW=True,WAW_and_transfer_controls=True,original_physical_OS_and_positive_completion=True,HTTP_requests=0,VideoOut_starts=0,automatic_retries=0,CI_runs=0)
 ec=n['compile_commands'][0];entry='#include "synchronization_fixture.h"\n'+Path(ec[ec.index('-c')+1]).read_text();entry=once(entry,literal(old),literal(scope))
 branch='''        qwen_app::enforce_native_model_compute_limits();
        if(qwen_app::native_model_device_stats().live)throw std::runtime_error("Empty synchronization fixture ledger required");
        qwen_service::mode=69;qwen_frontier::mode=7;
        qwen_native_stage("synchronization_fixture_started_model_not_loaded");
        auto checked=qwen_app::synchronization_fixture::run(BASE_MODE,qwen_native_driver_checkpoint,qwen_native_stage,require_model_CPU_budget);
        qwen_native_driver_complete();qwen_app::stop_native_model_sources();
        const auto live=qwen_app::native_model_device_stats();if(live.live)throw std::runtime_error("Synchronization fixture device ledger remains live");
        const auto&owner=policy.at("native_first_generation_validation");
        checked.update({{"schema","ps5-qwen-throughput-sync-fixture-result-v1"},{"completed",true},{"pid",getpid()},
            {"run_id",owner.at("run_id")},{"candidate_SELF_sha256",owner.at("candidate_SELF_sha256")},
            {"model_loaded",false},{"requests",Json::array()},{"HTTP_requests",0},{"VideoOut_starts",0},
            {"all_model_source_device_owners_positively_retired",true},{"all_owners_positively_retired",true},
            {"device_ledger_live_bytes",live.live},{"device_ledger_peak_bytes",live.peak},
            {"driver_revision",owner.at("driver_revision")},{"profile",owner.at("profile")}});
        write_fresh_report(startup.admission_report,checked);qwen_native_stage("synchronization_fixture_complete_waiting_for_ordinary_close");
        for(;;)std::this_thread::sleep_for(std::chrono::seconds(1));
'''.replace('BASE_MODE',str(a.base_throughput_mode))
 entry=once(entry,'        screen.state="loading original BF16 model";',branch+'        screen.state="loading original BF16 model";')
 r,jobs,sources=link(a.parent,a.out,dict(entry=(ec,entry)),[Path(__file__),ROOT/'native/app/synchronization_fixture.h',ROOT/'native/app/throughput_options.h']);update_sources(r,jobs,sources)
 r['GDN_model_comparison']['scope']=scope;r['next_five_comparison'].update(scope=scope,actual_sources=sources,commands=jobs);r['throughput_sync_fixture']=dict(scope=scope,actual_sources=sources,commands=jobs,actual_GPU_provider=n['lossless_shader_storage']['vulkan_object']);seal(r,a.workspace,a.cache,a.out)
 write_json(a.out/'core-safety.private.json',dict(completed=True,scope=scope,model_loads=0,synthetic_inputs_only=True,complete_GPU_bytes_and_guard_regions_checked=True,original_device_budget_completion_and_ordinary_close=True,PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()
