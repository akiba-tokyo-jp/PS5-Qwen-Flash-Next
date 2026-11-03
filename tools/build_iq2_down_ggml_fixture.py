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
    a=p.parse_args();base,native,provider=map(load,(a.component_link,a.native_proof,a.provider))
    need(base['completed'] and base['paired_down_carrier'] and native['completed'] and native['native_passed'] and
         native['ordinary_exit_observed'] and native['current_seven_restored_and_native_hashed'] and
         load(load(native['package']['path'])['relink']['path'])['artifact']==base['artifact'],
         'Reuse the exact completed native carrier operands and ordinary exit')
    need(provider['completed'] and provider['GPU_executable_sections_byte_exact'] and
         provider['original_codec_registry_unchanged'] and provider['redirected_resource_pairs']==13 and
         provider['new_global_initializers']==0,'The selected model resource provider is required')
    retained=controls(a.retained_controls,ROOT)
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
        target=a.out/name
        if target.exists():need((a.resume_source_staging or a.resume_link) and all(record(target)[k]==actual[k] for k in ('bytes','sha256')),
                                'An already staged source changed')
        else:shutil.copyfile(src,target)
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
        record(ROOT/'tools/build_iq2_down_ggml_fixture.py')]
    result.update(inputs_before=inputs,source=record(source),commands=[command,*base['commands'][1:3],result['link_command']],
        component_pack=base['component_pack'],parts=base['parts'],original_case_geometry=base['original_case_geometry'],
        component=base['component'],software_proof=base['software_proof'],model_resource_provider=record(a.provider),
        GGML_carrier_ABI=True,GGML_operator_linked=True,model_engine_linked=True,model_loads=0,
        CPU_startup_only_mode=True,driver_code_linked=True,maximum_GPU_dispatches=None,maximum_GGML_graphs=12,
        CPU_heap_cap=64<<20,device_owner_cap=128<<20,new_post_device_controls=0,retained_device_controls=19,
        retained_idle_device_until_ordinary_close=True,paired_down_carrier=True,
        unchanged_retirement_controls_reused=retained,actual_physical_dispatch_audit=callbacks,
        same_selected_Direct_table_mapping_and_incremental_restoration=True,
        linked_driver=base['linked_driver'],successful_driver_whole_archive_preserved=True,
        CPU_Direct_capacity_readmission=True,backend_free_calls=0,persistent_caches=False,
        numerical_negative_ordinary_close_admitted_only_after_all_submitted_graphs_complete=True,
        native_GPU_qualified=False,production_adopted=False,PS5_operations=0)
    result_path.write_text(json.dumps(result,indent=2)+'\n')
    save(a.out/'result.private.json',dict(completed=True,relink=record(result_path),source=record(source),
        compile_command=command,reused_pack=base['component_pack'],new_GPU_graphs=12,PS5_operations=0))
    print(json.dumps(dict(completed=True,GGML_carrier_ABI=True,new_GPU_graphs=12,PS5_operations=0)))


if __name__=='__main__':main()
