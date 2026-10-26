#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Link a CPU-only shader title from qualified unchanged CPU objects; never deploy."""
import argparse,json,os,re,subprocess
from pathlib import Path
from build_preservation_integrity import record
from audit_native_imports import audit
from native_driver import read_archive
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('workspace','cache','qualified-native','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    prior=json.loads(a.qualified_native.read_text());main_source=ROOT/'native/app/native_main.cpp';source=main_source.read_text()
    def function(signature):
        start=source.index(signature);end=source.index('\n}\n',start)+3
        return source[start:end]
    start=source.index('static bool boundary_memory_enabled=');end=source.index('\nenum class ReportWriteMode',start)
    (a.out/'mini_shader_boundaries.inc').write_text(source[start:end],newline='\n')
    extracted='\n'.join(function(s)for s in ('static ModelFileIdentity model_file_identity(',
        'static void validate_prior_shader_CPU(','static Json read_prior_shader_CPU(',
        'static Json diagnostic_VM_population(','static void admit_shader_storage_CPU('))
    (a.out/'mini_shader_admission.inc').write_text(extracted,newline='\n')
    needed={'native_fault.cpp','native_bootstrap.cpp','native_crt.cpp','system_memory.cpp','direct_integrity.cpp',
        'shader_assets.cpp','shader_file.cpp','shader_file_session.cpp','shader_file_native.cpp','sha256_backend.cpp','startup.cpp'}
    commands=prior['compile_commands'];chosen={}
    for c in commands:
        if '-c'in c:
            name=Path(c[c.index('-c')+1]).name
            if name in needed:chosen[name]=Path(c[c.index('-o')+1])
    if set(chosen)!=needed:raise ValueError('Qualified CPU object set incomplete')
    inputs_by_path={r['path']:r for r in prior['inputs_before']}
    for obj in chosen.values():
        if record(obj)!=inputs_by_path.get(str(obj)):raise ValueError('Qualified CPU object changed: '+obj.name)
    selected_objects=set(map(str,chosen.values()))
    selected_objects|={x for x in prior['link_command']if Path(x).name in ('shader-locations.o','shader-registry.o')}
    for obj in selected_objects:
        if record(obj)!=inputs_by_path.get(obj):raise ValueError('Qualified linked object changed')
    donor=Path(prior['linked_driver']['archive_path']);donor_record=record(donor)
    if donor_record['sha256']!='b57fe26e969940d147be05c1ffae830503d4865877281dffe03af32328f49925':
        raise ValueError('Exact qualified CPU codec donor required')
    index=read_archive(donor);codec=[];codec_members=[]
    llvm=Path(prior['compiler']['path']).parent if isinstance(prior['compiler'],dict)else Path(prior['compiler']).parent
    required_symbols={'adler32.c.o':'adler32','crc32.c.o':'crc32','inffast.c.o':'inflate_fast',
        'inflate.c.o':'inflateInit_','inftrees.c.o':'inflate_table','zutil.c.o':'zlibVersion'}
    with donor.open('rb')as stream:
        for name,symbol in required_symbols.items():
            matching=[]
            for (n,occurrence),member in index.items():
                if n!=name:continue
                stream.seek(member['offset']);target=a.out/(name+'.'+str(occurrence)+'.o');target.write_bytes(stream.read(member['bytes']))
                if record(target)['sha256']!=member['sha256']:raise ValueError('CPU codec member changed')
                raw=subprocess.check_output([str(llvm/'llvm-nm.exe'),'--defined-only','--format=posix',str(target)],text=True)
                if symbol in {line.split()[0]for line in raw.splitlines()if line.split()}:
                    matching.append((target,occurrence))
            if len(matching)!=1:raise ValueError('A unique CPU codec symbol provider is required: '+symbol)
            target,occurrence=matching[0];codec.append(target);codec_members.append(dict(name=name,occurrence=occurrence,symbol=symbol,artifact=record(target)))
    allowed_archives={'libc++.a','libc++abi.a','libunwind.a','libps5platform.a','libc.title.a','libclang_rt.builtins-x86_64.a'}
    providers={'libSceLibcInternal.so','libkernel.so','libSceNet.so','libSceSystemService.so'}
    keep_wrap={'fclose','fflush','abort','malloc','calloc','realloc','free','posix_memalign','aligned_alloc',
        'memalign','malloc_usable_size','reallocf','reallocarray','getline','getdelim'}
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
    mini=ROOT/'native/app/mini_shader_memory.cpp';obj=a.out/'mini_shader_memory.o'
    main_cmd[main_cmd.index('-c')+1]=str(mini);main_cmd[main_cmd.index('-o')+1]=str(obj);main_cmd+=['-I',str(a.out)]
    at=command.index('--start-group');command[at:at]=[str(obj),*map(str,codec)]
    fixed_files=[Path(__file__),mini,main_source,a.qualified_native,donor,a.out/'mini_shader_boundaries.inc',a.out/'mini_shader_admission.inc']
    fixed_files+=[Path(x)for x in command if Path(x).is_file()and Path(x).suffix in ('.o','.a','.so','.exe','.ld')]
    fixed_files+=list((ROOT/'native/app').glob('*.h'));fixed=[record(f)for f in sorted(set(fixed_files))]
    env=dict(os.environ,PATH=str(a.workspace/'toolchain/msys-clang64/clang64/bin')+os.pathsep+os.environ.get('PATH',''))
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
    forbidden=re.compile(r'^(?:vk[A-Z]|radv_|aco_|llama_|ggml_(?:backend|vk)_|qwen_native_gpu_)')
    if any(forbidden.match(line.split()[0])for line in names.splitlines()if line.split()):
        raise ValueError('Inference or Vulkan implementation leaked into CPU-only title')
    if any(n.startswith(('sceAgc','sceVideoOut'))for n in imported['resolved']):raise ValueError('GPU/display API in CPU-only title')
    receipt.update(schema='ps5-qwen-mini-shader-build-v1',commands=[main_cmd,command],real_module_import_audit=imported,
        link_returncode=0,input_hashes_stable=True,shared_shader_helper_extracted_verbatim=True,CPU_only=True,
        driver_code_linked=False,model_engine_linked=False,CPU_codec_members=codec_members,CPU_codec_donor=donor_record,
        driver_source_revision='872cc1264ad8ba5d6b888b092968fa5858a38c58',driver_source_profile='cumulative-idle',
        GPU_calls=0,source_workers=0,PS5_operations=0,CI_runs=0)
    (a.out/'receipt.private.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(dict(CPU_only_link_passed=True,bytes=receipt['artifact']['bytes'],missing_imports=0,driver_code_linked=False,PS5_operations=0)),flush=True)
if __name__=='__main__':main()
