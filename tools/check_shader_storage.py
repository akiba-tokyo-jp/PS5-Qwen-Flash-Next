#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Run the actual shader codec/lookup fixtures and compile its PS5 provider."""
import argparse,hashlib,json,os,struct,subprocess
from pathlib import Path
from shader_storage import record,validate_storage,unpack
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','cache','shader-storage-manifest','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    data=json.loads(a.shader_storage_manifest.read_text());validate_storage(a.shader_storage_manifest,data['extended_model_io']['path'],a.cache/'build/llama-ps5/receipt.private.json')
    host=a.workspace/'toolchain/msys-clang64/clang64/bin';target=a.workspace/'toolchain/llvm-mingw-20261006-ucrt-x86_64/bin'
    sdk=a.workspace/'toolchain/ps5-sdk-radv/ps5-payload-sdk';engine=a.cache/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569'
    root=a.shader_storage_manifest.parent;pool=Path(data['pool']['path']).read_bytes()
    sample=next(r for r in data['shaders']if r['storage_bytes']<r['original_bytes'])
    for row in data['shaders']:
        blob=pool[row['offset']:row['offset']+row['storage_bytes']];raw=unpack(blob)
        if hashlib.sha256(raw).hexdigest()!=row['original_sha256']:raise ValueError('Original compiled shader hash changed')
    (a.out/'shader_codec_sample.h').write_text(f'#define QWEN_EXPECTED_SHADER_COUNT {data["shader_count"]}\n#define QWEN_EXPECTED_LOOKUP_COUNT {data["lookup_entries"]}\n'+
        f'#define QWEN_EXPECTED_STORED_BYTES {data["stored_bytes"]}\n#define QWEN_EXPECTED_OUTPUT_BYTES {data["maximum_shader_bytes"]}\n'+
        '#define QWEN_EXPECTED_SHADER_REGISTRY '+json.dumps(data['registry_sha256'])+'\n'+
        '#define QWEN_CODEC_SAMPLE_DATA '+sample['name']+'_data\n#define QWEN_CODEC_SAMPLE_SIZE '+str(sample['storage_bytes'])+'\n')
    paths=[ROOT/n for n in ('native/app/shader_assets.cpp','native/app/shader_assets.h','native/app/shader_assets_bridge.h',
        'native/thirdparty/zlib/zlib.h','native/thirdparty/zlib/zconf.h','tests/shader_assets.cpp','tests/shader_codec_stubs/ps5platform/heap.h',
        'native/app/sha256_backend.cpp','native/app/model_cpu_budget.h','native/app/system_memory.h','native/app/profile_clock.h',
        'tools/check_shader_storage.py','tools/shader_storage.py')]
    r=dict(state='running',inputs={str(f.relative_to(ROOT)):record(f)['sha256']for f in paths},steps=[],console_requests=0,GPU_calls=0,
        storage_manifest=record(a.shader_storage_manifest),all_original_compiled_SPIRV_bytes_preserved=True)
    env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''))
    def run(label,cmd):
        x=subprocess.run(list(map(str,cmd)),capture_output=True,cwd=ROOT,env=env,timeout=180)
        (a.out/(label+'.private.log')).write_bytes(x.stdout+x.stderr);r['steps'].append(dict(name=label,returncode=x.returncode))
        if x.returncode:raise RuntimeError(x.stderr.decode('utf-8','replace')[-4000:])
        print(label+' passed',flush=True)
    try:
        host_asm=a.out/'shader-storage-host.o';host_registry=a.out/'shader-registry-host.o'
        run('host_storage_assembly',[host/'clang++.exe','-c',data['assembly']['path'],'-o',host_asm])
        run('host_registry_compile',[host/'clang++.exe','-std=c++17','-O2','-I',ROOT/'native/app','-I',a.cache/'build/llama-ps5/ggml/src/ggml-vulkan',
            '-c',data['registry']['path'],'-o',host_registry])
        exe=a.out/'actual-shader-storage.exe'
        run('actual_codec_compile',[host/'clang++.exe','-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',ROOT/'tests/shader_codec_stubs',
            '-I',ROOT/'native/app','-I',a.out,'-I',a.cache/'build/llama-ps5/ggml/src/ggml-vulkan','-I',engine/'vendor','-I',engine/'vendor/hash',
            ROOT/'tests/shader_assets.cpp',ROOT/'native/app/shader_assets.cpp',ROOT/'native/app/sha256_backend.cpp',host_asm,host_registry,
            '-L',host.parent/'lib','-lz','-o',exe])
        for mode in ('normal','concurrent','checksum','length','format','wrong_owner','heap_refusal','unknown_owner'):run(mode,[exe,mode])
        run('actual_PS5_codec_compile',[target/'clang++.exe','--no-default-config','--target=x86_64-sie-ps5','-DQWEN_NATIVE_PLATFORM=1',
            '-fno-stack-protector','-fno-plt','-femulated-tls','-fPIC','-std=c++17','-O1','-fexceptions','-fcxx-exceptions','-frtti','-nostdinc++',
            '-isystem',sdk/'target/include/c++/v1','-isystem',sdk/'target/include','-I',ROOT/'native/app','-I',engine/'vendor','-I',engine/'vendor/hash',
            '-Wall','-Wextra','-Werror','-c',ROOT/'native/app/shader_assets.cpp','-o',a.out/'shader-assets-PS5.o'])
        assert r['inputs']=={str(f.relative_to(ROOT)):record(f)['sha256']for f in paths}
        r.update(state='focused_shader_storage_host_passed_not_console_admitted',shader_count=data['shader_count'],lookup_entries=data['lookup_entries'],
            original_bytes=data['original_bytes'],stored_bytes=data['stored_bytes'],registry_sha256=data['registry_sha256'])
    except BaseException:r['state']='failed';raise
    finally:(a.out/'receipt.private.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
