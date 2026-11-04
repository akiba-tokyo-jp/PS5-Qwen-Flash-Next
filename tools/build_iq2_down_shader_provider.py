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
    p.add_argument('--caller-arrays',action='store_true',help='Redirect GPU references to separate arrays and preserve original startup lookups')
    p.add_argument('--trace-GPU-resources',action='store_true',help='Record actual resource addresses only after explicit GPU entry')
    p.add_argument('--generic-software-proof',type=Path)
    p.add_argument('--F16-Up-proof',type=Path)
    p.add_argument('--F16-operands',type=Path)
    p.add_argument('--large-cache-index-proof',type=Path)
    a=p.parse_args();built,software,lease=load(a.shaders),load(a.software_proof),load(a.lease_proof)
    packed=built.get('packed_half_dequant_refinement') is True
    generic=built.get('generic_indexed_refinement') is True
    F16=built.get('generic_indexed_F16_refinement') is True
    large=built.get('large_cache_index_safe') is True
    F16_base=built;F16_base_row=record(a.shaders)
    if large:
        need(F16 and a.large_cache_index_proof is not None and a.caller_arrays,
             'The full-cache index refinement requires exact uint32 domain controls and original startup arrays')
        index=load(a.large_cache_index_proof);F16_base_row=built['ancestor'];F16_base=load(F16_base_row['path'])
        need(record(F16_base_row['path'])==F16_base_row and F16_base['generic_indexed_F16_refinement'] and
             len(F16_base['shaders'])==len(built['shaders'])==17 and index['completed'] and
             index['shaders']==record(a.shaders) and index['decoder']==built['carrier_decoder'] and
             index['actual_GLSL_helper_extracted'] and index['independent_uint64_reference'] and
             index['all3713_planes_checked'] and index['all_physical_addresses_below_2GiB'] and
             index['cases']>=20000000 and index['old_overflow_negatives']>0 and
             built['original_float_decoder_expression_preserved'] and
             all(new['name']==old['name'] and new['recipe']==old['recipe'] and new['previous_artifact']==old['artifact']
                 for new,old in zip(built['shaders'],F16_base['shaders'])),
             'All seventeen unchanged recipes and exact large-cache address controls must remain bound')
    if F16:
        from iq2_up_model_scope import require_arithmetic_qualification,require_down_qualification
        need(a.F16_Up_proof is not None and a.F16_operands is not None,
             'The completed F16 storage prerequisite and six changed operand references are required')
        require_arithmetic_qualification(record(a.F16_Up_proof))
        parent=load(F16_base['ancestor']['path']);native=load(built['native_selection_evidence']['path'])
        previous_provider=load(load(native['package']['path'])['relink']['path'])['model_resource_provider']
        require_down_qualification(built['native_selection_evidence'],previous_provider)
        need(record(F16_base['ancestor']['path'])==F16_base['ancestor'] and parent['generic_indexed_refinement'] and
             len(parent['shaders'])==15 and F16_base['shaders'][:15]==parent['shaders'] and
             load(previous_provider['path'])['shaders']==F16_base['ancestor'],
             'The fifteen unchanged native-qualified F32 resources must remain exact')
        for file in ('mul_mm.comp','mul_mm_funcs.glsl','mul_mm_id_funcs.glsl'):
            need((Path(F16_base['ancestor']['path']).parent/'shaders'/file).read_bytes()==
                 (Path(F16_base_row['path']).parent/'shaders'/file).read_bytes(),
                 'F16 specialization may change only generator storage defines, not the qualified source')
        operands=load(a.F16_operands)
        need(operands['completed'] and operands['native_F32_proof']==built['native_selection_evidence'] and
             operands['F16_storage_FP32_accumulation'] and len(operands['wide_cases'])==6 and
             operands['reused_decode_cases']==6 and operands['original_tolerance_unchanged'] and
             operands['original_weights_and_ids_unchanged'],
             'Exactly six changed wide references with the original tolerance and weights are required')
        need({r['name'] for r in built['shaders'][15:]}=={'matmul_id_quant_f32','matmul_id_subgroup_quant_f32'} and
             all(r['recipe']['fp16'] and r['recipe']['defines']['ACC_TYPE']=='float' for r in built['shaders'][15:]),
             'Only the two F16-storage FP32-accumulation indexed variants may be added')
    if generic:
        parent=load(built['ancestor']['path']);old={r['name']:r for r in parent['shaders']};new={r['name']:r for r in built['shaders']}
        extra={'matmul_id_quant_f32_fp32','matmul_id_subgroup_quant_f32_fp32'}
        need(record(built['ancestor']['path'])==built['ancestor'] and built['reused_shader_resources']==13 and
             len(old)==13 and set(new)==set(old)|extra and all(new[k]==v for k,v in old.items()) and
             a.generic_software_proof is not None,'The immutable thirteen-resource parent and two generic additions are required')
        proof=load(a.generic_software_proof)
        need(proof['completed'] and proof['build']==record(a.shaders) and proof['distinct_cases']==6 and
             set(proof['qualified_resource_names'])==extra and proof['all_outputs_passed'] and
             proof['all_GPU_resources_positively_retired'] and proof['Q2_specialization_of_actual_new_SPIRV'],
             'Six positive wide Q2 specializations of the actual new binaries are required')
    if packed:
        parent=load(built['ancestor']['path']);new={r['name']:r for r in built['shaders']};old={r['name']:r for r in parent['shaders']}
        need(record(built['ancestor']['path'])==built['ancestor'] and built['reused_shader_resources']==12 and
             built['original_FP16_output_ABI_preserved'] and built['complete_FP16_values_verified']==49152000 and
             record(built['packed_half_software_proof']['path'])==built['packed_half_software_proof'] and
             load(built['packed_half_software_proof']['path'])['completed'] and new.keys()==old.keys() and
             all(new[k]==old[k] for k in old if k!='dequant_q2_0'),
             'Only one fully qualified packed-half resource may differ from the twelve immutable resources')
    software_build=load(F16_base['ancestor']['path'])['ancestor'] if F16 else (built['ancestor'] if generic else record(a.shaders))
    need(built['completed'] and (built['all_non_declaration_words_byte_exact'] or packed or generic or F16) and
         software['completed'] and software['build']==software_build and
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
    resource_count=17 if F16 else (15 if generic else 13)
    need(len(mapping)==resource_count and len(set(rename))==2*resource_count,'Every distinct actual resource pair is required')
    caller_tables=[]
    if a.caller_arrays:
        receipt=load(a.current/'provenance/native-link.receipt.private.json')
        caller_tables=[x for x in receipt['lossless_shader_storage']['lookup_tables'] if x['name'] in
            ('arr_dmmv_q2_0_f32_f32','arr_dmmv_q2_0_f16_f32','arr_dmmv_id_q2_0_f32_f32')]
        need(len(caller_tables)==3 and all(t['dimensions']==[3] and len(t['targets'])==3 and
             all(k in target_specs for k in t['targets']) for t in caller_tables),
             'Three original array recipes and nine selected targets required')
        for t in caller_tables:
            replacement='qwen_iq2_down_'+t['name']
            rename+=['--redefine-sym='+t['name']+'_data='+replacement+'_data',
                     '--redefine-sym='+t['name']+'_len='+replacement+'_len']
            assets+='__attribute__((visibility("hidden"))) const unsigned char*const '+replacement+'_data[3]={'+','.join(
                target_specs[k]['replacement']+'_data' for k in t['targets'])+'};\n'
            assets+='__attribute__((visibility("hidden"))) const uint64_t '+replacement+'_len[3]={'+','.join(
                str(target_specs[k]['replacement_bytes'])+'ULL' for k in t['targets'])+'};\n'
    data=a.out/'IQ2-Down-shader-data.c';put(data,assets)
    wrapper=a.out/'IQ2-Down-shader-lease.private.cpp'
    put(wrapper,'''// SPDX-License-Identifier: MIT
#include "fused_shader_lease.h"
#include <cstring>
#include <cstdio>
extern "C" {
#include "hash/sha256/sha256.h"
const void*__real_qwen_app_prepare_shader_code(const void*,std::size_t,std::size_t*,void**);
void qwen_app_complete_shader_code(void*);
void qwen_native_stage(const char*);
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
bool trace_GPU_resources=false;
}
extern "C" void qwen_iq2_down_begin_GPU_resource_trace(){trace_GPU_resources=true;}
extern "C" const void*__wrap_qwen_app_prepare_shader_code(const void*storage,std::size_t bytes,std::size_t*decoded,void**lease){
'''+(''' if(trace_GPU_resources){
  unsigned replacement=0;for(unsigned i=0;i<sizeof(sources)/sizeof(sources[0]);++i)if(storage==sources[i].replacement)replacement=i+1;
  char line[160];std::snprintf(line,sizeof(line),"IQ2_Down_GPU_shader pointer=%p bytes=%zu replacement=%u",storage,bytes,replacement);
  qwen_native_stage(line);
 }
''' if a.trace_GPU_resources else '')+'''
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
    if a.caller_arrays:
        new_table.write_bytes(Path(registry['path']).read_bytes())
        patched=dict(completed=True,array_pointer_length_pairs=[],added_undefined_symbols=0,
            all_other_original_bytes_exact=True,original_codec_registry_entries_and_relocations_unchanged=True,
            original_startup_lookup_arrays_and_expectations_byte_exact=True,
            separate_caller_arrays=caller_tables,new_executable_bytes=0)
    else:patched=patch_registry(registry['path'],new_table,target_specs,receipt['lossless_shader_storage']['lookup_tables'])
    save(a.out/'specialization-array-audit.private.json',patched)
    old_sections,new_sections=section_map(Path(registry['path'])),section_map(new_table)
    need(old_sections.keys()==new_sections.keys() and
         all(data==new_sections[name][1] for name,(section,data) in old_sections.items() if section[2]&4) and
         ELF(Path(registry['path'])).symbols.keys()==ELF(new_table).symbols.keys(),
         'The original specialization definitions and constructor instructions must remain exact')
    references=subprocess.check_output([str(host/'llvm-nm.exe'),'--undefined-only','--format=posix',str(new_gpu),str(new_table)],text=True)
    undefined={line.split()[0] for line in references.splitlines() if ' U ' in line}
    if a.caller_arrays:
        array_targets={k for t in caller_tables for k in t['targets']}
        need(all('qwen_iq2_down_'+r['name']+'_data' in undefined for r in built['shaders'] if r['name'] not in array_targets) and
             all('qwen_iq2_down_'+t['name']+suffix in undefined for t in caller_tables for suffix in ('_data','_len')) and
             new_table.read_bytes()==Path(registry['path']).read_bytes(),
             'Direct resources and separate caller arrays must bind without changing startup registry bytes')
    else:
        need(all('qwen_iq2_down_'+row['name']+'_data' in undefined for row in built['shaders']) and
             len(patched['array_pointer_length_pairs'])==9,
             'All thirteen data references and nine literal array lengths must be redirected')
    save(a.out/'result.private.json',dict(completed=True,shaders=record(a.shaders),software_proof=record(a.software_proof),
        reused_lease_controls=record(a.lease_proof),unchanged_lease_controls_replayed=0,
        inputs=inputs+[record(data),record(wrapper),record(ROOT/'native/app/fused_shader_lease.h')],
        GPU=record(new_gpu),selected_GPU=selected,shader_data=record(data_obj),shader_wrapper=record(wrapper_obj),
        shader_registry=record(new_table),selected_shader_registry=registry,specialization_array_audit=record(a.out/'specialization-array-audit.private.json'),
        existing_specialization_constructor_instructions_preserved=True,original_codec_registry_unchanged=True,
        original_shader_registry_unchanged=a.caller_arrays,
        original_startup_lookup_expectations_preserved=a.caller_arrays,separate_GPU_caller_arrays=len(caller_tables),
        only_selected_array_relocations_and_lengths_changed=not a.caller_arrays,
        reused_completed_compile_commands=3 if a.resume_compiled else 0,
        GPU_executable_sections_byte_exact=True,redirected_resource_pairs=resource_count,new_global_initializers=0,
        GPU_resource_trace=a.trace_GPU_resources,packed_half_dequant_refinement=packed,
        generic_indexed_refinement=generic,generic_software_proof=record(a.generic_software_proof) if generic else None,
        F16_arithmetic_only=F16,F16_Up_prerequisite=record(a.F16_Up_proof) if F16 else None,
        F16_operands=record(a.F16_operands) if F16 else None,
        large_cache_index_safe=large,large_cache_index_proof=record(a.large_cache_index_proof) if large else None,
        changed_decode_addressing=large,required_new_native_graphs=12 if large else (6 if F16 else None),
        link_flags=['--wrap=qwen_app_prepare_shader_code'],commands=commands,
        required_converted_Down_layers=list(range(48)),all_Q2_0_tensors_must_be_IQ2_carriers=True,
        model_profile_requires_MMVQ_and_F16_disabled=not F16,descriptor_plane_origin_and_cache_view_qualified=False,
        native_full_model_qualified=False,driver_code_changed=False,persistent_caches=False,PS5_operations=0,production_adopted=False))
    print(dict(completed=True,resource_pairs=resource_count,GPU_instructions_byte_exact=True,new_global_initializers=0,PS5_operations=0))


if __name__=='__main__':main()
