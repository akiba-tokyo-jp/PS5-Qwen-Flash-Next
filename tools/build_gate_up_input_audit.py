#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Observe Gate/Up logical operand identity without altering GGML operations."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

from audit_expert_all_q2_safety import body
from build_performance_quantizer import record
from build_speculative_batch_probe import once
from headless_current_entry import headless_entry
from start_success_route import load,need,save

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','base-entry','graph','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();base=load(a.base_entry);graph=load(a.graph);profile=load(base['application_policy']['path'])
    need(base['completed'] and base['CPU_minimum_plus_21_unchanged'] and graph['selected_object_byte_exact'],
         'Actual selected entry/reader and byte-exact graph source required')
    for row in (profile['source'],base['entry'],base['reader'],graph['source'],graph['artifact']):need(record(row['path'])==row,'Selected source or artifact changed')
    retained=load(a.current/'provenance/retained-relink-inputs.private.json')
    actual=next(r for r in retained if Path(r['original_path']).name=='graph.o')
    need(all(actual[k]==graph['artifact'][k] for k in ('bytes','sha256')),'The reconstructed graph must still be the selected provider')
    a.out.mkdir(parents=True,exist_ok=False)
    for header in Path(profile['source']['path']).parent.glob('*.h'):shutil.copyfile(header,a.out/header.name)
    for name in ('gate_up_input_audit.h','gate_up_input_audit.cpp'):shutil.copyfile(ROOT/'native/app'/name,a.out/name)
    original_graph=Path(graph['source']['path']).read_text(encoding='utf-8')
    text='struct ggml_tensor;\nextern "C" void qwen_observe_gate_up_inputs(const ggml_tensor*,const ggml_tensor*,int) noexcept;\n'+original_graph
    marker='        up = build_lora_mm_id(up_exps, cur, selected_experts, up_exps_s, slots);'
    text=once(text,marker,marker+'\n        ggml_tensor *const observed_up=up;')
    marker='            cur = build_lora_mm_id(gate_exps, cur, selected_experts, gate_exps_s, slots);'
    text=once(text,marker,marker+'\n            qwen_observe_gate_up_inputs(observed_up,cur,il);')
    operations=lambda source:re.findall(r'\b(ggml_[A-Za-z0-9_]+)\s*\(',source)
    need(operations(original_graph)==operations(text),'No GGML operation may be inserted, removed or reordered')
    graph_source=a.out/'graph.private.cpp';graph_source.write_text(text,encoding='utf-8',newline='\n')
    graph_obj=a.out/'graph.o';gc=graph['command'].copy();gc[gc.index('-c')+1]=str(graph_source);gc[gc.index('-o')+1]=str(graph_obj)
    if '-MF'in gc:gc[gc.index('-MF')+1]=str(a.out/'graph.private.d')
    original=Path(profile['source']['path']).read_text(encoding='utf-8')
    contract=dict(schema='ps5-qwen-headless-model-audit-v1',kind='Gate-Up-input-audit',requests=3,model_loads=1,
        HTTP_requests=0,VideoOut_starts=0,tensor_values_read=0,retained_tensor_pointers=0,graph_operations_added=0,
        GPU_calls_added=0,scheduler_splits_added=0,calibration_value_streams_added=0,performance_timings_usable=False)
    entry='#include "gate_up_input_audit.h"\n'+original
    marker='        const auto policy = Json::parse(policy_file);'
    entry=once(entry,marker,marker+'\n        if(policy.at("native_headless_model_audit")!=Json::parse('+json.dumps(json.dumps(contract,separators=(',',':')))+'))throw std::runtime_error("Exact Gate/Up input identity scope required");')
    entry=headless_entry(entry,contract['kind'],3,'qwen_app::gate_up_input_audit_report()')
    for name in ('observed_system_headroom','require_model_CPU_budget','wait_for_initial_model_CPU_budget',
                 'model_file_identity','model_directory_identity','resident_reset_empty_context'):
        need(body(original,name)==body(entry,name),'An original memory, identity or reset guard changed')
    source=a.out/'entry.private.cpp';source.write_text(entry,encoding='utf-8',newline='\n');obj=a.out/'entry.o'
    ec=base['commands'][1].copy();old_view=str(Path(profile['source']['path']).parent)
    overlay=load(ec[ec.index('-ivfsoverlay')+1])
    for root in overlay['roots']:root['external-contents']=(a.out/Path(root['external-contents']).name).resolve().as_posix()
    selected=a.out/'selected-view.private.json';save(selected,overlay)
    ec=[str(a.out) if x==old_view else x for x in ec];ec[ec.index('-ivfsoverlay')+1]=str(selected)
    ec[ec.index('-c')+1]=str(source);ec[ec.index('-o')+1]=str(obj)
    if '-MF'in ec:ec[ec.index('-MF')+1]=str(a.out/'entry.private.d')
    up=a.current.parent/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569';sdk=a.workspace/'toolchain/ps5-sdk-radv/ps5-payload-sdk/target/include'
    target=a.workspace/'toolchain/llvm-mingw-20261006-ucrt-x86_64/bin/clang++.exe';provider=a.out/'gate-up-input-audit.o'
    tc=[str(target),'--no-default-config','--target=x86_64-sie-ps5','-nostdinc++','-isystem',str(sdk/'c++/v1'),'-isystem',str(sdk),
        '-std=c++17','-fexceptions','-fcxx-exceptions','-femulated-tls','-fno-stack-protector','-fno-plt','-fPIC','-O2',
        '-ffunction-sections','-fdata-sections','-I',str(a.out),'-I',str(up/'ggml/include'),'-I',str(up/'vendor'),
        '-c',str(a.out/'gate_up_input_audit.cpp'),'-o',str(provider)]
    host=a.workspace/'toolchain/msys-clang64/clang64/bin';test=a.out/'gate-input-test.exe'
    hc=[str(host/'clang++.exe'),'-std=c++17','-O2','-I',str(ROOT/'native/app'),'-I',str(up/'ggml/include'),'-I',str(up/'vendor'),
        str(ROOT/'tests/gate_up_input_audit_test.cpp'),'-o',str(test)]
    env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''),TMP=str(a.out),TEMP=str(a.out));commands=[hc,[str(test)],tc,gc,ec]
    for i,job in enumerate(commands):
        result=subprocess.run(job,capture_output=True,timeout=240,env=env);(a.out/(str(i)+'.private.log')).write_bytes(result.stdout+result.stderr)
        need(result.returncode==0,result.stderr.decode(errors='replace')[-3500:])
    application=dict(profile,kind='headless-model-audit',entry_artifact=record(obj),source=record(source),
        overrides=dict(profile['overrides'],native_headless_model_audit=contract),model_and_GPU_topology_unchanged=False,
        headless_model_audit=True,model_and_GPU_guards_preserved=True,headless_audit_kind=contract['kind'],headless_requests=3,
        native_performance_qualified=False,production_adopted=False)
    policy=a.out/'application-policy.private.json';save(policy,application)
    save(a.out/'result.private.json',dict(completed=True,application_policy=record(policy),entry=record(obj),reader=base['reader'],
        provider=record(provider),graph=record(graph_obj),graph_source=record(graph_source),source=record(source),commands=commands,
        observer_inputs=[record(a.out/name) for name in ('gate_up_input_audit.h','gate_up_input_audit.cpp')],
        generator=record(__file__),headless_transform=record(ROOT/'tools/headless_current_entry.py'),
        original_GGML_operations_preserved=True,host_pointer_geometry_and_layer_refusal_controls_passed=True,
        PS5_operations=0,native_input_identity_qualified=False,production_adopted=False))
    print(json.dumps(dict(completed=True,target_entry_graph_observer_compiled=True,GGML_operations_added=0,PS5_operations=0)))


if __name__=='__main__':main()
