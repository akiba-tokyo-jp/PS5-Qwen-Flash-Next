#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build external locations using the exact previously compiled Vulkan object."""
import argparse,copy,json,subprocess
from pathlib import Path
from shader_storage import record,validate_storage
from external_shader_storage import SCHEMA,external_sources,validate_external_storage
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','cache','embedded-manifest','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    control=json.loads(a.embedded_manifest.read_text());base=a.cache/'build/llama-ps5/receipt.private.json'
    control=validate_storage(a.embedded_manifest,control['extended_model_io']['path'],base)
    assembly,registry,window=external_sources(control)
    if window>(2<<20):raise ValueError('External resource window exceeds the native contract')
    source=a.out/'shader-locations.private.S';source.write_text(assembly,encoding='utf-8')
    cpp=a.out/'shader-registry.private.cpp';cpp.write_text(registry,encoding='utf-8')
    compiler=a.workspace/'toolchain/llvm-mingw-20261006-ucrt-x86_64/bin/clang++.exe'
    sdk=a.workspace/'toolchain/ps5-sdk-radv/ps5-payload-sdk'
    header,=[r for r in control['inputs']if Path(r['path']).name=='ggml-vulkan-shaders.hpp']
    common=[compiler,'--no-default-config','--target=x86_64-sie-ps5','-fno-stack-protector','-fno-plt','-fPIC']
    obj=a.out/'shader-locations.o';reg=a.out/'shader-registry.o';steps=[]
    commands=[('native_external_locations',[*common,'-c',source,'-o',obj]),
        ('native_external_registry',[*common,'-std=c++17','-O1','-nostdinc++','-isystem',sdk/'target/include/c++/v1',
        '-isystem',sdk/'target/include','-I',ROOT/'native/app','-I',Path(header['path']).parent,'-c',cpp,'-o',reg])]
    data=copy.deepcopy(control);data.update(schema=SCHEMA,state='running',embedded_control=record(a.embedded_manifest),
        storage_kind='external_file',external_token_bytes=24,external_file_input_window_bytes=window,
        Vulkan_object_recompiled=False,model_bytes_read=0,console_requests=0,GPU_calls=0,steps=steps)
    try:
        for label,command in commands:
            r=subprocess.run(list(map(str,command)),cwd=ROOT,capture_output=True,timeout=120)
            (a.out/(label+'.private.log')).write_bytes(r.stdout+r.stderr);steps.append(dict(name=label,returncode=r.returncode))
            if r.returncode:raise RuntimeError(r.stderr.decode('utf-8','replace')[-3000:])
            print(label+' passed',flush=True)
        data.update(assembly=record(source),registry=record(cpp),asset_objects=[record(obj),record(reg)],
            inputs=control['inputs']+[record(a.embedded_manifest),record(Path(__file__)),
                record(ROOT/'tools/external_shader_storage.py'),record(ROOT/'native/app/shader_file_bridge.h')],
            state='compiled_not_console_admitted')
    except BaseException:data['state']='failed';raise
    finally:(a.out/'manifest.private.json').write_text(json.dumps(data,indent=2)+'\n')
    validate_external_storage(a.out/'manifest.private.json',control['extended_model_io']['path'],base)
    print(json.dumps(dict(state=data['state'],external_file_bytes=data['stored_bytes'],input_window_bytes=window,
        original_shader_count=data['shader_count'],Vulkan_object_recompiled=False)))
if __name__=='__main__':main()
