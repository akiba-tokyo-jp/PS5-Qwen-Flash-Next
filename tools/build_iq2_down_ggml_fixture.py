#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Bind the published Down operands to real GGML cache views and model shaders."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from build_performance_quantizer import record
from native_dispatch import ELF
from native_paired_carrier_adapter import controls
from start_success_route import load, need, save

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','component-link','native-proof','provider','retained-controls','out'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--resume-source-staging',action='store_true')
    p.add_argument('--resume-link',action='store_true',help='Reuse the completed entry after the missing AI SHA provider was identified')
    p.add_argument('--completed-GGML-prefix',type=Path,help='Reuse the two positively completed original decode cases')
    a=p.parse_args();base,native,provider=map(load,(a.component_link,a.native_proof,a.provider))
    need(base['completed'] and base['paired_down_carrier'] and native['completed'] and native['native_passed'] and
         native['ordinary_exit_observed'] and native['current_seven_restored_and_native_hashed'] and
         load(load(native['package']['path'])['relink']['path'])['artifact']==base['artifact'],
         'Reuse the exact completed native carrier operands and ordinary exit')
    need(provider['completed'] and provider['GPU_executable_sections_byte_exact'] and
         provider['original_codec_registry_unchanged'] and
         provider['redirected_resource_pairs']==(15 if provider.get('generic_indexed_refinement') else 13) and
         provider['new_global_initializers']==0 and provider.get('original_startup_lookup_expectations_preserved') is True and
         provider.get('separate_GPU_caller_arrays')==3,
         'The corrected caller-only provider must preserve original CPU startup lookup expectations')
    retained=controls(a.retained_controls,ROOT)
    completed_prefix=0
    if a.completed_GGML_prefix:
        done=load(a.completed_GGML_prefix);terminal=load(done['native']['path'])
        prior_link=load(load(done['package']['path'])['relink']['path'])
        from iq2_down_ggml_completion import validate_terminal
        validate_terminal(terminal)
        need(done['completed'] and done['ordinary_exit_observed'] and done['current_seven_restored_and_native_hashed'] and
             not done['native_passed'] and done['all_submitted_GPU_work_positively_completed'] and
             record(done['native']['path'])==done['native'] and prior_link['component_pack']==base['component_pack'] and
             len(terminal['cases'])==3 and [(r['layer'],r['width']) for r in terminal['cases']]==[(0,1),(0,2),(0,30)] and
             all(r['all_outputs_passed'] for r in terminal['cases'][:2]) and not terminal['cases'][2]['all_outputs_passed'],
             'Only the exact two returned decode cases before the numerical negative may be reused')
        old_provider=load(prior_link['model_resource_provider']['path']);changed=load(provider['shaders']['path'])
        if provider.get('generic_indexed_refinement'):
            parent=load(changed['ancestor']['path'])
            need(parent['packed_half_dequant_refinement'] and changed['reused_shader_resources']==13 and
                 all(r in changed['shaders'] for r in parent['shaders']),
                 'All thirteen prior resources must remain exact for the generic additions')
            changed=parent
        need(changed.get('packed_half_dequant_refinement') and changed['ancestor']==old_provider['shaders'] and
             changed['reused_shader_resources']==12,
             'The twelve original resources must remain exact when their two decode cases are reused')
        completed_prefix=2
    a.out.mkdir(parents=True,exist_ok=a.resume_source_staging or a.resume_link)
    if a.resume_link:
        need((a.out/'compile.private.log').read_bytes()==b'' and (a.out/'entry.o').is_file() and
             not(a.out/'link/result.private.json').exists() and not(a.out/'result.private.json').exists() and
             b'undefined symbol: ai_sha256_init' in (a.out/'link/link.private.log').read_bytes(),
             'Only the completed entry and diagnosed missing SHA link may resume')
    else:need(not(a.out/'compile.private.log').exists() and not(a.out/'link').exists(),
              'Source staging may resume only before the first compilation')
    for name in ('paired_down_native_support.h','paired_down_assets.h','resident_direct_tables.h',
                 'resident_incremental_tables.h','resident_phase_vm.h','resident_CPU_metadata_scope.h','system_memory.h'):
        src=a.component_link.parent/name
        actual=record(src)
        need(any(Path(row['path']).name==name and all(row[k]==actual[k] for k in ('bytes','sha256'))
                 for row in base['inputs_before']),
             'Only the exact completed native support and table headers may be reused')
        expected=src.read_bytes()
        if name=='paired_down_native_support.h':
            from build_speculative_batch_probe import once
            text=src.read_text()
            text=once(text,'        if(native_binding.at("CPU_only").get<bool>()){',
                '        const auto shader_CPU_admission=qwen_paired_down_prepare_CPU();\n        if(native_binding.at("CPU_only").get<bool>()){')
            text=once(text,'{"CPU_heap_peak_bytes",heap.peak_bytes},{"CPU_libc_fallbacks",heap.libc_fallbacks},{"Direct_readmission",capacity}',
                '{"CPU_heap_peak_bytes",heap.peak_bytes},{"CPU_libc_fallbacks",heap.libc_fallbacks},{"Direct_readmission",capacity},{"shader_CPU_admission",shader_CPU_admission}')
            expected=text.encode()
        target=a.out/name
        if target.exists():need((a.resume_source_staging or a.resume_link) and target.read_bytes()==expected,
                                'An already staged source changed')
        else:target.write_bytes(expected)
    receipt=load(a.current/'provenance/native-link.receipt.private.json')['lossless_shader_storage']
    shader_build=load(provider['shaders']['path'])
    need(record(provider['shaders']['path'])==provider['shaders'] and
         len(shader_build['shaders'])==provider['redirected_resource_pairs'],
         'Every immutable replacement resource is required')
    header='// SPDX-License-Identifier: MIT\n#pragma once\n#include <cstdint>\n'
    header+='extern "C" {const void*qwen_app_prepare_shader_code(const void*,std::size_t,std::size_t*,void**);void qwen_app_complete_shader_code(void*);\n'
    for row in shader_build['shaders']:
        header+='extern const unsigned char qwen_iq2_down_'+row['name']+'_data[];\n'
    header+='}\nstruct IQ2ResourceCheck{const void*data;std::size_t bytes;};\nstatic const IQ2ResourceCheck iq2_resource_checks[]={'+','.join(
        '{qwen_iq2_down_'+r['name']+'_data,'+str(r['artifact']['bytes'])+'}' for r in shader_build['shaders'])+'};\n'
    header+='static constexpr const char*iq2_shader_file_SHA256='+json.dumps(receipt['pool']['sha256'])+';\n'
    header+='static constexpr const char*iq2_shader_file_path='+json.dumps('/app0/qwen-runtime/shader-storage-'+receipt['pool']['sha256']+'.bin')+';\n'
    header+='static constexpr std::uint64_t iq2_shader_file_bytes='+str(receipt['pool']['bytes'])+';\n'
    header+='static constexpr const char*iq2_original_registry_SHA256='+json.dumps(receipt['registry_sha256'])+';\n'
    header+='static constexpr unsigned iq2_completed_GGML_prefix='+str(completed_prefix)+';\n'
    header+='#define IQ2_DOWN_GPU_RESOURCE_TRACE '+str(int(provider.get('GPU_resource_trace') is True))+'\n'
    if provider.get('GPU_resource_trace'):header+='extern "C" void qwen_iq2_down_begin_GPU_resource_trace();\n'
    (a.out/'iq2_down_resource_checks.h').write_text(header,newline='\n')
    support=(a.out/'paired_down_native_support.h').read_text()
    need('static void native_component_retain(' in support and
         'native_retained_result["IO_journal_closed"]=true;' in support and
         'vkDestroyDevice(' not in support,'Reuse the qualified retained-device completion path')
    source=a.out/'iq2_down_ggml_fixture.private.cpp'
    if a.resume_link:need(source.read_bytes()==(ROOT/'native/app/iq2_down_ggml_fixture.cpp').read_bytes(),
                          'The compiled entry source must remain exact')
    else:shutil.copyfile(ROOT/'native/app/iq2_down_ggml_fixture.cpp',source)
    command=base['commands'][0].copy()
    command[command.index('-c')+1]=str(source);command[command.index('-o')+1]=str(a.out/'entry.o')
    command=[str(a.out) if v==str(a.component_link.parent) else v for v in command]
    up=a.current.parent/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569'
    command[1:1]=['-I',str(up/'ggml/include'),'-I',str(up/'ggml/src')]
    env=dict(os.environ,TMP=str(a.out),TEMP=str(a.out))
    if not a.resume_link:
        run=subprocess.run(command,capture_output=True,timeout=180,env=env)
        (a.out/'compile.private.log').write_bytes(run.stdout+run.stderr)
        need(run.returncode==0,(run.stdout+run.stderr).decode(errors='replace')[-6000:])
    link_root=a.out/('link-with-ai-SHA' if a.resume_link else 'link')
    job=[sys.executable,'-B',str(ROOT/'tools/relink_retained_current.py'),'--current',str(a.current),
         '--out',str(link_root),'--replace','entry.o='+str(a.out/'entry.o'),
         '--replace','gpu.o='+provider['GPU']['path'],
         '--replace','shader-registry.o='+provider['shader_registry']['path']]
    for key in ('shader_data','shader_wrapper'):
        row=provider[key];need(record(row['path'])==row,'A selected resource object changed')
        job+=['--add-object',row['path']]
    # Reuse the already qualified whole-file Direct reader and integrity code.
    integrity=next(row for row in base['inputs_before'] if Path(row['path']).name=='paired_down_integrity.private.c')
    integrity_obj=a.component_link.parent/'integrity.o'
    compiled=next(x for x in base['commands'] if str(integrity_obj) in x)
    need(record(integrity['path'])==integrity and compiled[-1]==str(integrity_obj),
         'The unchanged compiled Direct reader is required')
    job+=['--add-object',str(integrity_obj)]
    sha_obj=a.component_link.parent/'sha256.o'
    need(base['commands'][1][-1]==str(sha_obj) and sha_obj.is_file(),'The unchanged original AI SHA object is required')
    job+=['--add-object',str(sha_obj)]
    flags=['--wrap=vkGetInstanceProcAddr','--wrap=qwen_native_driver_register_device',*provider['link_flags']]
    job+=['--link-flag='+flag for flag in flags]
    run=subprocess.run(job,capture_output=True,timeout=600,env=env)
    (a.out/('relink-with-ai-SHA.private.log' if a.resume_link else 'relink.private.log')).write_bytes(run.stdout+run.stderr)
    need(run.returncode==0,(run.stdout+run.stderr).decode(errors='replace')[-6000:])
    result_path=link_root/'result.private.json';result=load(result_path)
    prior=load(a.current/'provenance/native-link.receipt.private.json')
    linked=ELF(Path(result['artifact']['path']));table=linked.symbols['vk_common_physical_device_entrypoints'];callbacks=[]
    for row in prior['native_dispatch_audit']['required_physical_callbacks']:
        impl=linked.symbols.get('vk_common_'+row['callback']);pointer=linked.pointer(table['value']+row['offset'])
        callbacks.append(dict(callback=row['callback'],offset=row['offset'],implementation_present=impl is not None,
                              pointer_matches=impl is not None and pointer!=0 and pointer==impl['value']))
    need(all(row['pointer_matches'] for row in callbacks),'All original physical driver callbacks must remain selected')
    for name in ('__wrap_vkGetInstanceProcAddr','__wrap_qwen_native_driver_register_device','qwen_iq2_down_mul_mat_vec_id_q2_0_f32_f32_data'):
        need(name in linked.symbols,'The actual handle capture and selected model shader must be linked')
    inputs=result['inputs']+result['new_inputs']+[record(source),record(a.out/'paired_down_native_support.h'),
        record(a.out/'paired_down_assets.h'),record(ROOT/'native/app/retained_completed_device.h'),
        record(a.out/'iq2_down_resource_checks.h'),record(ROOT/'native/app/shader_assets.h'),
        record(ROOT/'native/app/shader_file_native.h'),
        record(ROOT/'native/app/native_failure_journal.h'),
        record(ROOT/'tools/build_iq2_down_ggml_fixture.py')]
    result.update(inputs_before=inputs,source=record(source),commands=[command,*base['commands'][1:3],result['link_command']],
        component_pack=base['component_pack'],parts=base['parts'],original_case_geometry=base['original_case_geometry'],
        component=base['component'],software_proof=base['software_proof'],model_resource_provider=record(a.provider),
        GGML_carrier_ABI=True,GGML_operator_linked=True,model_engine_linked=True,model_loads=0,
        CPU_startup_only_mode=True,driver_code_linked=True,maximum_GPU_dispatches=None,maximum_GGML_graphs=12-completed_prefix,
        completed_GGML_case_prefix=completed_prefix,
        completed_GGML_prefix_proof=record(a.completed_GGML_prefix) if a.completed_GGML_prefix else None,
        CPU_heap_cap=64<<20,device_owner_cap=128<<20,new_post_device_controls=0,retained_device_controls=19,
        retained_idle_device_until_ordinary_close=True,paired_down_carrier=True,
        unchanged_retirement_controls_reused=retained,actual_physical_dispatch_audit=callbacks,
        same_selected_Direct_table_mapping_and_incremental_restoration=True,
        linked_driver=base['linked_driver'],successful_driver_whole_archive_preserved=True,
        CPU_Direct_capacity_readmission=True,backend_free_calls=0,persistent_caches=False,
        CPU_shader_resource_admission_before_GPU=True,fresh_changed_CPU_startup_required=True,
        replacement_shader_CPU_leases_verified=len(shader_build['shaders']),original_all_asset_decode_replayed=False,
        successful_GGML_environment_verified_before_CPU_return=7,native_assertion_journal_installed=True,
        numerical_negative_ordinary_close_admitted_only_after_all_submitted_graphs_complete=True,
        native_GPU_qualified=False,production_adopted=False,PS5_operations=0)
    result_path.write_text(json.dumps(result,indent=2)+'\n')
    save(a.out/'result.private.json',dict(completed=True,relink=record(result_path),source=record(source),
        compile_command=command,reused_pack=base['component_pack'],new_GPU_graphs=12-completed_prefix,PS5_operations=0))
    print(json.dumps(dict(completed=True,GGML_carrier_ABI=True,new_GPU_graphs=12-completed_prefix,PS5_operations=0)))


if __name__=='__main__':main()
