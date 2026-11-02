#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Keep the normal program linked but complete before model/source/GPU startup."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess

from build_performance_quantizer import record
from build_speculative_batch_probe import once
from check_headless_legacy_policy import check as check_legacy_policy
from start_success_route import load,need,save

ROOT=Path(__file__).resolve().parents[1]
BLOCK=r'''
        if(qwen_cpu_startup_memory_only()){
            if(policy.at("native_headless_model_audit")!=Json::parse(SCOPE))
                throw std::runtime_error("Exact CPU startup-memory scope required");
            const auto run=policy.at("native_first_generation_validation").at("run_id").get<std::string>();
            const auto self=bind_resident_main_SELF(policy);
            resident_reuse_sample("CPU_startup_after_legacy_policy");
            struct ps5_heap_stats heap{};ps5_heap_stats(&heap);
            if(heap.libc_fallbacks||heap.peak_bytes>(512ull<<20))throw std::runtime_error("Original CPU heap contract refused");
            const Json audit={{"completed",true},{"kind","CPU-startup-staging-memory"},{"model_loads",0},{"GPU_calls",0},
                {"model_sources_initialized",false},{"source_workers_created",0},{"source_payload_reads",0},
                {"source_descriptor_worker_and_scratch_retired",true},{"device_ledger_initialized",false},
                {"full_original_model_path_linked",true},{"CPU_gate_is_separate_constant_one_provider",true},
                {"main_SELF",self},{"VM",resident_reuse_VM_report()},{"CPU_heap_peak_bytes",heap.peak_bytes},
                {"CPU_heap_mapped_bytes",heap.mapped_bytes},{"CPU_libc_fallbacks",heap.libc_fallbacks},
                {"pid",getpid()},{"run_id",run},{"candidate_SELF_sha256",policy.at("native_first_generation_validation").at("candidate_SELF_sha256")}};
            write_fresh_report(startup.admission_report+".first.start",{{"schema","ps5-qwen-first-generation-start-v1"},
                {"pid",getpid()},{"run_id",run},{"candidate_SELF_sha256",policy.at("native_first_generation_validation").at("candidate_SELF_sha256")},
                {"model_receipt_sha256",policy.at("native_first_generation_validation").at("model_receipt_sha256")},
                {"model_loaded",false},{"Vulkan_initialized",false}});
            write_fresh_report(startup.admission_report+".audit",audit);
            write_fresh_report(startup.admission_report,{{"schema","ps5-qwen-CPU-startup-memory-completion-v1"},{"kind","CPU-startup-staging-memory"},
                {"completed",true},{"pid",getpid()},{"run_id",run},{"candidate_SELF_sha256",policy.at("native_first_generation_validation").at("candidate_SELF_sha256")},
                {"model_receipt_sha256",policy.at("native_first_generation_validation").at("model_receipt_sha256")},
                {"requests",Json::array()},{"model_loads",0},{"HTTP_requests",0},{"VideoOut_starts",0},{"GPU_calls",0},
                {"audit",audit},{"source_windows",0},{"source_completed_windows",0},{"model_sources_initialized",false},
                {"all_model_source_device_owners_positively_retired",true},{"device_ledger_live_bytes",0},
                {"device_ledger_initialized",false},{"application_GPU_buffers_created",0},
                {"device_ledger_peak_bytes",0},{"CPU_heap_peak_bytes",heap.peak_bytes}});
            qwen_native_stage("CPU_startup_memory_completed_waiting_for_ordinary_close");
            for(;;)(void)usleep(1000000);
        }
'''


def frame(tools,obj):
    raw=subprocess.check_output([str(tools/'llvm-objdump.exe'),'-d','--section=.text.main','--stop-address=80',str(obj)],text=True)
    found=re.search(r'subq\s+\$0x([0-9a-f]+), %rsp',raw)
    need(found is not None,'Actual main stack allocation must be observed');return int(found[1],16),raw


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','out'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--passive-SELF-settle',action='store_true')
    p.add_argument('--original-reader-after-publication',type=Path)
    a=p.parse_args();base_path=a.current/'provenance/selected-entry-build.private.json';base=load(base_path)
    need(not (a.passive_SELF_settle and a.original_reader_after_publication),'CPU startup reader scopes must be exclusive')
    profile=load(base['application_policy']['path']);need(base['completed'] and base['CPU_minimum_plus_21_unchanged'] and
        base['model_GPU_memory_and_completion_guards_unchanged'] and base['full_SELF_hash_identity_EOF_requirements_preserved'],
        'Canonical selected entry, complete SELF verification and all original guards required')
    for row in (base['entry'],base['reader'],profile['source'],base['application_policy']):need(record(row['path'])==row,'Canonical selected provider changed')
    a.out.mkdir(parents=True,exist_ok=False)
    scope=dict(schema='ps5-qwen-CPU-startup-staging-memory-v1',kind='CPU-startup-staging-memory',requests=0,model_loads=0,GPU_calls=0,
        HTTP_requests=0,VideoOut_starts=0,early_return_before_model_source_initialization=True,source_workers_created=0,source_payload_reads=0,
        full_original_model_path_linked=True,separate_non_LTO_gate_always_one=True,complete_after_CXX_SELF_SHA_identity_EOF_unchanged=True,
        Direct_capacity_recovery_query=False,model_launch_admission_granted=False)
    reader=base['reader'];settle=None
    if a.original_reader_after_publication:
        published=load(a.original_reader_after_publication)
        need(published['completed'] and published['all_current_seven_payloads_identical_and_natively_hashed'] and
            published['prior_complete1527_asset382_lookup_CPU_content_proof_preserved'] and published['all108_PC_whole_SHA_values_unchanged'] and
            published['title_launches']==published['GPU_calls']==published['initializer_requests']==0,
            'A positively completed identical selected-file publication is required')
        scope.update(original_selected_64KiB_reader_after_identical_publication=True,passive_before_SELF_settle=False,
            original_reader_floor_and_30_second_total_deadline_unchanged=True)
    if a.passive_SELF_settle:
        from cpu_startup_settle import build as build_settle
        settle=build_settle(a.workspace,base,a.out);reader=settle['artifact']
        scope.update(passive_before_SELF_settle=True,maximum_passive_ms=5000,additional_pre_read_working_pages=1152,
            original_reader_floor_and_30_second_total_deadline_unchanged=True)
    declaration='extern "C" int qwen_cpu_startup_memory_only();\n'
    original=Path(profile['source']['path']).read_text(encoding='utf-8');marker='        qwen_app::require_first_generation_policy(policy,false);'
    block=BLOCK.replace('SCOPE',json.dumps(json.dumps(scope,separators=(',',':'))))
    text=declaration+once(original,marker,marker+block)
    need(text.removeprefix(declaration).replace(marker+block,marker,1)==original,'Entire original entry must remain byte-identical after removing the inserted CPU block')
    source=a.out/'entry.private.cpp';source.write_text(text,encoding='utf-8',newline='\n');entry=a.out/'entry.o'
    command=base['commands'][1].copy();need(command[command.index('-c')+1]==profile['source']['path'],'Exact canonical entry compiler required')
    command[1:1]=['-I',str(Path(profile['source']['path']).parent)]
    command[command.index('-c')+1]=str(source);command[command.index('-o')+1]=str(entry)
    if '-MF' in command:command[command.index('-MF')+1]=str(a.out/'entry.private.d')
    need(not any('flto' in arg for arg in command),'Opaque CPU gate must not be folded across providers')
    compiler=a.workspace/'toolchain/llvm-mingw-20261006-ucrt-x86_64/bin';provider=a.out/'CPU-startup-gate.o';gate=ROOT/'native/app/cpu_startup_memory_only.c'
    need(gate.read_text(encoding='utf-8').count('int qwen_cpu_startup_memory_only(void) { return 1; }')==1,'One unconditional CPU-only gate required')
    tc=[str(compiler/'clang.exe'),'--no-default-config','--target=x86_64-sie-ps5','-std=c11','-fno-stack-protector','-fno-plt','-fPIC','-O2',
        '-ffunction-sections','-fdata-sections','-Wall','-Wextra','-Werror','-c',str(gate),'-o',str(provider)]
    legacy=check_legacy_policy(a.workspace,a.current,Path(command[command.index('-ivfsoverlay')+1]),a.out/'legacy-policy-host-check')
    for index,job in enumerate((tc,command)):
        run=subprocess.run(job,capture_output=True,timeout=240,env=dict(os.environ,TMP=str(a.out),TEMP=str(a.out)))
        (a.out/(str(index)+'.private.log')).write_bytes(run.stdout+run.stderr);need(run.returncode==0,run.stderr.decode(errors='replace')[-3000:])
    imports=subprocess.check_output([str(compiler/'llvm-nm.exe'),'--undefined-only',str(provider)],text=True);need(not imports.strip(),'The constant CPU gate may import nothing')
    disassembly=subprocess.check_output([str(compiler/'llvm-objdump.exe'),'-d',str(provider)],text=True)
    need(re.search(r'movl\s+\$0x1, %eax',disassembly) and 'retq' in disassembly,'Actual target gate must return constant one')
    (a.out/'CPU-gate-disassembly.private.txt').write_text(disassembly,encoding='utf-8')
    before,old_frame=frame(compiler,base['entry']['path']);after,new_frame=frame(compiler,entry)
    need(after>=before,'CPU measurement must not shrink the normal main stack reservation')
    (a.out/'main-frame-comparison.private.txt').write_text(old_frame+'\n'+new_frame,encoding='utf-8')
    application=dict(profile,kind='headless-model-audit',entry_artifact=record(entry),source=record(source),
        overrides=dict(profile['overrides'],native_headless_model_audit=scope),model_and_GPU_topology_unchanged=False,
        headless_model_audit=True,unloaded_CPU_fixture=True,model_and_GPU_guards_preserved=True,
        headless_audit_kind=scope['kind'],headless_requests=0,actual_legacy_policy_validator_passed=True,legacy_policy_host_check=legacy,
        native_performance_qualified=False,production_adopted=False)
    application.update(CPU_startup_gate_source=record(gate),CPU_startup_gate_provider=record(provider),CPU_startup_original_entry=profile['source'])
    if a.original_reader_after_publication:application['CPU_startup_identical_publication']=record(a.original_reader_after_publication)
    if settle:application['CPU_SELF_provider']=dict(profile['CPU_SELF_provider'],source=settle['source'],artifact=reader,startup_settle=settle)
    policy=a.out/'application-policy.private.json';save(policy,application)
    save(a.out/'result.private.json',dict(completed=True,application_policy=record(policy),entry=record(entry),reader=reader,startup_settle=settle,
        source=record(source),provider=record(provider),inputs=[record(gate),record(Path(__file__)),base['application_policy'],profile['source']],
        commands=[tc,command],canonical_entry=record(base_path),original_main_stack_bytes=before,candidate_main_stack_bytes=after,
        entire_original_entry_retained=True,whole_SELF_reader_unchanged=settle is None,whole_SELF_SHA_identity_EOF_and_floor_unchanged=True,constant_gate_has_no_imports=True,
        required_link_flags=['--undefined='+name for name in ('qwen_driver_table_storage','Q2_bundle_expected_identity','Q2_extra_expected_identity','Q2_current_expected_identity')],
        model_loads=0,GPU_calls=0,source_workers_created=0,PS5_operations=0,production_adopted=False))
    print(json.dumps(dict(completed=True,target_compiled=True,original_main_stack_bytes=before,candidate_main_stack_bytes=after,model_loads=0,GPU_calls=0,PS5_operations=0)))


if __name__=='__main__':main()
