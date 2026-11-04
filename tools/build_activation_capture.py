#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build a bounded real-activation diagnostic from the admitted current entry."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess

from audit_expert_all_q2_safety import body
from build_performance_quantizer import record
from build_speculative_batch_probe import once
from start_success_route import load,need,save

ROOT=Path(__file__).resolve().parents[1]
SCOPE=dict(schema='ps5-qwen-real-activation-capture-v1',request_ordinal=0,layers=48,
    maximum_evaluations=33,maximum_tokens_per_evaluation=32,maximum_selected_Experts=10,
    scratch_bytes=4<<20,maximum_file_bytes=256<<20,original_Expert_IDs_before_slot_remapping=True,
    actual_indexed_matmul_operands=True,timings_usable_for_performance=False,
    capture_state_allocation='tracked_heap_after_context_admission',
    additional_weight_quantization=False,automatic_retries=0)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','base-entry','out'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--headless',action='store_true',help='Capture one completed counting request without API, display or a33-row reference copy')
    args=parser.parse_args();base=load(args.base_entry)
    need(base['completed'] and base['CPU_minimum_plus_21_unchanged'],'Admitted smaller CPU SELF source required')
    profile=load(base['application_policy']['path'])
    for row in (base['application_policy'],base['entry'],base['reader'],profile['source']):
        need(record(row['path'])==row,'Actual admitted entry or reader changed')
    args.out.mkdir(parents=True,exist_ok=False)
    scope_contract=dict(SCOPE,headless=bool(args.headless),maximum_requests=1 if args.headless else 3,
                        HTTP_requests=0 if args.headless else 2,VideoOut_starts=0 if args.headless else 1)
    for header in Path(profile['source']['path']).parent.glob('*.h'):shutil.copyfile(header,args.out/header.name)
    original=Path(profile['source']['path']).read_text(encoding='utf-8');text='#include "activation_capture_runtime.h"\n'+original
    marker='        const auto policy = Json::parse(policy_file);'
    scope=json.dumps(json.dumps(scope_contract,separators=(',',':')))
    text=once(text,marker,marker+'\n        if(policy.at("native_activation_capture")!=Json::parse('+scope+'))throw std::runtime_error("Exact real activation diagnostic required");')
    marker='        const auto run=policy.at("native_first_generation_validation").at("run_id").get<std::string>();'
    text=once(text,marker,marker+'\n        require_model_CPU_budget();\n'
        '        qwen_app::prepare_activation_capture(startup.admission_report+".activation-samples.bin",Json{{"run_id",run},'
        '{"candidate_SELF_sha256",policy.at("native_first_generation_validation").at("candidate_SELF_sha256")},'
        '{"model_receipt_sha256",policy.at("native_first_generation_validation").at("model_receipt_sha256")},'
        '{"pid",getpid()},{"scope",policy.at("native_activation_capture")}});\n        require_model_CPU_budget();')
    text=once(text,'            const auto &result=trial.run(request,[&](const auto &bound){',
        '            qwen_app::activation_capture_request(ordinal);\n            const auto &result=trial.run(request,[&](const auto &bound){')
    text=once(text,'            },observed_inference_stage);','            },observed_inference_stage);\n            qwen_app::activation_capture_request(1);')
    marker='        if(ledger.live)throw std::runtime_error("Additional model owners remain live");'
    text=once(text,marker,marker+'\n        write_fresh_report(startup.admission_report+".activation-capture",qwen_app::finish_activation_capture());')
    if args.headless:
        text=once(text,'        const unsigned request_count=3;','        const unsigned request_count=1;')
        text=once(text,'        std::vector<float> reference_logits(resident_reference_rows*columns);','        // Calibration scans each existing row without retaining33 full rows.')
        start=text.index('            engine->set_logits_observer([&](const float*v,std::size_t count)noexcept{')
        end=text.index('            qwen_app::CausalExpertSharingEngine causal',start)
        text=text[:start]+'''            engine->set_logits_observer([&](const float*v,std::size_t count)noexcept{
                qwen_load::CpuSpan measured(qwen_load::full_validation);
                if(!v||count!=columns||rows>=resident_reference_rows){geometry_error=true;return;}
                for(std::size_t i=0;i<count;++i)if(!std::isfinite(v[i]))value_error=true;
                ++rows;if(!ordinal)++reference_rows;
            });
'''+text[end:]
        start=text.index('                if(ordinal){\n                    Json event')
        end=text.index('            },observed_inference_stage);',start)
        text=text[:start]+text[end:]
        start=text.index('            if(ordinal){\n                if(!result.metrics.decode_tokens_per_second')
        end=text.index('            return row;',start)
        text=text[:start]+text[end:]
        start=text.index('        qwen_app::HardwareInfo hardware;',text.index('        run_all_Q2_request(0,'))
        cleanup=text.index('        qwen_app_complete_predictive_expert();qwen_native_driver_begin();',start)
        text=text[:start]+text[cleanup:]
        start=text.index('        write_fresh_report(startup.admission_report,{{"scheduler_slot_map_counts"',start)
        end=text.index('        qwen_native_stage("resident_additional_completed_waiting_for_ordinary_close");',start)
        text=text[:start]+'''        write_fresh_report(startup.admission_report,{{"schema","ps5-qwen-headless-activation-completion-v1"},
            {"kind","Q2-headless-calibration"},{"completed",true},{"pid",getpid()},{"run_id",run},
            {"candidate_SELF_sha256",policy.at("native_first_generation_validation").at("candidate_SELF_sha256")},
            {"model_receipt_sha256",policy.at("native_first_generation_validation").at("model_receipt_sha256")},
            {"requests",completed},{"model_loads",1},{"HTTP_requests",0},{"VideoOut_starts",0},
            {"source_windows",source.chunks},{"source_completed_windows",source.completed_windows},
            {"all_model_source_device_owners_positively_retired",true},{"device_ledger_live_bytes",ledger.live},
            {"device_ledger_peak_bytes",ledger.peak},{"CPU_heap_peak_bytes",heap.peak_bytes},
            {"timings_usable_for_performance",false},{"prefix_or_causal_sharing_exercised",false}});
'''+text[end:]
    for name in ('observed_system_headroom','require_model_CPU_budget','wait_for_initial_model_CPU_budget',
                 'model_file_identity','model_directory_identity','resident_reset_empty_context'):
        need(body(original,name)==body(text,name),'An original memory, identity or reset guard changed')
    source=args.out/'entry.private.cpp';source.write_text(text,encoding='utf-8',newline='\n')
    command=base['commands'][1].copy();old_view=str(Path(profile['source']['path']).parent)
    overlay=load(command[command.index('-ivfsoverlay')+1])
    for root in overlay['roots']:root['external-contents']=(args.out/Path(root['external-contents']).name).resolve().as_posix()
    selected=args.out/'selected-view.private.json';save(selected,overlay)
    command=[str(args.out) if v==old_view else v for v in command];command[command.index('-ivfsoverlay')+1]=str(selected)
    obj=args.out/'entry.o';command[command.index('-c')+1]=str(source);command[command.index('-o')+1]=str(obj)
    if '-MF' in command:command[command.index('-MF')+1]=str(args.out/'entry.private.d')
    sdk=args.workspace/'toolchain/ps5-sdk-radv/ps5-payload-sdk/target/include'
    up=args.current.parent/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569'
    target=args.workspace/'toolchain/llvm-mingw-20261006-ucrt-x86_64/bin/clang++.exe'
    for name in ('activation_capture.h','activation_capture_runtime.h','activation_capture_runtime.cpp'):
        shutil.copyfile(ROOT/'native/app'/name,args.out/name)
    runtime=args.out/'activation_capture_runtime.cpp';provider=args.out/'activation-capture.o'
    C=[str(target),'--no-default-config','--target=x86_64-sie-ps5','-nostdinc++','-isystem',str(sdk/'c++/v1'),'-isystem',str(sdk),
        '-std=c++17','-fexceptions','-fcxx-exceptions','-femulated-tls','-fno-stack-protector','-fno-plt','-fPIC','-O2',
        '-ffunction-sections','-fdata-sections','-I',str(args.out),'-I',str(ROOT/'native/app'),'-I',str(up/'ggml/include'),'-I',str(up/'vendor'),
        '-c',str(runtime),'-o',str(provider)]
    host=args.workspace/'toolchain/msys-clang64/clang64/bin/clang++.exe';test=args.out/'activation-check.exe'
    commands=[[str(host),'-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'native/app'),'-I',str(up/'ggml/include'),
               str(ROOT/'tests/activation_capture_test.cpp'),'-o',str(test)],[str(test)],C,command]
    for index,job in enumerate(commands):
        result=subprocess.run(job,capture_output=True,timeout=240,env=dict(os.environ,PATH=str(host.parent)+os.pathsep+os.environ.get('PATH',''),TMP=str(args.out),TEMP=str(args.out)))
        (args.out/(str(index)+'.private.log')).write_bytes(result.stdout+result.stderr)
        need(result.returncode==0,result.stderr.decode(errors='replace')[-5000:])
    application=dict(completed=True,kind='Q2-calibration',entry_artifact=record(obj),source=record(source),token_sync_policy='request_end',
        overrides=dict(profile['overrides'],native_activation_capture=scope_contract),CPU_SELF_provider=profile['CPU_SELF_provider'],
        model_and_GPU_topology_unchanged=not args.headless,headless_calibration=bool(args.headless),model_and_GPU_guards_preserved=True,
        diagnostic_scheduler_splits_added=True,timings_usable_for_performance=False,
        native_performance_qualified=False,PS5_operations=0)
    path=args.out/'application-policy.private.json';save(path,application)
    report=dict(completed=True,application_policy=record(path),entry=record(obj),reader=base['reader'],provider=record(provider),
        commands=commands,inputs=[record(args.out/p) for p in ('activation_capture.h','activation_capture_runtime.h','activation_capture_runtime.cpp')],
        host_noncontiguous_original_ID_slot_mapping_and_returned_failure_controls_passed=True,
        original_memory_identity_reset_and_GPU_ownership_guards_preserved=True,
        link_flags=['--wrap=ggml_backend_sched_set_eval_callback','--wrap=ggml_backend_sched_graph_compute_async'],
        native_capture_qualified=False,PS5_operations=0,production_adopted=False)
    save(args.out/'result.private.json',report)
    print(json.dumps(dict(completed=True,target_compiled=True,host_callback_controls_passed=True,PS5_operations=0)))


if __name__=='__main__':main()
