#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Opt-in native source-window guard; preserve original arithmetic and sources."""
from pathlib import Path
import os
import subprocess
from shader_storage import record

ROOT=Path(__file__).resolve().parents[1]


def build(parent,out):
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
    generated=out/'mapped-source-phase-VM.private.cpp'
    generated.write_text('#include "resident_phase_vm.h"\n'+text,newline='\n')
    recipe=next(x.copy()for x in parent['compile_commands']if '-c'in x and Path(x[x.index('-c')+1]).name=='mapped_source.cpp')
    old_object=recipe[recipe.index('-o')+1];obj=out/'mapped-source-phase-VM.o'
    recipe[recipe.index('-c')+1]=str(generated);recipe[recipe.index('-o')+1]=str(obj);recipe+=['-I',str(ROOT/'native/app')]
    inputs=[record(p)for p in (Path(__file__),original,generated,ROOT/'native/app/resident_phase_vm.h')]
    result=subprocess.run(recipe,capture_output=True,timeout=180,env=dict(os.environ,TMP=str(out),TEMP=str(out)))
    (out/'compile.private.log').write_bytes(result.stdout+result.stderr)
    if result.returncode:raise RuntimeError(result.stderr.decode(errors='replace')[-2500:])
    for row in inputs:
        if record(row['path'])!=row:raise ValueError('Phase source input changed')
    return dict(original_source=record(original),generated_source=record(generated),original_object=old_object,
                object=record(obj),command=recipe,inputs=inputs,production_default_unchanged=True,
                original_read_window_and_arithmetic_unchanged=True,selected_next_window_VM_pages=19)
