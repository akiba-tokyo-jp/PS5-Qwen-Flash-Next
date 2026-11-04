#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Move the original zero-table span behind BSS and qualify its owned LOAD hole."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
from build_performance_quantizer import record
from driver_table_storage import audit_linked_storage
from external_rodata_layout import verify_repacked
from external_zero_layout import exclude
from native_dispatch import ELF
from price_cpu_startup_original_reader import require_CPU_profile
from start_success_route import load,need,save
ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','CPU-package','CPU-completion','primitive-proof','out'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--finish-linked',action='store_true',help='Finish auditing the same linked ELF after a host-only ordering refusal')
    a=p.parse_args();base,profile=require_CPU_profile(a.CPU_package);done=load(a.CPU_completion)
    need(done['completed'] and done['native_requests']==0 and done['kind']=='CPU-startup-staging-memory' and
        load(done['closure']['path'])['current_seven_restored_and_native_hashed'] and
        load(done['terminal']['path'])['candidate_SELF_sha256']==base['SELF']['sha256'] and
        base['CPU_startup_libc_parameter_policy']['heap_bytes']==8<<20,
        'Completed original full-link eight-MiB CPU-only startup required')
    primitive=load(a.primitive_proof)
    need(primitive['completed'] and primitive['CPU_probe_passed'] and primitive['ordinary_exit_observed'] and
        primitive['current_seven_restored_and_native_hashed'] and primitive['GPU_calls']==primitive['model_loads']==0,
        'The pre-CXX model-independent owned-hole Direct primitive must already be positive')
    old=load(base['relink']['path']);need(record(old['artifact']['path'])==old['artifact'],'The unchanged full CPU link changed')
    for row in old['inputs']+old['new_inputs']:need(record(row['path'])==row,'A frozen original CPU input changed')
    prior=load(a.current/'provenance/native-link.receipt.private.json');tables=prior['lossless_driver_tables']
    if a.finish_linked:need(a.out.is_dir() and not(a.out/'result.private.json').exists(),'Only the same incomplete host scope may finish')
    else:a.out.mkdir(parents=True,exist_ok=False)
    def freeze(path,text):
        if path.exists():need(a.finish_linked and path.read_text()==text,'A frozen native input changed')
        else:path.write_text(text,newline='\n')
    size=(9486336+65535)&~65535
    zero_sha=hashlib.sha256(bytes(size)).hexdigest();fnv=14695981039346656037*pow(1099511628211,size,1<<64)%(1<<64)
    manifest=a.out/'early_CPU_tables_manifest.h'
    freeze(manifest,'#define EARLY_ORIGINAL_TABLE_BYTES 9486336u\n#define EARLY_DIRECT_BYTES '+str(size)+'u\n'+
        '#define EARLY_PACKED_BYTES '+str(tables['packed_bytes'])+'u\n#define EARLY_ZERO_FNV64 UINT64_C('+str(fnv)+')\n'+
        'static const unsigned char early_zero_SHA256[32]={'+','.join(str(x) for x in bytes.fromhex(zero_sha))+'};\n')
    assembly=a.out/'boundary.S';freeze(assembly,'.section .qwen_early_padding,"aw",@nobits\n.section .note.GNU-stack,"",@progbits\n')
    script=a.out/'early-tables.ld';freeze(script,'''SECTIONS {
 .qwen_driver_tables (NOLOAD) : ALIGN(65536) {
  __qwen_driver_tables_start = .; KEEP(*(.qwen_cold_table_*)) . = ALIGN(16384); __qwen_driver_tables_end = .;
 } : data
 .qwen_early_padding (NOLOAD) : { KEEP(*(.qwen_early_padding)) . = ALIGN(65536); __qwen_early_tables_end = .; } : data
} INSERT AFTER .bss;
''')
    llvm=a.workspace/'toolchain/llvm-mingw-20261006-ucrt-x86_64/bin';sdk=a.workspace/'toolchain/ps5-sdk-radv/ps5-payload-sdk/target/include'
    source=ROOT/'native/app/early_CPU_tables.c';sha=a.workspace/'native/model_hash/sha256.c';obj=a.out/'early-tables.o'
    common=[str(llvm/'clang.exe'),'--no-default-config','--target=x86_64-sie-ps5','-isystem',str(sdk),'-std=gnu11',
        '-O2','-fPIC','-fno-stack-protector','-fno-plt','-ffunction-sections','-fdata-sections','-Wall','-Wextra','-Werror',
        '-I',str(a.out),'-I',str(ROOT/'native/app'),'-I',str(sha.parent)]
    commands=[]
    def run(job,label):
        if a.finish_linked and label in ('compile-prelude','compile-boundary','compile-SHA','link'):
            target=Path(job[job.index('-o')+1])
            need(target.is_file() and (a.out/(label+'.private.log')).is_file() and not(a.out/(label+'.private.log')).read_bytes(),
                 'One already successful host compile/link is required')
            if label=='compile-prelude':need(source.stat().st_mtime_ns<=target.stat().st_mtime_ns and
                manifest.stat().st_mtime_ns<=target.stat().st_mtime_ns,'Native source or constants changed after compilation')
            commands.append(job);return
        commands.append(job);result=subprocess.run(job,capture_output=True,timeout=180,env=dict(os.environ,TMP=str(a.out),TEMP=str(a.out)))
        (a.out/(label+'.private.log')).write_bytes(result.stdout+result.stderr)
        need(not result.returncode,(result.stdout+result.stderr).decode(errors='replace')[-4000:])
    run(common+['-c',str(source),'-o',str(obj)],'compile-prelude')
    boundary=a.out/'boundary.o';run([str(llvm/'clang.exe'),'--no-default-config','--target=x86_64-sie-ps5','-c',str(assembly),'-o',str(boundary)],'compile-boundary')
    added=[obj,boundary];SHA_reused='ai_sha256_init' in ELF(Path(old['artifact']['path'])).symbols
    if not SHA_reused:
        sha_obj=a.out/'sha256.o';run(common+['-c',str(sha),'-o',str(sha_obj)],'compile-SHA');added.append(sha_obj)
    control=a.out/'control.pie.elf';image=a.out/'early-CPU.pie.elf';link=old['link_command'].copy()
    table_index=next(i for i in range(len(link)-1) if link[i]=='-T' and Path(link[i+1]).name=='tables.ld')
    link[table_index+1]=str(script);link[link.index('-o')+1]=str(control)
    link=[('-Map='+str(a.out/'native-link.private.map')) if x.startswith('-Map=') else x for x in link]
    link[1:1]=list(map(str,added));run(link,'link')
    geometry=audit_linked_storage(control,tables);native=ELF(control)
    begin=native.symbols['__qwen_driver_tables_start']['value'];end=native.symbols['__qwen_early_tables_end']['value']
    need(end-begin==size and native.symbols['__qwen_driver_tables_end']['value']-begin==9486336,'Original table span and exclusive padding differ')
    start=native.symbols['__init_array_start']['value'];finish=native.symbols['__init_array_end']['value']
    constructors=[native.pointer(at) for at in range(start,finish,8)]
    need(len(constructors)==32 and constructors[:2]==[native.symbols[name]['value'] for name in ('__cpu_indicator_init','_GLOBAL__I_000100')] and
        constructors[2:4]==[native.symbols[name]['value'] for name in ('early_CPU_tables_map','early_CPU_tables_check')],
        'Preserve the original two platform initializers, then back tables before the original application initializers')
    raw,layout=exclude(native.data,begin,end);intermediate=a.out/'excluded.pie.elf';intermediate.write_bytes(raw)
    # Preserve the original zero sections through the stock formatter so it
    # places its generated dynamic metadata AFTER the complete owned range.
    # The CPU-only package excludes the range only after that conversion.
    layout['zero_hole_applied_after_PS5_conversion_only']=True
    result=copy.deepcopy(old);result.update(artifact=record(control),baseline_relink=False,exact_current_native_ELF_reproduced=False,
        new_inputs=old['new_inputs']+[record(path) for path in added],link_command=link,commands=commands,
        early_CPU_tables=dict(completed_host_layout=True,control_native=record(control),original_CPU_package=record(a.CPU_package),
            original_CPU_completion=record(a.CPU_completion),pre_CXX_primitive_proof=record(a.primitive_proof),layout=layout,
            original_table_geometry=geometry,source=record(source),header=record(ROOT/'native/app/early_CPU_tables.h'),
            manifest=record(manifest),linker_script=record(script),zero_SHA256=zero_sha,zero_FNV64=fnv,
            mapped_CPU_Direct_bytes=size,original_table_bytes=9486336,additional_zero_padding_bytes=size-9486336,
            original_constructors=30,original_platform_initializers_preserved_before_prelude=2,
            additional_CPU_constructors=2,strict_failure_park_before_original_application_CXX=True,
            runtime_mapping_adoption_by_model_not_yet_qualified=True,source_payload_IO=0,model_GPU_operations=0,
            process_lifetime_CPU_backing_retained_until_ordinary_OS_close=True,SHA_provider_reused=SHA_reused),
        native_quality_or_speed_measured=False,production_adopted=False,PS5_operations=0,
        completed_compile_and_link_reused_without_replay=a.finish_linked)
    save(a.out/'result.private.json',result)
    print(dict(completed=True,original_tables=673,exclusive_zero_hole_bytes=size,constructors=32,source_payload_IO=0,PS5_operations=0))


if __name__=='__main__':main()
