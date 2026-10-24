#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compile lossless shader resources against unchanged driver and engine controls."""
import argparse,copy,json,os,re,shlex,subprocess
from pathlib import Path
from shader_storage import collect,compiled_assets,patch_vulkan,record,write_storage,validate_storage
from build_model_io import validate_overrides
ROOT=Path(__file__).resolve().parents[1]
def arguments(command):
    return [x[1:-1]if x.startswith('"')and x.endswith('"')else x for x in shlex.split(command,posix=False)]
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','cache','model-io-manifest','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
    base=a.cache/'build/llama-ps5';base_receipt=base/'receipt.private.json';parent=validate_overrides(a.model_io_manifest,base_receipt)
    engine=json.loads(base_receipt.read_text());archive=[x for x in engine['artifacts']if Path(x['path']).name=='libggml-vulkan.a']
    if len(archive)!=1 or record(archive[0]['path'])!=archive[0]:raise ValueError('The immutable original Vulkan engine archive is required')
    try:
        generated,sources,header,recipes=collect(base);assets,members,tables=compiled_assets(archive[0]['path'],generated,header['path'])
    except BaseException as error:
        (out/'manifest.private.json').write_text(json.dumps(dict(schema='ps5-qwen-shader-storage-v1',state='failed',
            phase='original_shader_source_and_archive_admission',error_type=type(error).__name__,
            error=str(error),console_requests=0,GPU_calls=0,model_bytes_read=0),indent=2)+'\n')
        raise
    data=write_storage(assets,out,tables);data.update(schema='ps5-qwen-shader-storage-v1',state='running',
        parent_model_io=record(a.model_io_manifest),original_engine=record(base_receipt),original_shader_archive=archive[0],
        original_shader_members=members,steps=[],console_requests=0,GPU_calls=0,model_bytes_read=0,
        all_compiled_shader_bytes_preserved=True)
    compiler=a.workspace/'toolchain/llvm-mingw-20261006-ucrt-x86_64/bin/clang++.exe'
    host=a.workspace/'toolchain/msys-clang64/clang64/bin';env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''))
    def run(label,cmd):
        x=subprocess.run(list(map(str,cmd)),capture_output=True,cwd=ROOT,env=env,timeout=300)
        (out/(label+'.private.log')).write_bytes(x.stdout+x.stderr);data['steps'].append(dict(name=label,returncode=x.returncode))
        if x.returncode:raise RuntimeError(x.stderr.decode('utf-8','replace')[-4000:])
        print(label+' passed',flush=True)
    try:
        model_io=copy.deepcopy(parent);source=out/'source'
        for name,row in model_io['sources'].items():
            original=a.model_io_manifest.parent/'source'/name
            if record(original)['sha256']!=row['patched_sha256']:raise ValueError('Original model-I/O source changed')
            target=source/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(original.read_bytes())
        key='ggml/src/ggml-vulkan/ggml-vulkan.cpp';target=source/key
        target.write_text(patch_vulkan(target.read_text()),encoding='utf-8',newline='\n')
        row=[x for x in model_io['objects']if x['source']==key][0];cmd=arguments(row['command'])
        if Path(cmd[0]).resolve()!=compiler.resolve()or '--target=x86_64-sie-ps5'not in cmd:raise ValueError('The qualified original PS5 compile recipe is required')
        cmd[cmd.index('-c')+1]=str(target);obj=out/'ggml-vulkan.cpp.o';cmd[cmd.index('-o')+1]=str(obj)
        run('native_Vulkan_input_extension',cmd);row.update(object=record(obj),command=subprocess.list2cmdline(cmd))
        model_io['sources'][key]['patched_sha256']=record(target)['sha256']
        model_io['shader_storage_extension']=dict(parent=record(a.model_io_manifest),bridge=record(ROOT/'native/app/shader_assets_bridge.h'),
            original_shader_bytes_preserved=True,driver_unchanged=True)
        extended=out/'model-io.private.json';extended.write_text(json.dumps(model_io,indent=2)+'\n')
        validate_overrides(extended,base_receipt)
        sdk=a.workspace/'toolchain/ps5-sdk-radv/ps5-payload-sdk'
        shared=[compiler,'--no-default-config','--target=x86_64-sie-ps5','-fno-stack-protector','-fno-plt','-fPIC']
        assembly=out/'shader-storage.o';registry=out/'shader-registry.o'
        run('native_shader_storage_assembly',[*shared,'-c',data['assembly']['path'],'-o',assembly])
        run('native_shader_registry',[*shared,'-std=c++17','-O1','-nostdinc++','-isystem',sdk/'target/include/c++/v1',
            '-isystem',sdk/'target/include','-I',ROOT/'native/app','-I',Path(header['path']).parent,'-c',data['registry']['path'],'-o',registry])
        data.update(extended_model_io=record(extended),vulkan_object=record(obj),asset_objects=[record(assembly),record(registry)],
            inputs=[record(Path(__file__)),record(ROOT/'tools/shader_storage.py'),record(ROOT/'native/app/shader_assets_bridge.h'),
                record(a.model_io_manifest),record(base_receipt),archive[0],header,recipes,*sources],
            state='compiled_not_console_admitted')
    except BaseException:data['state']='failed';raise
    finally:(out/'manifest.private.json').write_text(json.dumps(data,indent=2)+'\n')
    validate_storage(out/'manifest.private.json',extended,base_receipt)
    print(json.dumps({k:data[k]for k in ('shader_count','original_bytes','stored_bytes','maximum_shader_bytes','registry_sha256','state')}))
if __name__=='__main__':main()
