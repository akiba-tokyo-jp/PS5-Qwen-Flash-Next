#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Redirect only selected Q2 resource symbols while preserving GPU instructions."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
from build_gpu_cache_rank_fused import section_map
from build_performance_quantizer import record
from native_dispatch import ELF
from start_success_route import load,need,save

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','shaders','software-proof','lease-proof','out'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--resume-compiled',action='store_true',help='Reuse the three exact compiled objects after the incomplete reference audit')
    a=p.parse_args();built,software,lease=load(a.shaders),load(a.software_proof),load(a.lease_proof)
    need(built['completed'] and built['all_non_declaration_words_byte_exact'] and
         software['completed'] and software['build']==record(a.shaders) and
         software['actual_model_matvec_shaders']==6 and software['shape_cases']==18 and software['F32_input_only'] and
         software['all_outputs_passed'] and software['software_SPIRV_reference'] and
         lease['completed'] and lease['new_shader_lease_controls']==10,
         'Validated model shaders, actual six-resource software math and the unchanged ten lease controls required')
    known={Path(x['path']).name:x for x in lease['inputs']}
    for relative in ('native/app/fused_shader_lease.h','tests/fused_shader_lease_test.cpp'):
        need(record(ROOT/relative)==known[Path(relative).name],'The qualified original CPU shader lease changed')
    a.out.mkdir(parents=True,exist_ok=a.resume_compiled)
    need(not(a.out/'result.private.json').exists(),'A completed provider must not be rebuilt')
    def put(path,text):
        if path.exists():need(a.resume_compiled and path.read_text()==text,'An already compiled source changed')
        else:path.write_text(text,encoding='utf-8',newline='\n')
    host=a.workspace/'toolchain/llvm-mingw-20261006-ucrt-x86_64/bin'
    sdk=a.workspace/'toolchain/ps5-sdk-radv/ps5-payload-sdk/target/include'
    up=a.current.parent/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569'
    rows=load(a.current/'provenance/retained-relink-inputs.private.json');selected=next(x for x in rows if Path(x['original_path']).name=='gpu.o')
    need(record(selected['path'])=={k:selected[k] for k in ('path','bytes','sha256')},'The exact selected GPU provider changed')
    original=ELF(a.current/'provenance/qwen-native.pie.elf');new_gpu=a.out/'GPU-IQ2-Down-resource-references.o'
    rename=[];assets='#include <stdint.h>\n';declarations=[];sources=[];mapping=[];inputs=[];target_specs={}
    for row in built['shaders']:
        artifact=row['artifact'];need(record(artifact['path'])==artifact,'An actual validated shader changed')
        raw=Path(artifact['path']).read_bytes();name=row['name'];replacement='qwen_iq2_down_'+name
        token=original.symbol_data(name+'_data');magic,offset,stored,decoded=struct.unpack('<8sQII',token)
        need(magic==b'QWSPVX01' and struct.unpack('<Q',original.symbol_data(name+'_len'))[0]==stored and
             len(raw)>=20 and len(raw)<=1<<20 and len(raw)%4==0,'The exact selected external token/length and bounded replacement are required')
        rename+=['--redefine-sym='+name+'_data='+replacement+'_data','--redefine-sym='+name+'_len='+replacement+'_len']
        assets+='__attribute__((aligned(4),visibility("hidden"))) const unsigned char '+replacement+'_data[]={'+','.join(str(x) for x in raw)+'};\n'
        assets+='const uint64_t '+replacement+'_len='+str(len(raw))+'ULL;\n'
        digest=hashlib.sha256(raw).digest()
        declarations+=['extern const unsigned char '+name+'_data[];',
            'extern const unsigned char '+replacement+'_data[];']
        sources.append('static const unsigned char '+replacement+'_sha[]={'+','.join(str(x) for x in digest)+'};')
        mapping.append('{'+name+'_data,'+str(stored)+','+str(decoded)+','+replacement+'_data,'+str(len(raw))+','+replacement+'_sha}')
        target_specs[name]=dict(replacement=replacement,original_stored_bytes=stored,replacement_bytes=len(raw))
        inputs.append(artifact)
    need(len(mapping)==13 and len(set(rename))==26,'Thirteen distinct actual resource pairs required')
    data=a.out/'IQ2-Down-shader-data.c';put(data,assets)
    wrapper=a.out/'IQ2-Down-shader-lease.private.cpp'
    put(wrapper,'''// SPDX-License-Identifier: MIT
#include "fused_shader_lease.h"
#include <cstring>
extern "C" {
#include "hash/sha256/sha256.h"
const void*__real_qwen_app_prepare_shader_code(const void*,std::size_t,std::size_t*,void**);
void qwen_app_complete_shader_code(void*);
'''+ '\n'.join(declarations)+'''
}
namespace {
bool digest(const void*data,std::size_t bytes,const unsigned char*expected){
 sha256_t state;unsigned char actual[32];sha256_init(&state);
 sha256_update(&state,static_cast<const unsigned char*>(data),bytes);sha256_final(&state,actual);
 return !std::memcmp(actual,expected,32);
}
'''+ '\n'.join(sources)+'''
const qwen_app::FusedShaderSource sources[]={'''+','.join(mapping)+'''};
}
extern "C" const void*__wrap_qwen_app_prepare_shader_code(const void*storage,std::size_t bytes,std::size_t*decoded,void**lease){
 for(const auto&source:sources)if(storage==source.replacement)
  return qwen_app::prepare_fused_shader(storage,bytes,decoded,lease,source,
   {__real_qwen_app_prepare_shader_code,qwen_app_complete_shader_code,digest});
 return __real_qwen_app_prepare_shader_code(storage,bytes,decoded,lease);
}
''')
    data_obj=a.out/'IQ2-Down-shader-data.o';wrapper_obj=a.out/'IQ2-Down-shader-lease.o'
    commands=[[str(host/'llvm-objcopy.exe'),*rename,selected['path'],str(new_gpu)],
        [str(host/'clang.exe'),'--no-default-config','--target=x86_64-sie-ps5','-isystem',str(sdk),'-O2','-fPIC','-c',str(data),'-o',str(data_obj)],
        [str(host/'clang++.exe'),'--no-default-config','--target=x86_64-sie-ps5','-nostdinc++','-isystem',str(sdk/'c++/v1'),
         '-isystem',str(sdk),'-std=c++17','-fexceptions','-fcxx-exceptions','-femulated-tls','-fno-stack-protector','-fno-plt','-fPIC',
         '-O2','-ffunction-sections','-fdata-sections','-I',str(ROOT/'native/app'),'-I',str(up/'vendor'),'-c',str(wrapper),'-o',str(wrapper_obj)]]
    for index,job in enumerate(commands):
        if a.resume_compiled:
            need((a.out/(str(index)+'.private.log')).is_file() and (new_gpu,data_obj,wrapper_obj)[index].is_file(),
                 'All three previously completed compile outputs/logs are required');continue
        r=subprocess.run(job,capture_output=True,timeout=90,env=dict(os.environ,TMP=str(a.out),TEMP=str(a.out)))
        (a.out/(str(index)+'.private.log')).write_bytes(r.stdout+r.stderr)
        need(r.returncode==0,(r.stdout+r.stderr).decode(errors='replace')[-3000:])
    before,after=section_map(Path(selected['path'])),section_map(new_gpu)
    need(before.keys()==after.keys() and all(data==after[name][1] for name,(section,data) in before.items() if section[2]&4),
         'Every executable GPU provider byte must remain exact')
    for artifact in (data_obj,wrapper_obj):
        sections=section_map(artifact)
        need(not any('init_array' in name or '.ctors' in name for name in sections),'No additional global initializer is permitted')
        if artifact==data_obj:need(not any(x[0][2]&4 and x[0][5] for x in sections.values()),'Shader data must contain no executable bytes')
    # The selected registry object defines the matvec lookup arrays. Its
    # separate codec lookup must continue pointing to the original tokens.
    registry=next(x for x in rows if Path(x['original_path']).name=='shader-registry.o')
    need(record(registry['path'])=={k:registry[k] for k in ('path','bytes','sha256')},'The selected original registry changed')
    new_table=a.out/'IQ2-Down-specialization-registry.o'
    from iq2_down_specialization_arrays import patch_registry
    receipt=load(a.current/'provenance/native-link.receipt.private.json')
    patched=patch_registry(registry['path'],new_table,target_specs,receipt['lossless_shader_storage']['lookup_tables'])
    save(a.out/'specialization-array-audit.private.json',patched)
    old_sections,new_sections=section_map(Path(registry['path'])),section_map(new_table)
    need(old_sections.keys()==new_sections.keys() and
         all(data==new_sections[name][1] for name,(section,data) in old_sections.items() if section[2]&4) and
         ELF(Path(registry['path'])).symbols.keys()==ELF(new_table).symbols.keys(),
         'The original specialization definitions and constructor instructions must remain exact')
    references=subprocess.check_output([str(host/'llvm-nm.exe'),'--undefined-only','--format=posix',str(new_gpu),str(new_table)],text=True)
    undefined={line.split()[0] for line in references.splitlines() if ' U ' in line}
    need(all('qwen_iq2_down_'+row['name']+'_data' in undefined for row in built['shaders']) and
         len(patched['array_pointer_length_pairs'])==9,
         'All thirteen data references and nine literal array lengths must be redirected')
    save(a.out/'result.private.json',dict(completed=True,shaders=record(a.shaders),software_proof=record(a.software_proof),
        reused_lease_controls=record(a.lease_proof),unchanged_lease_controls_replayed=0,
        inputs=inputs+[record(data),record(wrapper),record(ROOT/'native/app/fused_shader_lease.h')],
        GPU=record(new_gpu),selected_GPU=selected,shader_data=record(data_obj),shader_wrapper=record(wrapper_obj),
        shader_registry=record(new_table),selected_shader_registry=registry,specialization_array_audit=record(a.out/'specialization-array-audit.private.json'),
        existing_specialization_constructor_instructions_preserved=True,original_codec_registry_unchanged=True,
        original_shader_registry_unchanged=False,only_selected_array_relocations_and_lengths_changed=True,
        reused_completed_compile_commands=3 if a.resume_compiled else 0,
        GPU_executable_sections_byte_exact=True,redirected_resource_pairs=13,new_global_initializers=0,
        link_flags=['--wrap=qwen_app_prepare_shader_code'],commands=commands,
        required_converted_Down_layers=list(range(48)),all_Q2_0_tensors_must_be_IQ2_carriers=True,
        model_profile_requires_MMVQ_and_F16_disabled=True,descriptor_plane_origin_and_cache_view_qualified=False,
        native_full_model_qualified=False,driver_code_changed=False,persistent_caches=False,PS5_operations=0,production_adopted=False))
    print(dict(completed=True,resource_pairs=13,GPU_instructions_byte_exact=True,new_global_initializers=0,PS5_operations=0))


if __name__=='__main__':main()
