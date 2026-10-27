#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Link CPU-only original GGUF attribution from exact CPU objects; never deploy."""
import argparse,json,os,re,subprocess
from pathlib import Path
from build_preservation_integrity import record
from audit_native_imports import audit
from native_driver import read_archive
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('workspace','cache','qualified-native','out'):p.add_argument('--'+k,type=Path,required=True)
    p.set_defaults(all_assets_bootstrap=False)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    prior=json.loads(a.qualified_native.read_text());main_source=ROOT/'native/app/native_main.cpp';source=main_source.read_text()
    def function(signature):
        start=source.index(signature);end=source.index('\n}\n',start)+3
        return source[start:end]
    counters=source[source.index('static qwen_app::MetadataMemoryProbe metadata_memory;'):source.index('// A required link symbol')]
    extracted=counters+'\n'+'\n'.join(function(sig)for sig in ('static std::string model_file(',
        'static ModelFileIdentity model_file_identity(','static ModelFileIdentity model_directory_identity(',
        'static Json diagnostic_VM_population(','static void inspect_container('))
    (a.out/'mini_metadata_inspection.inc').write_text(extracted,newline='\n')
    needed={'native_fault.cpp','native_bootstrap.cpp','native_crt.cpp','system_memory.cpp','direct_integrity.cpp',
        'sha256_backend.cpp','startup.cpp','runtime_admission.cpp','direct_metadata.cpp'}
    commands=prior['compile_commands'];chosen={}
    for c in commands:
        if '-c'in c:
            name=Path(c[c.index('-c')+1]).name
            if name in needed:chosen[name]=Path(c[c.index('-o')+1])
    if set(chosen)!=needed:raise ValueError('Qualified CPU object set incomplete')
    inputs_by_path={r['path']:r for r in prior['inputs_before']}
    for obj in chosen.values():
        if record(obj)!=inputs_by_path.get(str(obj)):raise ValueError('Qualified CPU object changed: '+obj.name)
    # Reused CPU objects must retain their actual application ABI. Unrelated
    # inference headers may evolve without forcing another CPU/driver rebuild.
    prior_sources={Path(r['path']).resolve():r for r in prior['application_sources']}
    prior_headers={Path(r['path']).resolve():r for r in prior['application_headers']}
    CPU_dependencies=set()
    def dependencies(path):
        path=path.resolve()
        if path in CPU_dependencies:return
        CPU_dependencies.add(path)
        expected=prior_sources.get(path)or prior_headers.get(path)
        if expected is None or record(path)!=expected:raise ValueError('Reused CPU source/header ABI changed: '+str(path))
        for name in re.findall(r'^\s*#include\s+"([^"]+)"',path.read_text(),re.M):
            candidates=(path.parent/name,ROOT/'native/app'/name)
            for target in candidates:
                if target.is_file()and target.resolve().is_relative_to(ROOT):dependencies(target);break
    for name in sorted(needed):dependencies(ROOT/'native/app'/name)
    selected_objects=set(map(str,chosen.values()))
    for obj in selected_objects:
        if record(obj)!=inputs_by_path.get(obj):raise ValueError('Qualified linked object changed')
    donor=next(Path(x)for x in prior['link_command']if Path(x).name=='libggml-base.a')
    donor_record=record(donor);codec=[];codec_members=[]
    allowed_archives={'libc++.a','libc++abi.a','libunwind.a','libps5platform.a','libc.title.a','libclang_rt.builtins-x86_64.a','libggml-base.a'}
    providers={'libSceLibcInternal.so','libkernel.so','libSceNet.so','libSceSystemService.so'}
    keep_wrap={'fclose','fflush','abort','malloc','calloc','realloc','free','posix_memalign','aligned_alloc',
        'memalign','malloc_usable_size','reallocf','reallocarray','getline','getdelim','gguf_init_from_file'}
    command=[]
    for x in prior['link_command']:
        q=Path(x)
        if x.endswith('.o')and x not in selected_objects:continue
        if x.endswith('.a')and q.name not in allowed_archives:continue
        if x.endswith('.so')and q.name not in providers:continue
        if x.startswith('--wrap=')and x[len('--wrap='):]not in keep_wrap:continue
        if x.startswith('--defsym=')and ('=qwen_'in x or x.startswith('--defsym=kernel_mprotect=')):continue
        if x.startswith('-Map='):x='-Map='+str(a.out/'native-link.private.map')
        command.append(x)
    image=a.out/'mini-shader.pie.elf';command[command.index('-o')+1]=str(image)
    main_cmd=next(c.copy()for c in commands if '-c'in c and Path(c[c.index('-c')+1]).name=='native_main.cpp')
    mini=ROOT/'native/app/mini_metadata_memory.cpp';obj=a.out/'mini_shader_memory.o'
    main_cmd[main_cmd.index('-c')+1]=str(mini);main_cmd[main_cmd.index('-o')+1]=str(obj);main_cmd+=['-I',str(a.out)]
    at=command.index('--start-group');command[at:at]=[str(obj),*map(str,codec)]
    fixed_files=[Path(__file__),mini,main_source,a.qualified_native,donor,a.out/'mini_metadata_inspection.inc',*CPU_dependencies]
    fixed_files+=[Path(x)for x in command if Path(x).is_file()and Path(x).suffix in ('.o','.a','.so','.exe','.ld')]
    fixed_files+=list((ROOT/'native/app').glob('*.h'));fixed=[record(f)for f in sorted(set(fixed_files))]
    env=dict(os.environ,PATH=str(a.workspace/'toolchain/msys-clang64/clang64/bin')+os.pathsep+os.environ.get('PATH',''))
    policy_controls=None
    if True:
        test=ROOT/'tests/mini_metadata_memory_policy.cpp';fixed_files.append(test)
        fixed=[record(f)for f in sorted(set(fixed_files))]
        up=a.cache/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569'
        host=a.workspace/'toolchain/msys-clang64/clang64/bin';exe=a.out/'bootstrap-policy.exe'
        commands=[[str(host/'clang++.exe'),'-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'native/app'),
            '-I',str(up/'vendor'),str(test),'-o',str(exe)],[str(exe)]]
        for i,c in enumerate(commands):
            r=subprocess.run(c,cwd=ROOT,capture_output=True,timeout=120,env=env);(a.out/f'policy-{i}.private.log').write_bytes(r.stdout+r.stderr)
            if r.returncode:raise RuntimeError('CPU bootstrap policy: '+r.stderr.decode(errors='replace')[-2400:])
        policy_controls=json.loads(r.stdout)
    for i,c in enumerate((main_cmd,command)):
        r=subprocess.run(c,cwd=ROOT,capture_output=True,timeout=180,env=env);(a.out/f'build-{i}.private.log').write_bytes(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace')[-4000:])
    if fixed!=[record(f)for f in sorted(set(fixed_files))]:raise ValueError('A frozen CPU build input changed')
    # The audit is unchanged and checks actual strong module providers.
    receipt=dict(artifact=record(image),inputs_before=fixed,runtime_providers=prior['runtime_providers'])
    (a.out/'receipt.private.json').write_text(json.dumps(receipt,indent=2)+'\n')
    imported=audit(a.workspace,a.cache,a.out)
    if imported['missing']:raise ValueError('Missing real CPU imports: '+str(imported['missing']))
    llvm=Path(main_cmd[0]).parent
    names=subprocess.check_output([str(llvm/'llvm-nm.exe'),'--defined-only','--format=posix',str(image)],text=True)
    forbidden=re.compile(r'^(?:vk[A-Z]|radv_|aco_|llama_|ggml_(?:backend_vk|vk)_|qwen_native_gpu_)')
    if any(forbidden.match(line.split()[0])for line in names.splitlines()if line.split()):
        raise ValueError('Inference or Vulkan implementation leaked into CPU-only title')
    if any(n.startswith(('sceAgc','sceVideoOut'))for n in imported['resolved']):raise ValueError('GPU/display API in CPU-only title')
    receipt.update(schema='ps5-qwen-mini-metadata-build-v1',commands=[main_cmd,command],real_module_import_audit=imported,
        link_returncode=0,input_hashes_stable=True,original_GGUF_inspector_extracted_verbatim=True,CPU_only=True,
        driver_code_linked=False,model_engine_linked=False,GGUF_metadata_library=donor_record,CPU_metadata_only=True,
        driver_source_revision='872cc1264ad8ba5d6b888b092968fa5858a38c58',driver_source_profile='cumulative-idle',
        GPU_calls=0,source_workers=0,PS5_operations=0,CI_runs=0)
    receipt['current_run_all_asset_bootstrap']=a.all_assets_bootstrap
    receipt['CPU_bootstrap_policy_controls']=policy_controls
    receipt['reused_CPU_source_and_transitive_header_ABI']=[record(f)for f in sorted(CPU_dependencies)]
    (a.out/'receipt.private.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(dict(CPU_only_link_passed=True,bytes=receipt['artifact']['bytes'],missing_imports=0,driver_code_linked=False,PS5_operations=0)),flush=True)
if __name__=='__main__':main()
