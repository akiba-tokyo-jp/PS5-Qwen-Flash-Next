#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Adopt the completed pre-CXX CPU table backing in one finite model package."""
import argparse
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from audit_expert_all_q2_safety import body
from build_performance_quantizer import record
from build_speculative_batch_probe import once
from driver_table_storage import audit_linked_storage
from external_zero_layout import exclude
from native_dispatch import ELF
from start_success_route import load,need,save
ROOT=Path(__file__).resolve().parents[1]


def adoption_header(text):
    text='#include "early_CPU_tables_adoption.h"\n'+text
    start=text.index('    const auto pool=sceKernelGetDirectMemorySize();')
    end=text.index('    owner.free_after=observe_native_system_memory()',start)
    text=text[:start]+'''    const auto*early=qwen_early_CPU_tables_result();
    require_early_CPU_table_backing(early,begin,end,owner.allocated_bytes);
    const auto pool=sceKernelGetDirectMemorySize();std::int64_t available_start=-1;std::size_t available=0;
    if(pool<=0||sceKernelAvailableDirectMemorySize(0,pool,65536,&available_start,&available)||available_start<0||
       available<(256ull<<20))throw std::runtime_error("Adopted CPU tables cannot retain the original Direct reserve");
    owner.available_before=early->available_before;owner.physical=early->physical;
    owner.allocated=true;owner.mapped=true;owner.free_after_map=before.kernel_free;
    // The pre-CXX constructors already own this exact CPU Direct allocation.
    // Preserve its backing and verify no application initializer changed it.
    const volatile unsigned char*zero=plan.begin;
    for(std::size_t i=0;i<early->mapped_bytes;++i)if(zero[i])
        throw std::runtime_error("An original initializer changed the early zero table range; retain backing");
    owner.zeroed=true;
    qwen_native_stage("original_CPU_Direct_table_backing_adopted_no_second_allocation_GPU_not_started");
'''+text[end:]
    need('sceKernelAllocateDirectMemory(' not in text and 'sceKernelMapDirectMemory(' not in text,
         'The model must adopt the existing backing without a second allocation or mapping')
    return text


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','model-package','CPU-package','CPU-completion','CPU-controls','out'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--reuse-adoption-controls',type=Path)
    p.add_argument('--finish-entry',action='store_true',help='Reuse the completed identical entry and controls after a host link-only failure')
    a=p.parse_args();package=load(a.model_package);CPU=load(a.CPU_package);done=load(a.CPU_completion);controls=load(a.CPU_controls)
    early=CPU['early_CPU_tables'];linked=load(package['relink']['path']);profile=load(package['effective_application_policy']['profile']['path'])
    need(package['completed'] and package['normalized_SELF_roundtrip_equal'] and
        profile['kind']=='headless-model-audit' and profile['headless_requests']==3 and profile['model_and_GPU_guards_preserved'],
        'One original finite three-request model package is required')
    need(done['completed'] and done['native_requests']==0 and done['kind']=='CPU-startup-staging-memory' and
        load(done['terminal']['path'])['candidate_SELF_sha256']==CPU['SELF']['sha256'] and
        load(done['closure']['path'])['current_seven_restored_and_native_hashed'] and
        load(done['closure']['path'])['ordinary_exit_observed'] and not done['unknown_completion'] and
        load(done['early_CPU_tables_completion']['path'])['whole_zero_SHA256_and_subsequent_FNV_passed'] and
        controls['completed'] and controls['package']==record(a.CPU_package) and
        controls['native_body_positive']==1 and controls['native_body_refusals']==16 and
        controls['close_boundary_positive']==2 and controls['close_boundary_refusals']==9,
        'The exact CPU prelude must already have completed all32 constructors and ordinary restoration')
    need(record(early['source']['path'])==early['source'] and record(early['header']['path'])==early['header'] and
        record(early['manifest']['path'])==early['manifest'] and record(linked['artifact']['path'])==linked['artifact'],
        'Frozen CPU prelude and selected model link must be unchanged')
    a.out.mkdir(parents=True,exist_ok=a.finish_entry)
    def freeze(path,data):
        if path.exists():need(a.finish_entry and path.read_bytes()==data,'A frozen compiled entry input changed')
        else:path.write_bytes(data)
    selected=load(a.current/'provenance/selected-entry-build.private.json');original=load(selected['application_policy']['path'])
    base_dir=Path(original['source']['path']).parent;model_dir=Path(profile['source']['path']).parent
    for folder in (base_dir,model_dir):
        for path in folder.glob('*.h'):
            if path.name!='resident_direct_tables.h':freeze(a.out/path.name,path.read_bytes())
    for name in ('early_CPU_tables.h','early_CPU_tables_adoption.h'):freeze(a.out/name,(ROOT/'native/app'/name).read_bytes())
    header=a.out/'resident_direct_tables.h'
    original_header=model_dir/header.name if (model_dir/header.name).exists() else base_dir/header.name
    freeze(header,adoption_header(original_header.read_text()).encode())
    commands=[];env=dict(os.environ,TMP=str(a.out),TEMP=str(a.out))
    def run(job,label):
        job=list(map(str,job));commands.append(job)
        if a.finish_entry and label in ('adoption-compile','adoption-controls','entry-compile'):
            log=a.out/(label+'.private.log');need(log.is_file(),'Completed immutable host log required')
            if '-o' in job:
                target=Path(job[job.index('-o')+1]);need(target.is_file() and not log.read_bytes(),'Previously successful host compilation required')
                inputs=[p for p in a.out.iterdir() if p.suffix in ('.h','.cpp')]
                need(all(p.stat().st_mtime_ns<=target.stat().st_mtime_ns for p in inputs) or label=='adoption-compile',
                     'Compiled native source/header must not change after the accepted entry')
            return log.read_bytes()
        if a.finish_entry and label=='link' and (a.out/'model.pie.elf').is_file() and not(a.out/'link.private.log').read_bytes():
            return b''
        r=subprocess.run(job,capture_output=True,timeout=240,env=env)
        (a.out/(label+'.private.log')).write_bytes(r.stdout+r.stderr)
        need(not r.returncode,(r.stdout+r.stderr).decode(errors='replace')[-4000:]);return r.stdout
    test=ROOT/'tests/early_CPU_tables_adoption_test.cpp';adoption=ROOT/'native/app/early_CPU_tables_adoption.h'
    if a.reuse_adoption_controls:
        prior=load(a.reuse_adoption_controls)
        need(prior['completed'] and prior['adoption_header']==record(adoption) and prior['adoption_test']==record(test) and
            prior['adoption_controls']==dict(positive_controls=1,negative_controls=16,CPU_mapping_API_calls=0),
            'Only identical completed adoption controls may be reused')
        checked=prior['adoption_controls']
    else:
        host=a.workspace/'toolchain/msys-clang64/clang64/bin';exe=a.out/'adoption-check.exe'
        run([host/'clang++.exe','-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',ROOT/'native/app',test,'-o',exe],'adoption-compile')
        env['PATH']=str(host)+os.pathsep+os.environ.get('PATH','');checked=json.loads(run([exe],'adoption-controls'))
        need(checked==dict(positive_controls=1,negative_controls=16,CPU_mapping_API_calls=0),'All new ownership controls must pass')
    source=a.out/'entry.private.cpp';text=Path(profile['source']['path']).read_text()
    freeze(source,text.encode());entry=a.out/'entry.o'
    ec=next(job for job in selected['commands'] if '-c' in job and job[job.index('-c')+1].endswith('entry.private.cpp')).copy()
    view=load(ec[ec.index('-ivfsoverlay')+1])
    for row in view['roots']:
        path=a.out/Path(row['external-contents']).name
        if path.exists():row['external-contents']=path.resolve().as_posix()
    overlay=a.out/'selected-view.private.json'
    if overlay.exists():need(a.finish_entry and load(overlay)==view,'The compiled VFS header view changed')
    else:save(overlay,view)
    ec[1:1]=['-I',str(a.out)];ec[ec.index('-ivfsoverlay')+1]=str(overlay)
    ec[ec.index('-c')+1]=str(source);ec[ec.index('-o')+1]=str(entry)
    if '-MF' in ec:ec[ec.index('-MF')+1]=str(a.out/'entry.private.d')
    run(ec,'entry-compile')
    oldCPU=load(CPU['relink']['path']);add=[]
    for name in ('early-tables.o','boundary.o'):
        matches=[row for row in oldCPU['new_inputs'] if Path(row['path']).name==name]
        need(len(matches)==1 and record(matches[0]['path'])==matches[0],'One exact already qualified CPU prelude object required');add.append(matches[0])
    if 'ai_sha256_init' not in ELF(Path(linked['artifact']['path'])).symbols:
        matches=[row for row in oldCPU['new_inputs'] if Path(row['path']).name=='sha256.o']
        need(len(matches)==1 and record(matches[0]['path'])==matches[0],'Reuse the exact already compiled CPU prelude SHA provider');add.append(matches[0])
    script=a.out/'early-tables.ld';freeze(script,Path(early['linker_script']['path']).read_bytes())
    link=linked['link_command'].copy();old_entry=profile['entry_artifact']['path']
    need(link.count(old_entry)==1,'One exact selected entry must be replaced')
    link=[str(entry) if x==old_entry else x for x in link]
    at=next(i for i in range(len(link)-1) if link[i]=='-T' and Path(link[i+1]).name=='tables.ld');link[at+1]=str(script)
    image=a.out/'model.pie.elf';link[link.index('-o')+1]=str(image)
    link=[('-Map='+str(a.out/'native-link.private.map')) if x.startswith('-Map=') else x for x in link]
    link[1:1]=[row['path'] for row in add];run(link,'link')
    native=ELF(image);begin=native.symbols['__qwen_driver_tables_start']['value'];end=native.symbols['__qwen_early_tables_end']['value']
    _,layout=exclude(native.data,begin,end)
    original_tables=load(a.current/'provenance/native-link.receipt.private.json')['lossless_driver_tables']
    geometry=audit_linked_storage(image,original_tables)
    start=native.symbols['__init_array_start']['value'];finish=native.symbols['__init_array_end']['value']
    ctors=[native.pointer(at) for at in range(start,finish,8)]
    baseline=ELF(Path(linked['artifact']['path']))
    old_count=(baseline.symbols['__init_array_end']['value']-baseline.symbols['__init_array_start']['value'])//8
    need(len(ctors)==old_count+2 and ctors[:4]==[native.symbols[n]['value'] for n in
        ('__cpu_indicator_init','_GLOBAL__I_000100','early_CPU_tables_map','early_CPU_tables_check')],
        'Preserve both platform initializers and the exact qualified pre-application CPU prelude')
    for name in ('observed_system_headroom','require_model_CPU_budget','wait_for_initial_model_CPU_budget',
        'model_file_identity','model_directory_identity','resident_reset_empty_context','bind_resident_main_SELF'):
        need(body(text,name)==body(Path(original['source']['path']).read_text(),name),'An original model/physical/SELF guard changed')
    scope=dict(completed_host_layout=True,control_native=record(image),layout=layout,source=early['source'],header=early['header'],
        manifest=early['manifest'],original_table_geometry=geometry,original_CPU_package=record(a.CPU_package),
        original_CPU_completion=record(a.CPU_completion),CPU_host_controls=record(a.CPU_controls),
        adoption_header=record(adoption),adoption_test=record(test),adoption_controls=checked,
        adoption_controls_reused=record(a.reuse_adoption_controls) if a.reuse_adoption_controls else None,
        mapped_CPU_Direct_bytes=9502720,original_table_bytes=9486336,additional_CPU_constructors=2,
        original_model_constructors=old_count,total_constructors=old_count+2,
        strict_failure_park_before_original_application_CXX=True,model_reuses_exact_early_backing=True,
        private_libc_heap_bytes=8<<20,private_libc_heap_extension=False,original_model_CPU_GPU_and_source_guards_unchanged=True,
        prelude_GPU_and_source_operations=0,native_model_qualification_pending=True)
    profile=copy.deepcopy(profile);profile.update(source=record(source),entry_artifact=record(entry),early_model_CPU_tables=scope)
    policy=a.out/'application-policy.private.json';save(policy,profile)
    result=copy.deepcopy(linked);result.update(artifact=record(image),link_command=link,
        new_inputs=[row for row in linked['new_inputs'] if row['path']!=old_entry]+[record(entry)]+add,
        inputs=linked['inputs']+[record(header),record(source),record(script)],baseline_relink=False,
        exact_current_native_ELF_reproduced=False,effective_application_policy=dict(kind='headless-model-audit',
            profile=record(policy),overrides=profile['overrides']),early_model_CPU_tables=scope)
    receipt=a.out/'relink.private.json';save(receipt,result)
    identity=package['required_bundle_identity_audit']['provider']
    run([sys.executable,'-B',ROOT/'tools/package_retained_current.py','--workspace',a.workspace,'--current',a.current,
        '--relink',receipt,'--out',a.out/'SELF','--formatter-from',a.current/'provenance/current-package.private.json',
        '--identity-provider',identity['path']],'SELF')
    save(a.out/'result.private.json',dict(completed=True,package=record(a.out/'SELF/result.private.json'),
        parent_model_package=record(a.model_package),CPU_completion=record(a.CPU_completion),adoption_header=record(adoption),
        adoption_test=record(test),adoption_controls=checked,commands=commands,PS5_operations=0,native_qualified=False,production_adopted=False))
    print(dict(completed=True,model_package=1,new_adoption_controls=0 if a.reuse_adoption_controls else 17,PS5_operations=0))


if __name__=='__main__':main()
