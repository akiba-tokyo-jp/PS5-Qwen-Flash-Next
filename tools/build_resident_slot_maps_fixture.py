#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Test dedicated maps, alias rebinding, unchanged reuse and changed entries on GPU."""
import argparse,json
from pathlib import Path
from build_speculative_batch_probe import once
from build_cache_capacity_1125 import literal
from scoped_native_variant import link,seal
from expert_q4 import write_json
ROOT=Path(__file__).resolve().parents[1]

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('parent','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();n=json.loads(a.parent.read_text());a.out.mkdir(parents=True,exist_ok=False)
 scope=dict(schema='ps5-qwen-resident-slot-map-fixture-v1',model_loads=0,requests=0,GPU_graphs=36,scenarios=3,samples_per_arm=3,HTTP_requests=0,VideoOut_starts=0,maximum_seconds=180,all_I32_bytes_and_canaries_exact=True,original_driver_and_shader_objects=True,automatic_retries=0,CI_runs=0)
 ec=n['compile_commands'][0];entry='#include "resident_slot_maps_fixture.h"\n'+Path(ec[ec.index('-c')+1]).read_text();entry=once(entry,literal(n['GDN_model_comparison']['scope']),literal(scope))
 branch='''        qwen_app::enforce_native_model_compute_limits();
        if(qwen_app::native_model_device_stats().live)throw std::runtime_error("Empty slot-map fixture ledger required");
        qwen_service::mode=69;qwen_frontier::mode=7;qwen_load_tail_select(true);
        auto checked=qwen_app::resident_slot_maps_fixture::run(qwen_native_driver_checkpoint,qwen_native_stage,require_model_CPU_budget);
        qwen_native_driver_complete();qwen_app::stop_native_model_sources();
        const auto live=qwen_app::native_model_device_stats();if(live.live)throw std::runtime_error("Slot-map fixture ledger remains live");
        const auto&owner=policy.at("native_first_generation_validation");
        checked.update({{"schema","ps5-qwen-resident-slot-map-fixture-result-v1"},{"pid",getpid()},
            {"run_id",owner.at("run_id")},{"candidate_SELF_sha256",owner.at("candidate_SELF_sha256")},
            {"requests",Json::array()},{"HTTP_requests",0},{"VideoOut_starts",0},
            {"all_model_source_device_owners_positively_retired",true},{"all_owners_positively_retired",true},
            {"device_ledger_live_bytes",live.live},{"device_ledger_peak_bytes",live.peak},
            {"driver_revision",owner.at("driver_revision")},{"profile",owner.at("profile")}});
        write_fresh_report(startup.admission_report,checked);qwen_native_stage("resident_slot_map_fixture_complete_waiting_for_ordinary_close");
        for(;;)std::this_thread::sleep_for(std::chrono::seconds(1));
'''
 entry=once(entry,'        screen.state="loading original BF16 model";',branch+'        screen.state="loading original BF16 model";')
 r,jobs,sources=link(a.parent,a.out,dict(entry=(ec+['-I',str(ROOT/'native/app')],entry)),[Path(__file__),ROOT/'native/app/resident_slot_maps_fixture.h',ROOT/'native/app/resident_slot_maps.h']);r['GDN_model_comparison']['scope']=scope;r['next_five_comparison']['scope']=scope
 r['resident_slot_map_fixture']=dict(scope=scope,actual_sources=sources,commands=jobs);seal(r,a.workspace,a.cache,a.out)
 write_json(a.out/'core-safety.private.json',dict(completed=True,host_source_and_link_checks_only=True,native_qualification_claimed=False,synthetic_maps_only=True,all_original_driver_shaders_weights_and_ownership_guards_preserved=True,PS5_operations=0,CI_runs=0))
 print(json.dumps(dict(completed=True,model_loads=0,GPU_graphs=36)))
if __name__=='__main__':main()
