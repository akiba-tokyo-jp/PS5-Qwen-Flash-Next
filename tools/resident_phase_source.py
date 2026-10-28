#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Opt-in native source-window guard; preserve original arithmetic and sources."""
from pathlib import Path
import os
import subprocess
from shader_storage import record

ROOT=Path(__file__).resolve().parents[1]


def build(parent,out,window_bytes=8<<20,existing_window=False):
    out=Path(out);out.mkdir()
    original=ROOT/'native/app/mapped_source.cpp';text=original.read_text()
    replacements=(
        ('namespace {\nclass NativeReads', 'namespace {\nstd::atomic<bool> resident_VM_scope{false};\nclass NativeReads'),
        ('return qwen_app::qualified_system_headroom(qwen_app::admit_native_system_memory());',
         'const auto memory=qwen_app::admit_native_system_memory();\n        if(resident_VM_scope.load())qwen_app::require_resident_source_VM(memory);\n        return qwen_app::qualified_system_headroom(memory);'),
        ('return qwen_app::qualified_system_headroom(qwen_app::observe_native_system_memory());',
         'const auto memory=qwen_app::observe_native_system_memory();\n        if(resident_VM_scope.load())qwen_app::require_resident_source_VM(memory);\n        return qwen_app::qualified_system_headroom(memory);'),
        ('SourceReadStats native_model_source_stats()',
         'void enable_resident_source_VM() { required().require_completed_window();\n    if(resident_VM_scope.exchange(true))throw std::runtime_error("Resident source VM scope cannot repeat");\n}\nSourceReadStats native_model_source_stats()'),
    )
    for old,new in replacements:
        if text.count(old)!=1:raise ValueError('Unique original source guard boundary required')
        text=text.replace(old,new)
    if existing_window:
        text=text.replace('qwen_app::require_resident_source_VM(memory)',
                          'qwen_app::require_resident_existing_source_VM(memory)')
    extra_inputs=[]
    if window_bytes not in (1<<20,8<<20):raise ValueError('Unsupported resident model-load window')
    if window_bytes==1<<20:
        from resident_load_reader import generate as generate_reader
        header=ROOT/'native/app/mapped_source.h';derived=out/'resident-mapped-source.private.h'
        derived.write_text(generate_reader(header.read_text()),newline='\n')
        text=text.replace('MappedSourceReader','ResidentMappedSourceReader')
        anchor='if(resident_VM_scope.exchange(true))throw std::runtime_error("Resident source VM scope cannot repeat");'
        if text.count(anchor)!=1:raise ValueError('Unique model-load window activation boundary required')
        text=text.replace(anchor,anchor+'\n    required().set_resident_load_limit(1u<<20);')
        anchor='    device_budget.enable();'
        if text.count(anchor)!=1:raise ValueError('Unique original postload device admission frontier required')
        text=text.replace(anchor,'    required().set_resident_load_limit(model_read_window);\n'+anchor)
        text='#include "resident-mapped-source.private.h"\n'+text
        extra_inputs=[ROOT/'tools/resident_load_reader.py',header,derived]
    generated=out/'mapped-source-phase-VM.private.cpp'
    generated.write_text('#include "resident_phase_vm.h"\n'+text,newline='\n')
    recipe=next(x.copy()for x in parent['compile_commands']if '-c'in x and Path(x[x.index('-c')+1]).name=='mapped_source.cpp')
    old_object=recipe[recipe.index('-o')+1];obj=out/'mapped-source-phase-VM.o'
    recipe[recipe.index('-c')+1]=str(generated);recipe[recipe.index('-o')+1]=str(obj);recipe+=['-I',str(ROOT/'native/app')]
    inputs=[record(p)for p in (Path(__file__),original,generated,ROOT/'native/app/resident_phase_vm.h')]+[record(p)for p in extra_inputs]
    result=subprocess.run(recipe,capture_output=True,timeout=180,env=dict(os.environ,TMP=str(out),TEMP=str(out)))
    (out/'compile.private.log').write_bytes(result.stdout+result.stderr)
    if result.returncode:raise RuntimeError(result.stderr.decode(errors='replace')[-2500:])
    for row in inputs:
        if record(row['path'])!=row:raise ValueError('Phase source input changed')
    return dict(original_source=record(original),generated_source=record(generated),original_object=old_object,
                object=record(obj),command=recipe,inputs=inputs,production_default_unchanged=True,
                original_read_window_and_arithmetic_unchanged=window_bytes==8<<20,
                selected_new_Direct_allocation_VM_pages=19,selected_next_existing_window_VM_pages=0 if existing_window else 19,
                existing_window_allocation_charged_once=existing_window,
                model_load_maximum_read_bytes=window_bytes,postload_maximum_read_bytes=8<<20,
                owned_CPU_scratch_bytes=8<<20,original_source_precision_and_payload_bytes_preserved=True)
