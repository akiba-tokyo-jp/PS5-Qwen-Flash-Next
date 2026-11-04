#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build an unloaded native Q2_K/IQ2 component using real-calibrated Up weights."""
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


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','base-entry','samples','out'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--prefill',action='store_true',help='Also qualify widths 30/32 with ten selected physical slots and three replicated real matrices')
    parser.add_argument('--F32-shader-arithmetic',action='store_true',help='Use the existing backend F16-disable option for a distinct numerical profile')
    parser.add_argument('--F16-storage-reference',action='store_true',help='Only new prefill cases: FP16 storage, FP32 accumulation, twelve distinct qualification graphs')
    parser.add_argument('--MMVQ-decode-reference',action='store_true',help='Only twelve new decode graphs, with exact Q8_1 inputs and normal MMVQ enabled')
    args=parser.parse_args();base=load(args.base_entry);samples=load(args.samples)
    need(not args.MMVQ_decode_reference or not (args.prefill or args.F16_storage_reference or args.F32_shader_arithmetic),
         'The MMVQ refinement qualifies only the distinct normal-profile decode path')
    need(not args.F16_storage_reference or (args.prefill and not args.F32_shader_arithmetic),
         'The distinct FP16-storage scope requires prefill and the normal F16 environment')
    need(base['completed'] and base['CPU_minimum_plus_21_unchanged'] and samples['completed'] and
         len(samples['matrices'])==9 and samples['all_nine_Experts_actually_visited'] and not samples['synthetic_uniform_importance_used'],
         'Admitted CPU entry and nine actually calibrated original Up samples are required')
    need(record(samples['pack']['path'])==samples['pack'],'IQ2 component pack changed')
    profile=load(base['application_policy']['path']);need(record(profile['source']['path'])==profile['source'],'Selected base entry changed')
    args.out.mkdir(parents=True,exist_ok=False)
    for header in Path(profile['source']['path']).parent.glob('*.h'):shutil.copyfile(header,args.out/header.name)
    remote='/app0/qwen-runtime/iq2-Up-'+samples['pack']['sha256'][:24]+'.bin'
    widths=([30,32] if args.F16_storage_reference else [1,2,30,32]) if args.prefill else [1,2];cases=3*len(widths)
    graph_bound=(2 if args.F16_storage_reference or args.MMVQ_decode_reference else 12)*cases
    scope=dict(schema='ps5-qwen-calibrated-IQ2-component-v1',model_loads=0,widths=widths,decode_selected_Experts=2,
        prefill_selected_slots=10 if args.prefill else None,prefill_unique_original_Experts_per_layer=3 if args.prefill else None,
        prefill_replicated_weights_explicit=bool(args.prefill),original_Up_matrices=9,groups=3,cases=cases,maximum_GPU_graphs=graph_bound,CPU_deadline_seconds=240,
        formats=['Q2_K','IQ2_XXS'],original_weight_source='BF16',real_PS5_importance=True,
        synthetic_component_inputs=True,component_not_model_speed=True,activation_input_tensor_type='F32',
        vector_MMVQ_disabled=True,larger_width_internal_arithmetic_independently_qualified=False,
        backend_environment=dict(GGML_VK_DISABLE_MMVQ='1',**({'GGML_VK_DISABLE_F16':'1'} if args.F32_shader_arithmetic else {})),
        F32_shader_arithmetic_explicit=args.F32_shader_arithmetic,pack_bytes=samples['pack']['bytes'],pack_sha256=samples['pack']['sha256'],
        HTTP_requests=0,VideoOut_starts=0,automatic_retries=0)
    if args.F16_storage_reference:
        scope.update(qualification_only=True,F16_storage_FP32_accumulation=True,
            reference='F64 of FP16-rounded decoded weights and FP16-exact F32 inputs',
            synthetic_inputs_exactly_FP16=True,unchanged_decode_cases_replayed=0)
    if args.MMVQ_decode_reference:
        scope.update(qualification_only=True,MMVQ_decode_FP32_accumulation=True,
            vector_MMVQ_disabled=False,backend_environment={},
            reference='F64 of decoded weights and exactly Q8_1-representable F32 inputs',
            synthetic_inputs_exactly_Q8_1=True,unchanged_prefill_cases_replayed=0)
    header=args.out/'calibrated_iq2_assets.h';text='#pragma once\n#include <cstdint>\n'
    text+='inline constexpr unsigned iq2_widths[]={'+','.join(map(str,widths))+'};\n'
    text+='inline constexpr const char*iq2_pack_path='+json.dumps(remote)+';\n'
    text+='inline constexpr std::uint64_t iq2_pack_bytes='+str(samples['pack']['bytes'])+'ULL;\n'
    text+='inline constexpr const char*iq2_pack_sha256='+json.dumps(samples['pack']['sha256'])+';\n'
    text+='struct IQ2Part{std::uint64_t offset,bytes;const char*sha256;};\nstruct IQ2Matrix{unsigned layer,expert;IQ2Part encoded[2];};\n'
    text+='inline constexpr IQ2Matrix iq2_matrices[9]={\n'
    for row in samples['matrices']:
        need(row['role']=='up' and row['columns']==2560 and row['rows']==640 and row['actual_activation_samples']>0 and
             row['C_and_Python_IQ2_decode_exact'],'Each fixture weight must have real importance and independently decoded bytes')
        parts=[]
        for label,size in (('Q2_K',537600),('IQ2_XXS',422400)):
            part=row[label];need(part['bytes']==size and part['offset']%16384==0,'Exact component geometry required')
            parts.append('{'+str(part['offset'])+'ULL,'+str(size)+'ULL,'+json.dumps(part['sha256'])+'}')
        text+='{'+str(row['layer'])+','+str(row['expert'])+',{'+','.join(parts)+'}},\n'
    header.write_text(text+'};\n',encoding='utf-8',newline='\n')
    original=Path(profile['source']['path']).read_text(encoding='utf-8')
    text='#include "calibrated_iq2_fixture.h"\n'+original
    marker='        const auto policy = Json::parse(policy_file);'
    text=once(text,marker,marker+'\n        if(policy.at("native_IQ2_fixture")!=Json::parse('+json.dumps(json.dumps(scope,separators=(',',':')))+'))throw std::runtime_error("Exact calibrated IQ2 component scope required");')
    marker='\n        qwen_native_gpu_initialize((startup.admission_report+".driver.log").c_str());\n'
    text=once(text,marker,'\n        if(setenv("GGML_VK_DISABLE_MMVQ","1",1))throw std::runtime_error("F32 component activation policy unavailable");'+marker)
    if args.F32_shader_arithmetic:
        text=once(text,marker,'\n        if(setenv("GGML_VK_DISABLE_F16","1",1))throw std::runtime_error("Explicit component F32 shader profile unavailable");'+marker)
    if args.F16_storage_reference:
        text=once(text,marker,'\n        if(unsetenv("GGML_VK_DISABLE_F16")||getenv("GGML_VK_DISABLE_F16"))throw std::runtime_error("Normal F16 environment required");'+marker)
    if args.MMVQ_decode_reference:
        text=once(text,'if(setenv("GGML_VK_DISABLE_MMVQ","1",1))throw std::runtime_error("F32 component activation policy unavailable");',
                  'if(unsetenv("GGML_VK_DISABLE_MMVQ")||unsetenv("GGML_VK_DISABLE_F16"))throw std::runtime_error("Normal MMVQ profile required");')
    start=text.index(marker)+len(marker);end=text.index('    }catch(const std::exception &e){',start)
    text=text[:start]+'''        qwen_app::enforce_native_model_compute_limits();
        if(qwen_app::native_model_device_stats().live)throw std::runtime_error("Empty IQ2 component device ledger required");
        qwen_native_driver_begin();llama_backend_init();
        const auto component_started_epoch_ms=qwen_app::monitor_clock().now();
        auto component=qwen_app::run_calibrated_iq2_fixture(qwen_native_driver_checkpoint,qwen_native_stage);
        const auto component_completed_epoch_ms=qwen_app::monitor_clock().now();
        component.update({{"started_epoch_ms",component_started_epoch_ms},{"completed_epoch_ms",component_completed_epoch_ms},
            {"clock_calibrated",qwen_app::monitor_clock().calibrated()},
            {"clock_uncertainty_ms",qwen_app::monitor_clock().initial_uncertainty_ms().value_or(5000)}});
        const auto run=policy.at("native_first_generation_validation").at("run_id").get<std::string>();
        component.update({{"pid",getpid()},{"run_id",run},{"candidate_SELF_sha256",policy.at("native_first_generation_validation").at("candidate_SELF_sha256")}});
        write_fresh_report(startup.admission_report+".IQ2-component",component);
        if(!component.at("all_backends_positively_retired").get<bool>()||!component.at("source_descriptor_and_scratch_retired").get<bool>())
            throw std::runtime_error("Positive IQ2 component retirement required");
        qwen_native_driver_complete();
        const auto source=qwen_app::native_model_source_stats();
        if(source.chunks!=source.completed_windows)throw std::runtime_error("Original source windows remain incomplete");
        qwen_app::stop_native_model_sources();const auto ledger=qwen_app::native_model_device_stats();
        if(ledger.live)throw std::runtime_error("IQ2 component device owners remain live");
        struct ps5_heap_stats heap{};ps5_heap_stats(&heap);
        write_fresh_report(startup.admission_report,{{"schema","ps5-qwen-unloaded-IQ2-completion-v1"},{"kind","Q2-IQ2-fixture"},
            {"completed",true},{"pid",getpid()},{"run_id",run},{"candidate_SELF_sha256",policy.at("native_first_generation_validation").at("candidate_SELF_sha256")},
            {"model_receipt_sha256",policy.at("native_first_generation_validation").at("model_receipt_sha256")},
            {"requests",Json::array()},{"model_loads",0},{"HTTP_requests",0},{"VideoOut_starts",0},
            {"component",component},{"source_windows",source.chunks},{"source_completed_windows",source.completed_windows},
            {"all_model_source_device_owners_positively_retired",true},{"device_ledger_live_bytes",ledger.live},
            {"device_ledger_peak_bytes",ledger.peak},{"CPU_heap_peak_bytes",heap.peak_bytes},{"component_not_model_speed",true}});
        qwen_native_stage("resident_additional_completed_waiting_for_ordinary_close");
        for(;;)(void)usleep(1000000);
'''+text[end:]
    for name in ('observed_system_headroom','require_model_CPU_budget','wait_for_initial_model_CPU_budget','model_file_identity','model_directory_identity'):
        need(body(original,name)==body(text,name),'An original model memory or identity guard changed')
    source=args.out/'entry.private.cpp';source.write_text(text,encoding='utf-8',newline='\n')
    command=base['commands'][1].copy();old_view=str(Path(profile['source']['path']).parent);overlay=load(command[command.index('-ivfsoverlay')+1])
    for root in overlay['roots']:root['external-contents']=(args.out/Path(root['external-contents']).name).resolve().as_posix()
    selected=args.out/'selected-view.private.json';save(selected,overlay)
    command=[str(args.out) if v==old_view else v for v in command];command[command.index('-ivfsoverlay')+1]=str(selected)
    obj=args.out/'entry.o';command[command.index('-c')+1]=str(source);command[command.index('-o')+1]=str(obj)
    if '-MF' in command:command[command.index('-MF')+1]=str(args.out/'entry.private.d')
    runtime=args.out/'calibrated_iq2_fixture.cpp';runtime_text=(ROOT/'native/app/calibrated_iq2_fixture.cpp').read_text(encoding='utf-8')
    if args.F32_shader_arithmetic:
        runtime_text=once(runtime_text,'    Pack pack(stage);',
            '    need(getenv("GGML_VK_DISABLE_F16")&&std::strcmp(getenv("GGML_VK_DISABLE_F16"),"1")==0,"Exact F32 shader environment required");\n    Pack pack(stage);')
        runtime_text=once(runtime_text,'{"vector_MMVQ_disabled",true},','{"vector_MMVQ_disabled",true},{"F32_shader_arithmetic_explicit",true},')
    if args.F16_storage_reference or args.MMVQ_decode_reference:
        if args.MMVQ_decode_reference:
            runtime_text=once(runtime_text,
                'float input(unsigned column,unsigned token){return float(int((column+3*token)%13)-6)/1009.0f;}',
                'float input(unsigned column,unsigned token){constexpr int values[13]={-127,-64,-32,-16,-8,-4,0,4,8,16,32,64,127};return float(values[(column+3*token)%13])/1024.0f;}')
            runtime_text=once(runtime_text,
                '    need(checkpoint&&stage&&getenv("GGML_VK_DISABLE_MMVQ")&&std::strcmp(getenv("GGML_VK_DISABLE_MMVQ"),"1")==0,\n         "Explicit original F32 activation policy required before backend creation");',
                '    need(checkpoint&&stage&&!getenv("GGML_VK_DISABLE_MMVQ")&&!getenv("GGML_VK_DISABLE_F16"),\n         "Normal MMVQ environment required before backend creation");')
        else:
            runtime_text=once(runtime_text,
                'float input(unsigned column,unsigned token){return float(int((column+3*token)%13)-6)/1009.0f;}',
                'float input(unsigned column,unsigned token){return ggml_fp16_to_fp32(ggml_fp32_to_fp16(float(int((column+3*token)%13)-6)/1009.0f));}')
        runtime_text=once(runtime_text,
            'outputs[format]=ggml_mul_mat_id(ctx,weights[format],x,ids);ggml_set_output(outputs[format]);',
            'outputs[format]=ggml_mul_mat_id(ctx,weights[format],x,ids);'+('if(format)' if args.MMVQ_decode_reference else '')+'outputs[format]->op_params[0]=int32_t(GGML_PREC_F32);ggml_set_output(outputs[format]);')
        if args.F16_storage_reference:
            runtime_text=once(runtime_text,
                'sums[(expert*640+row)*13+col%13]+=double(decoded[col]);',
                'sums[(expert*640+row)*13+col%13]+=double(ggml_fp16_to_fp32(ggml_fp32_to_fp16(decoded[col])));')
        begin=runtime_text.index('            for(unsigned i=0;i<4&&valid;++i)')
        end=runtime_text.index('            // A returned numerical negative',begin)
        runtime_text=runtime_text[:begin]+'''            for(unsigned format=0;format<2&&valid;++format){
                load(pack,format);compute(format);verify(format);
                arms.push_back({{"format",format?"IQ2_XXS":"Q2_K"},{"qualification_only",true},{"GPU_graphs",1}});
            }
'''+runtime_text[end:]
        runtime_text=once(runtime_text,'{"reference","F64 of each separately decoded format"}',
            '{"reference",'+json.dumps(scope['reference'] if args.MMVQ_decode_reference else
             'F64 of FP16-rounded decoded weights and FP16-exact F32 inputs; FP32 accumulation')+'}')
        runtime_text=once(runtime_text,'{"vector_MMVQ_disabled",true},',
            ('{"vector_MMVQ_disabled",false},{"MMVQ_decode_FP32_accumulation",true},{"synthetic_inputs_exactly_Q8_1",true},' if args.MMVQ_decode_reference else
             '{"vector_MMVQ_disabled",true},{"F16_storage_FP32_accumulation",true},')+'{"qualification_only",true},{"performance_timings_measured",false},')
        if args.F16_storage_reference:
            runtime_text=once(runtime_text,'{"larger_width_internal_arithmetic_independently_qualified",false}',
                '{"larger_width_internal_arithmetic_independently_qualified",valid}')
    runtime.write_text(runtime_text,encoding='utf-8',newline='\n')
    shutil.copyfile(ROOT/'native/app/calibrated_iq2_fixture.h',args.out/'calibrated_iq2_fixture.h')
    sdk=args.workspace/'toolchain/ps5-sdk-radv/ps5-payload-sdk/target/include'
    up=args.current.parent/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569'
    provider=args.out/'calibrated-iq2.o';target=args.workspace/'toolchain/llvm-mingw-20261006-ucrt-x86_64/bin/clang++.exe'
    C=[str(target),'--no-default-config','--target=x86_64-sie-ps5','-nostdinc++','-isystem',str(sdk/'c++/v1'),'-isystem',str(sdk),
        '-std=c++17','-fexceptions','-fcxx-exceptions','-femulated-tls','-fno-stack-protector','-fno-plt','-fPIC','-O2',
        '-ffunction-sections','-fdata-sections','-I',str(args.out),'-I',str(ROOT/'native/app'),'-I',str(up/'ggml/include'),
        '-I',str(up/'ggml/src'),'-I',str(up/'vendor'),'-c',str(runtime),'-o',str(provider)]
    for index,job in enumerate((C,command)):
        result=subprocess.run(job,capture_output=True,timeout=240,env=dict(os.environ,TMP=str(args.out),TEMP=str(args.out)))
        (args.out/(str(index)+'.private.log')).write_bytes(result.stdout+result.stderr)
        need(result.returncode==0,result.stderr.decode(errors='replace')[-5000:])
    policy=dict(completed=True,kind='Q2-IQ2-fixture',entry_artifact=record(obj),source=record(source),token_sync_policy='request_end',
        overrides=dict(profile['overrides'],native_IQ2_fixture=scope),CPU_SELF_provider=profile['CPU_SELF_provider'],
        model_and_GPU_topology_unchanged=False,unloaded_GPU_fixture=True,model_and_GPU_guards_preserved=True,
        component_pack=dict(local=samples['pack'],application_path=remote),native_performance_qualified=False,PS5_operations=0)
    if args.F16_storage_reference or args.MMVQ_decode_reference:
        policy.update(arithmetic_reference_runtime=record(runtime),arithmetic_reference_provider=record(provider))
    path=args.out/'application-policy.private.json';save(path,policy)
    save(args.out/'result.private.json',dict(completed=True,application_policy=record(path),entry=record(obj),reader=base['reader'],
        provider=record(provider),samples=record(args.samples),source=record(source),runtime=record(runtime),header=record(header),
        commands=[C,command],model_loads=0,maximum_GPU_graphs=graph_bound,native_operator_qualified=False,PS5_operations=0,production_adopted=False))
    print(json.dumps(dict(completed=True,target_compiled=True,model_loads=0,maximum_GPU_graphs=graph_bound,PS5_operations=0)))


if __name__=='__main__':main()
