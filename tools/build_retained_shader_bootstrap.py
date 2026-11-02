#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build the successful CPU shader bootstrap using actual current CPU providers."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess

from audit_native_imports import audit
from build_performance_quantizer import record
from native_driver import read_archive
from prepare_shared_q4 import REVISION,load

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','cache','current','out'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--bundle-plan',type=Path)
    parser.add_argument('--model-proof',type=Path)
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=False)
    prior=load(args.current/'provenance/native-link.receipt.private.json')
    retained=load(args.current/'provenance/retained-relink-inputs.private.json')
    mapping={r['original_path']:r['path'] for r in retained}
    llvm=args.workspace/'toolchain/llvm-mingw-20261006-ucrt-x86_64/bin'
    providers={}
    predicates={'bootstrap':'qwen_native_bootstrap','fault':'qwen_native_set_fault_report','CRT':'_start',
                'system':'qwen_app::observe_native_system_memory(',
                'integrity':'qwen_app::verify_native_startup_file_direct(',
                'assets':'qwen_app::native_shader_asset_stats(',
                'session':'qwen_app::native_shader_file_registered(',
                'file_native':'qwen_app::open_native_shader_file(',
                'file':'qwen_app::ShaderFileStore::verify(',
                'startup':'qwen_app::read_startup(','SHA256':'sha256_init'}
    for row in retained:
        if Path(row['path']).suffix!='.o':continue
        output=subprocess.check_output([str(llvm/'llvm-nm.exe'),'--demangle','--defined-only','--extern-only',row['path']],text=True)
        names=[s.split(' ',2)[-1] for s in output.splitlines() if ' T ' in s]
        for label,needle in predicates.items():
            if any(n.startswith(needle) if needle.endswith('(') else n==needle for n in names):
                if label in providers:raise ValueError('Ambiguous actual CPU provider: '+label)
                providers[label]=row
    if providers.keys()!=predicates.keys():raise ValueError('Missing actual CPU provider: '+str(predicates.keys()-providers.keys()))
    selected={r['original_path'] for r in providers.values()}
    selected|={r['original_path'] for r in retained if Path(r['original_path']).name in ('shader-locations.o','shader-registry.o')}
    public_main=ROOT/'native/app/native_main.cpp';text=public_main.read_text()
    def function(signature):
        at=text.index(signature);end=text.index('\n}\n',at)+3;return text[at:end]
    start=text.index('static bool boundary_memory_enabled=');end=text.index('\nenum class ReportWriteMode',start)
    (args.out/'mini_shader_boundaries.inc').write_text(text[start:end],encoding='utf-8',newline='\n')
    extracted='\n'.join(function(s) for s in ('static ModelFileIdentity model_file_identity(',
        'static void validate_prior_shader_CPU(','static Json read_prior_shader_CPU(',
        'static Json diagnostic_VM_population(','static void admit_shader_storage_CPU('))
    (args.out/'mini_shader_admission.inc').write_text(extracted,encoding='utf-8',newline='\n')
    # This is the same isolated CPU metadata selector used before GPU setup in
    # the current application. The bootstrap never enters a GPU/model phase.
    mini=ROOT/'native/app/mini_shader_bootstrap.cpp'
    entry='#include <cstdint>\nextern "C" void qwen_app_select_resident_CPU_metadata_scope(bool);\n'+mini.read_text()
    entry=entry.replace('int main(int argc,char **argv) {','int main(int argc,char **argv) {\n    qwen_app_select_resident_CPU_metadata_scope(true);',1)
    bundle=None;extra_inputs=[]
    if args.bundle_plan or args.model_proof:
        if not(args.bundle_plan and args.model_proof):raise ValueError('Original bundle plan and current model proof are both required')
        from native_bundle_restore_entry import compose
        entry,bundle,extra_inputs=compose(entry,args.bundle_plan,args.model_proof,args.out)
    source=args.out/'bootstrap.cpp';source.write_text(entry,encoding='utf-8',newline='\n')
    up=args.cache/('upstream/llama.cpp-'+REVISION);sdk=args.workspace/'toolchain/ps5-sdk-radv/ps5-payload-sdk'
    obj=args.out/'bootstrap.o'
    compile_command=[str(llvm/'clang++.exe'),'--no-default-config','--target=x86_64-sie-ps5','-nostdinc++',
        '-isystem',str(sdk/'target/include/c++/v1'),'-isystem',str(sdk/'target/include'),'-std=c++17',
        '-fexceptions','-fcxx-exceptions','-frtti','-femulated-tls','-fno-stack-protector','-fno-plt','-fPIC',
        '-fdenormal-fp-math=ieee','-O2','-ffunction-sections','-fdata-sections','-DQWEN_NATIVE_PLATFORM=1',
        '-I',str(args.out),'-I',str(ROOT/'native/app'),'-I',str(up/'vendor'),'-I',str(up/'include'),
        '-I',str(up/'ggml/include'),'-I',str(up/'ggml/src/ggml-cpu'),'-c',str(source),'-o',str(obj)]
    donor=next(r for r in retained if Path(r['original_path']).name=='libvulkan-cold-tables.a')
    if record(donor['path'])!={k:donor[k] for k in ('path','bytes','sha256')}:raise ValueError('Current CPU codec donor differs')
    index=read_archive(donor['path']);codec=[]
    with Path(donor['path']).open('rb') as stream:
        for name,symbol in {'adler32.c.o':'adler32','crc32.c.o':'crc32','inffast.c.o':'inflate_fast',
                            'inflate.c.o':'inflateInit_','inftrees.c.o':'inflate_table','zutil.c.o':'zlibVersion'}.items():
            found=[]
            for (member_name,occurrence),member in index.items():
                if member_name!=name:continue
                stream.seek(member['offset']);path=args.out/(name+'.'+str(occurrence)+'.o');path.write_bytes(stream.read(member['bytes']))
                if record(path)['sha256']!=member['sha256']:raise ValueError('CPU codec member changed')
                symbols=subprocess.check_output([str(llvm/'llvm-nm.exe'),'--defined-only','--format=posix',str(path)],text=True)
                if symbol in {line.split()[0] for line in symbols.splitlines() if line.split()}:found.append(path)
            if len(found)!=1:raise ValueError('One actual CPU codec provider required')
            codec.append(found[0])
    libraries={'libc++.a','libc++abi.a','libunwind.a','libps5platform.a','libc.title.a','libclang_rt.builtins-x86_64.a'}
    modules={'libSceLibcInternal.so','libkernel.so','libSceNet.so','libSceSystemService.so'}
    wraps={'fclose','fflush','abort','malloc','calloc','realloc','free','posix_memalign','aligned_alloc',
           'memalign','malloc_usable_size','reallocf','reallocarray','getline','getdelim'}
    command=[];skip=False
    for i,value in enumerate(prior['link_command']):
        if skip:skip=False;continue
        if value=='-T' and prior['link_command'][i+1]==prior['lossless_driver_tables']['linker_script']['path']:
            skip=True;continue
        name=Path(value).name
        if value.endswith('.o') and value not in selected:continue
        if value.endswith('.a') and name not in libraries:continue
        if value.endswith('.so') and name not in modules:continue
        if value.startswith('--wrap=') and value[7:] not in wraps:continue
        if value.startswith('--defsym=') and ('=qwen_' in value or value.startswith('--defsym=kernel_mprotect=')):continue
        if value.startswith('-Map='):value='-Map='+str(args.out/'native-link.private.map')
        command.append(mapping.get(value,value))
    image=args.out/'mini-shader.pie.elf';command[command.index('-o')+1]=str(image)
    at=command.index('--start-group');command[at:at]=[str(obj),*map(str,codec)]
    if '--gc-sections' not in command:command.append('--gc-sections')
    jobs=[compile_command,command]
    for i,job in enumerate(jobs):
        result=subprocess.run(job,capture_output=True,timeout=180,env=dict(os.environ,TMP=str(args.out),TEMP=str(args.out)))
        (args.out/(str(i)+'.private.log')).write_bytes(result.stdout+result.stderr)
        if result.returncode:raise RuntimeError(result.stderr.decode(errors='replace')[-5000:])
    used=[record(Path(p)) for p in command if Path(p).is_file()]
    receipt=dict(artifact=record(image),inputs_before=used,runtime_providers=prior['runtime_providers'])
    save_path=args.out/'receipt.private.json';save_path.write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    imports=audit(args.workspace,args.cache,args.out)
    if imports['missing']:raise ValueError('CPU imports missing: '+str(imports['missing']))
    symbols=subprocess.check_output([str(llvm/'llvm-nm.exe'),'--defined-only','--format=posix',str(image)],text=True)
    forbidden=re.compile(r'^(?:vk[A-Z]|radv_|aco_|llama_|ggml_(?:backend|vk)_|qwen_native_gpu_)')
    if any(forbidden.match(line.split()[0]) for line in symbols.splitlines() if line.split()):raise ValueError('GPU/model implementation leaked into the CPU bootstrap')
    if any(n.startswith(('sceAgc','sceVideoOut')) for n in imports['resolved']):raise ValueError('GPU/display API in the CPU bootstrap')
    entry_imports=subprocess.check_output([str(llvm/'llvm-nm.exe'),'--undefined-only',str(obj)],text=True)
    if bundle and ('statfs' in imports['resolved'] or re.search(r'\b(?:lstat|statfs)\b',entry_imports)):
        raise ValueError('New native copy entry must use descriptor identity and external capacity observation')
    if bundle:bundle['new_entry_path_stat_imports']=0
    report=dict(completed=True,baseline_relink=False,artifact=record(image),CPU_only=True,driver_code_linked=False,
                model_engine_linked=False,actual_current_CPU_providers={k:record(r['path']) for k,r in providers.items()},
                inputs_before=used,real_module_import_audit=imports,commands=jobs,
                source_inputs=[record(p) for p in (Path(__file__),source,public_main,mini,args.out/'mini_shader_boundaries.inc',args.out/'mini_shader_admission.inc')]+extra_inputs,
                driver_revision='872cc1264ad8ba5d6b888b092968fa5858a38c58',driver_profile='cumulative-idle',
                current_run_all_asset_bootstrap=True,PS5_operations=0,native_execution=False,production_adopted=False)
    if bundle:report['required_bundle_restore']=bundle
    save_path.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    (args.out/'result.private.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(CPU_only_link_passed=True,actual_CPU_providers=len(providers),GPU_or_model_symbols=0,
                         missing_imports=0,bytes=report['artifact']['bytes'],PS5_operations=0)))


if __name__=='__main__':main()
