#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build owner-context CPU maintenance before any driver/model initialization."""
import argparse,json
from pathlib import Path
from build_next_five_comparison import update_sources
from build_speculative_batch_probe import once
from expert_q4 import record,require,write_json
from scoped_native_variant import link,seal
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in('parent','workspace','cache','archives','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();n=json.loads(a.parent.read_text());m=json.loads(a.archives.read_text());rows=[x for x in m['files']if x['target']['kind']=='closed_display'];require(m['completed']and len(rows)==152,'All152 complete historical display archives required');a.out.mkdir(parents=True,exist_ok=False)
 h='#pragma once\nstruct ClosedDisplay{const char*path;std::uint64_t bytes;const char*sha256;};\ninline constexpr ClosedDisplay closed_display_files[]={\n'
 for x in rows:
  t=x['target'];require(record(x['archive']['path'])==x['archive']and t['path'].startswith('/data/ai/native-moss-image-sft/PPSA99190/qwen-runtime/plan-')and t['path'].endswith('.display.bmp'),'Exact full archived diagnostic bytes required');h+='{'+json.dumps('/app0'+t['path'].split('/PPSA99190',1)[1])+','+str(t['bytes'])+'ULL,'+json.dumps(x['archive']['sha256'])+'},\n'
 header=a.out/'closed-display-plan.private.h';header.write_text(h+'};\n',newline='\n');ec=n['compile_commands'][0];entry='#include "closed_display_retirement.h"\n'+Path(ec[ec.index('-c')+1]).read_text()
 scope=dict(schema='ps5-qwen-closed-display-CPU-app-v1',enabled=True,targets=152,model_loads=0,GPU_initializations=0,permission_or_flag_changes=0,maximum_executions=1,automatic_retries=0)
 branch='''
        if(policy.at("native_closed_display_CPU")!=Json::parse(SCOPE_LITERAL))throw std::runtime_error("Exact archived-display CPU scope required");
        if(policy.at("native_closed_display_CPU").at("enabled").get<bool>()){
        qwen_native_stage("closed_display_CPU_maintenance_started_driver_and_model_not_initialized");
        auto checked=qwen_app::closed_display_retirement::run(require_model_CPU_budget,qwen_native_stage);
        ps5_ai_arena_stats empty_driver{};ps5_ai_arena_snapshot(&empty_driver);
        if(empty_driver.allocation_attempts||empty_driver.live_allocations||empty_driver.reserved_bytes||empty_driver.mapping_uncertain||empty_driver.gpu_fault_retained)
            throw std::runtime_error("CPU display maintenance observed unexpected driver ownership");
        const auto&owner=policy.at("native_first_generation_validation");
        checked.update({{"schema","ps5-qwen-closed-display-CPU-result-v1"},{"pid",getpid()},
            {"run_id",owner.at("run_id")},{"candidate_SELF_sha256",owner.at("candidate_SELF_sha256")},
            {"requests",Json::array()},{"HTTP_requests",0},{"VideoOut_starts",0},
            {"all_model_source_device_owners_positively_retired",true},{"all_owners_positively_retired",true},
            {"device_ledger_live_bytes",0},{"driver_allocation_attempts",empty_driver.allocation_attempts},
            {"driver_revision",owner.at("driver_revision")},{"profile",owner.at("profile")}});
        write_fresh_report(startup.admission_report,checked);qwen_native_stage("closed_display_CPU_maintenance_complete_waiting_for_ordinary_close");
        for(;;)std::this_thread::sleep_for(std::chrono::seconds(1));
        }
'''.replace('SCOPE_LITERAL',json.dumps(json.dumps(scope,separators=(',',':'))))
 entry=once(entry,'        const auto policy = Json::parse(policy_file);','        const auto policy = Json::parse(policy_file);'+branch)
 r,jobs,sources=link(a.parent,a.out,dict(entry=(ec+['-I',str(ROOT/'native/app')],entry)),[Path(__file__),ROOT/'native/app/closed_display_retirement.h',header,a.archives]);update_sources(r,jobs,sources);r['closed_display_CPU_app']=dict(scope=scope,actual_sources=sources,commands=jobs,all_host_archives=record(a.archives));seal(r,a.workspace,a.cache,a.out)
 write_json(a.out/'core-safety.private.json',dict(completed=True,scope=r['closed_display_CPU_app']['scope'],branch_before_all_driver_and_model_initialization=True,exact_current_production_to_be_restored_after_ordinary_close=True,all_full_archives_and_native_hashes_required=True,PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()
