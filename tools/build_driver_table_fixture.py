#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Relink the isolated driver fixture from frozen application inputs; no execution."""
import argparse,json,os,subprocess
from pathlib import Path
from shader_storage import record
from audit_native_imports import audit
from native_dispatch import audit as audit_dispatch
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in('workspace','cache','qualified-native','out'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--compact-code',action='store_true',help='Separately record size-oriented fixture compilation and address-safe identical-code folding')
    p.add_argument('--table-storage-manifest',type=Path,help='An explicit exact-byte extension of the immutable donor table set')
    p.add_argument('--refresh-driver-table-runtime',action='store_true',help='Relink the current explicitly fingerprinted restoration wrapper')
    a=p.parse_args();prior=json.loads(a.qualified_native.read_text())
    if not prior.get('lossless_driver_tables_link_map_passed'):raise ValueError('The exact cold-table native link is required')
    for row in prior['inputs_before']+[prior['artifact']]:
        if record(row['path'])!=row:raise ValueError('A qualified native input changed')
    a.out.mkdir(parents=True,exist_ok=False);source=(ROOT/'native/app/native_main.cpp').read_text()
    def function(signature):
        at=source.index(signature);end=source.index('\n}\n',at)+3;return source[at:end]
    at=source.index('static bool boundary_memory_enabled=');end=source.index('\nenum class ReportWriteMode',at)
    (a.out/'mini_shader_boundaries.inc').write_text(source[at:end],newline='\n')
    helper='\n'.join(function(s)for s in('static ModelFileIdentity model_file_identity(','static void validate_prior_shader_CPU(',
        'static Json read_prior_shader_CPU(','static Json diagnostic_VM_population(','static void admit_shader_storage_CPU('))
    (a.out/'mini_shader_admission.inc').write_text(helper,newline='\n')
    compile_cmd=next(c.copy()for c in prior['compile_commands']if '-c'in c and Path(c[c.index('-c')+1]).name=='native_main.cpp')
    old=compile_cmd[compile_cmd.index('-o')+1];obj=a.out/'fixture.o';image=a.out/'driver-table-fixture.pie.elf'
    compile_cmd[compile_cmd.index('-c')+1]=str(ROOT/'native/app/driver_table_fixture.cpp')
    compile_cmd[compile_cmd.index('-o')+1]=str(obj);compile_cmd+=['-I',str(a.out),'-I',str(a.workspace/'toolchain/ps5-sdk-radv/ps5-payload-sdk/target/include')]
    if a.compact_code:compile_cmd=[v for v in compile_cmd if v not in('-O1','-O2','-O3')]+['-Oz']
    command=[str(obj)if v==old else v for v in prior['link_command']]
    table_storage=prior['lossless_driver_tables'];extra_commands=[];extra_inputs=[]
    if a.table_storage_manifest:
        from driver_table_storage import validate
        table_storage=validate(a.table_storage_manifest,prior['lossless_driver_tables']['source_archive']['path'])
        for key in ('assembly','registry'):
            c=next(c.copy()for c in prior['compile_commands']if '-c'in c and c[c.index('-c')+1]==prior['lossless_driver_tables'][key]['path'])
            old_object=c[c.index('-o')+1];c[c.index('-c')+1]=table_storage[key]['path']
            c[c.index('-o')+1]=str(a.out/(key+'.o'));extra_commands.append(c)
            command=[c[c.index('-o')+1]if v==old_object else v for v in command]
        swaps={prior['lossless_driver_tables'][key]['path']:table_storage[key]['path']for key in('archive','linker_script')}
        command=[swaps.get(v,v)for v in command]
        extra_inputs=[record(a.table_storage_manifest),*[table_storage[k]for k in('archive','pool','assembly','registry','linker_script','additional_cold_member')]]
    if a.refresh_driver_table_runtime:
        c=next(c.copy()for c in prior['compile_commands']if '-c'in c and Path(c[c.index('-c')+1]).name=='driver_tables.cpp')
        old_object=c[c.index('-o')+1];c[c.index('-o')+1]=str(a.out/'driver-table-runtime.o');extra_commands.append(c)
        command=[c[c.index('-o')+1]if v==old_object else v for v in command]
        extra_inputs += [record(ROOT/'native/app'/n)for n in('driver_tables.cpp','driver_tables.h','driver_table_restore.h','system_memory.h')]
    command[command.index('-o')+1]=str(image)
    command=[('-Map='+str(a.out/'native-link.private.map'))if v.startswith('-Map=')else v for v in command]
    if a.compact_code:command+=['--icf=safe']
    inputs=[record(Path(__file__)),record(a.qualified_native),record(ROOT/'native/app/driver_table_fixture.cpp'),
        *[record(f)for f in a.out.glob('*.inc')],*prior['inputs_before'],*extra_inputs]
    env=dict(os.environ,PATH=str(a.workspace/'toolchain/msys-clang64/clang64/bin')+os.pathsep+os.environ.get('PATH',''))
    for i,c in enumerate([compile_cmd,*extra_commands,command]):
        r=subprocess.run(c,env=env,capture_output=True,timeout=600);(a.out/f'build-{i}.private.log').write_bytes(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace')[-4500:])
    for row in inputs:
        if record(row['path'])!=row:raise ValueError('A frozen driver fixture input changed')
    receipt=dict(schema='ps5-qwen-driver-table-fixture-link-v1',artifact=record(image),inputs_before=inputs,
        runtime_providers=prior['runtime_providers'],linked_driver=prior['linked_driver'],driver=prior['driver'],
        lossless_driver_tables=table_storage,shader_resource_manifest=prior['shader_resource_manifest'],
        source_parent=record(a.qualified_native),compile_command=compile_cmd,link_command=command,
        compact_code=a.compact_code,
        refreshed_driver_table_runtime=a.refresh_driver_table_runtime,
        GPU_graphs=1,model_loaded=False,model_engine_execution=False,console_access=False,PS5_operations=0)
    target=a.out/'receipt.private.json';target.write_text(json.dumps(receipt,indent=2)+'\n')
    imports=audit(a.workspace,a.cache,a.out)
    if imports['missing']:raise ValueError('Actual native imports are missing: '+str(imports['missing']))
    llvm=Path(prior['compiler']['path']).parent
    dispatch=audit_dispatch(a.workspace,a.workspace/'driver-work/PS5-Vulkan-Inference-qwen-872cc126',image,a.out/'dispatch')
    if not dispatch.get('passed'):raise ValueError('Required native physical dispatch callbacks are missing')
    names=subprocess.check_output([str(llvm/'llvm-nm.exe'),'--defined-only','--demangle',str(image)],text=True)
    if any(v in names for v in('llama_model_load_from_file','llama_decode(')):
        raise ValueError('A full-model entry leaked into the minimal driver fixture')
    receipt.update(real_module_import_audit=imports,native_dispatch_audit=dispatch)
    from driver_table_storage import audit_linked_storage
    receipt['lossless_driver_table_geometry']=audit_linked_storage(image,table_storage)
    target.write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(dict(native_driver_fixture_link_passed=True,bytes=image.stat().st_size,PS5_operations=0)))
if __name__=='__main__':main()
