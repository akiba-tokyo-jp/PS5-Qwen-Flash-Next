#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Relink a finite GDN-only probe without loading model weights or KV state."""
import argparse,json
from pathlib import Path
from build_speculative_batch_probe import once
from expert_q4 import record,write_json
from scoped_native_variant import link,seal

SCOPE=dict(schema='ps5-qwen-GDN-columns-fixture-v1',enabled=True,model_loads=0,
           cases=8,maximum_graphs=320,deadline_seconds=180,
           F64_reference_absolute_limit=1e-6,original_reserves=True,
           automatic_retries=0,production_adoption=False)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('parent','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--split-timing',action='store_true',help='Measure backend/synchronize and completion-check wall separately, retaining both')
    a=p.parse_args();parent=json.loads(a.parent.read_text());a.out.mkdir(parents=True,exist_ok=False)
    command=parent['compile_commands'][0];entry=Path(command[command.index('-c')+1]).read_text()
    header=Path(__file__).resolve().parents[1]/'native/app/gdn_columns_fixture.h'
    headers=[header];scope=dict(SCOPE)
    if a.split_timing:
        text=header.read_text()
        text=once(text,'    double maximum=0;','    double maximum=0,last_backend_us=0,last_checkpoint_us=0;')
        text=once(text,'        ggml_backend_synchronize(backend);checkpoint();++executions;\n        const auto elapsed=std::chrono::duration<double,std::micro>(Clock::now()-start).count();',
            '        ggml_backend_synchronize(backend);const auto backend_end=Clock::now();\n        checkpoint();const auto verified_end=Clock::now();++executions;\n        last_backend_us=std::chrono::duration<double,std::micro>(backend_end-start).count();\n        last_checkpoint_us=std::chrono::duration<double,std::micro>(verified_end-backend_end).count();\n        const auto elapsed=std::chrono::duration<double,std::micro>(verified_end-start).count();')
        text=once(text,'            std::array<double,8> times{};for(auto&time:times)time=compute(arm);check(arm);',
            '            std::array<double,8> times{},backend_times{},checkpoint_times{};\n            for(unsigned i=0;i<8;++i){times[i]=compute(arm);backend_times[i]=last_backend_us;checkpoint_times[i]=last_checkpoint_us;}check(arm);\n            double backend_sum=0,checkpoint_sum=0;for(auto x:backend_times)backend_sum+=x;for(auto x:checkpoint_times)checkpoint_sum+=x;')
        text=once(text,'{{"candidate",arm==1},{"samples_us",times},',
            '{{"backend_samples_us",backend_times},{"checkpoint_samples_us",checkpoint_times},{"backend_mean_us",backend_sum/8},{"checkpoint_mean_us",checkpoint_sum/8},{"candidate",arm==1},{"samples_us",times},')
        generated=a.out/'gdn_columns_timing_fixture.private.h';generated.write_text(text,newline='\n');headers.append(generated)
        scope.update(timing_components=['backend_and_synchronize','positive_completion_check'],all_original_completion_checks_retained=True)
    entry='#include "'+headers[-1].name+'"\n'+entry
    branch='''        if(policy.at("native_GDN_columns_fixture")!=Json::parse(SCOPE_LITERAL))
            throw std::runtime_error("Exact GDN-only fixture scope required");
        qwen_app::enforce_native_model_compute_limits();
        if(qwen_app::native_model_device_stats().live)throw std::runtime_error("Empty GDN fixture ledger required");
        qwen_native_stage("GDN_columns_fixture_started_model_not_loaded");
        auto gdn=qwen_app::gdn_fixture::run(qwen_native_driver_checkpoint,qwen_native_stage,require_model_CPU_budget);
        qwen_app_gdn_trial_release();qwen_native_driver_complete();qwen_app::stop_native_model_sources();
        const auto gdn_ledger=qwen_app::native_model_device_stats();
        if(gdn_ledger.live)throw std::runtime_error("GDN fixture ledger remains live");
        const auto&gdn_owner=policy.at("native_first_generation_validation");
        gdn.update({{"schema","ps5-qwen-GDN-columns-fixture-result-v1"},{"completed",true},
            {"pid",getpid()},{"run_id",gdn_owner.at("run_id")},
            {"candidate_SELF_sha256",gdn_owner.at("candidate_SELF_sha256")},
            {"model_loaded",false},{"requests",Json::array()},{"HTTP_requests",0},{"VideoOut_starts",0},
            {"all_model_source_device_owners_positively_retired",true},
            {"device_ledger_live_bytes",gdn_ledger.live},{"device_ledger_peak_bytes",gdn_ledger.peak},
            {"driver_revision",gdn_owner.at("driver_revision")},{"profile",gdn_owner.at("profile")}});
        write_fresh_report(startup.admission_report,gdn);
        qwen_native_stage("GDN_columns_fixture_completed_waiting_for_ordinary_close");
        for(;;)std::this_thread::sleep_for(std::chrono::seconds(1));
'''.replace('SCOPE_LITERAL',json.dumps(json.dumps(scope,separators=(',',':'))))
    entry=once(entry,'        screen.state="loading original BF16 model";',branch+'        screen.state="loading original BF16 model";')
    result,jobs,sources=link(a.parent,a.out,dict(entry=(command,entry)),[Path(__file__),*headers])
    for key in ('normal_performance','output_Q8_normal','cold_request','resident_all_Q8','resident_cache3072','resident_small_rows','resident_weight_normal','memory_quality_cohort'):
        result[key]['actual_sources'].update(sources);result[key]['commands'].update(jobs)
    result['all_Q2_optimized_monitor']['actual_entry']=sources['entry']
    result['all_Q2_optimized_monitor']['commands'][0]=jobs['entry']
    result['routing_winners_normal']['actual_entry']=sources['entry']
    result['GDN_columns_fixture']=dict(scope=scope,header=record(headers[-1]),model_loads=0,
        GPU_object=parent['lossless_shader_storage']['vulkan_object'],full_model_adoption_enabled=False)
    seal(result,a.workspace,a.cache,a.out)
    write_json(a.out/'core-safety.private.json',dict(completed=True,kind='GDN_only_F64_fixture',
        original_physical_and_kernel_guards_preserved=True,CPU_heap_limit_bytes=512<<20,
        cache_slots=3072,driver_unchanged=True,model_loads=0,
        candidate=record(a.out/'receipt.private.json'),PS5_operations=0,CI_runs=0))

if __name__=='__main__':main()
