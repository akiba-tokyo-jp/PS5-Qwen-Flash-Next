#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Link a model-free native paired Down client against the exact selected driver."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

from audit_native_imports import audit
from native_dispatch import ELF
from build_performance_quantizer import record
from start_success_route import load, need, save

ROOT = Path(__file__).resolve().parents[1]


def once(text, before, after):
    need(text.count(before) == 1, 'One exact original component adapter location required')
    return text.replace(before, after)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('workspace', 'current', 'component', 'software-proof', 'out'):
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--reuse-retirement-controls',type=Path)
    a = p.parse_args()
    component, proof = load(a.component), load(a.software_proof)
    need(component['completed'] and component['buffer_tables'] and component['all14745600_decoded_F32_values_byte_exact'] and
         proof['completed'] and proof['all_outputs_passed'] and proof['software_SPIRV_reference'] and
         proof['Vulkan_dispatches'] == 960 and proof['all_GPU_resources_positively_retired'] and
         proof['build'] == record(a.component), 'Reuse the exact completed buffer-codebook software component')
    cases = load(component['GPU_cases']['path'])
    need(record(component['GPU_cases']['path']) == component['GPU_cases'] and len(cases['cases']) == 12 and
         len(cases['shader']) == 2 and cases['buffer_tables'], 'Exact original twelve cases and two shaders required')
    desktop = ROOT / 'tools/check_iq2_paired_down_gpu.cpp'
    need(record(desktop)['sha256'] == proof['source']['sha256'], 'The completed desktop component source changed')
    a.out.mkdir(parents=True, exist_ok=False)
    support=a.out/'paired_down_native_support.h'
    shutil.copyfile(ROOT/'native/app/paired_down_native_support.h',support)
    builder_snapshot=a.out/'builder.private.py';shutil.copyfile(Path(__file__),builder_snapshot)
    source_inputs = [record(a.component), record(a.software_proof), component['GPU_cases'], record(desktop),
                     record(support),
                     record(ROOT / 'native/qwen_flash_next/app_named_stat.h'),
                     record(ROOT / 'native/qwen_flash_next/launch_integrity.h'),
                     record(ROOT / 'native/qwen_flash_next/launch_integrity_native.h'), record(builder_snapshot)]
    canonical=a.current/'provenance/R1-source-513952a2b79853db'
    for name in ('resident_direct_tables.h','resident_incremental_tables.h','resident_phase_vm.h',
                 'resident_CPU_metadata_scope.h','system_memory.h'):
        path=canonical/name;source_inputs.append(record(path));shutil.copyfile(path,a.out/name)
        need(record(a.out/name)['sha256']==source_inputs[-1]['sha256'],'An exact selected Direct table header changed')
    # Repack already checked blobs without re-encoding any weight or reference.
    original = copy.deepcopy(cases)
    blobs = {}
    for row in cases['cases']:
        for key in ('weights', 'inputs', 'ids', 'expected'):
            blobs[row[key]['sha256']] = row[key]
    for row in cases['shader']:
        blobs[row['artifact']['sha256']] = row['artifact']
    blobs[cases['tables']['sha256']] = cases['tables']
    parts = []
    pack = a.out / 'paired-Down.pack'
    with pack.open('xb') as out:
        for ordinal, row in enumerate(blobs.values()):
            need(record(row['path']) == row, 'A checked original component blob changed')
            source_inputs.append(copy.deepcopy(row))
            raw = Path(row['path']).read_bytes()
            out.write(bytes((-out.tell()) % 16384))
            parts.append(dict(key='BLOB_' + str(ordinal), offset=out.tell(), bytes=len(raw), sha256=row['sha256']))
            out.write(raw)
        out.write(bytes((-out.tell()) % 16384))
    pack_record = record(pack)
    need(pack_record['bytes'] <= 128 << 20, 'Bounded model-free component pack required')
    with pack.open('rb') as check:
        for row in parts:
            check.seek(row['offset'])
            need(hashlib.sha256(check.read(row['bytes'])).hexdigest()==row['sha256'],
                 'Independent packed-extent readback differs from the original checked blob')
    keys = {row['sha256']: row['key'] for row in parts}
    for row in cases['cases']:
        for key in ('weights', 'inputs', 'ids', 'expected'):
            row[key]['path'] = keys[row[key]['sha256']]
    for row in cases['shader']:
        row['artifact']['path'] = keys[row['artifact']['sha256']]
    cases['tables']['path'] = keys[cases['tables']['sha256']]
    remote = '/app0/qwen-runtime/paired-Down-' + pack_record['sha256'][:24] + '.bin'
    header = '#pragma once\n#include <cstdint>\n'
    header += 'struct NativePart{const char*key;std::uint64_t offset,bytes;const char*sha256;};\n'
    header += 'inline constexpr NativePart paired_parts[]={\n'
    for row in parts:
        header += '{' + json.dumps(row['key']) + ',' + str(row['offset']) + 'ULL,' + str(row['bytes']) + 'ULL,' + json.dumps(row['sha256']) + '},\n'
    header += '};\ninline constexpr const char*paired_pack_path=' + json.dumps(remote) + ';\n'
    header += 'inline constexpr std::uint64_t paired_pack_bytes=' + str(pack_record['bytes']) + 'ULL;\n'
    header += 'inline constexpr const char*paired_pack_sha256=' + json.dumps(pack_record['sha256']) + ';\n'
    header += 'inline constexpr char paired_cases_json[]=' + json.dumps(json.dumps(cases, separators=(',', ':'))) + ';\n'
    assets = a.out / 'paired_down_assets.h'
    assets.write_text(header, encoding='utf-8', newline='\n')
    text = desktop.read_text(encoding='utf-8')
    text = once(text, '// A finite desktop Vulkan component check. It never communicates with a PS5.',
                '// Native adapter of the completed numerical component; no model or display.')
    text = once(text, '#include <windows.h>', '#include "paired_down_native_support.h"')
    text = once(text, '#include <iostream>\n', '')
    text = once(text, 'std::cout<<row.dump()<<\'\\n\'<<std::flush;', '')
    text = once(text, '        std::cerr<<"Desktop GPU completion unknown; resources retained, no resubmission\\n"<<std::flush;', '')
    start, end = text.index('std::vector<unsigned char>read('), text.index('#define DEVICE_API')
    text = text[:start] + 'std::vector<unsigned char>read(const std::string&path){return native_read(path);}\nvoid save(const std::string&path,const Json&value){native_save(path,value);}\n' + text[end:]
    start = text.index('        auto library=LoadLibraryA(')
    end = text.index('        const auto create=', start)
    text = text[:start] + '        const auto get=vkGetInstanceProcAddr;\n' + text[end:]
    text = once(text, 'void close(){vkDestroyDevice(device,nullptr);device=VK_NULL_HANDLE;destroy_instance(instance,nullptr);instance=VK_NULL_HANDLE;}',
                'void close(){qwen_native_driver_complete();const auto epoch=native_completed_epoch();vkDestroyDevice(device,nullptr);device=VK_NULL_HANDLE;destroy_instance(instance,nullptr);instance=VK_NULL_HANDLE;native_component_finish(epoch);}')
    text = once(text, '    Buffer b;b.bytes=bytes;', '    native_guard();Buffer b;b.bytes=bytes;')
    text = once(text, '        const auto started=std::chrono::steady_clock::now();',
                '        native_guard(31);const auto started=std::chrono::steady_clock::now();') if text.count('        const auto started=std::chrono::steady_clock::now();') else once(text,
                '    const auto started=std::chrono::steady_clock::now();', '    native_guard(31);const auto started=std::chrono::steady_clock::now();')
    text = once(text, 'int main(int argc,char**argv){try{', 'int qwen_paired_down_component(int argc,char**argv){try{')
    text = once(text, '    API a(software);Json result=', '    need(!software&&!first_only,"The complete native component is required");native_component_prepare();API a(false);Json result=')
    text = once(text, 'unsigned count=0;ok(enumerate(instance,&count,nullptr)',
                'qwen_native_stage("paired_Down_before_physical_enumeration_count");unsigned count=0;ok(enumerate(instance,&count,nullptr)')
    text = once(text, 'std::vector<VkPhysicalDevice>devices(count);',
                'qwen_native_stage("paired_Down_physical_enumeration_count_returned");std::vector<VkPhysicalDevice>devices(count);')
    text = once(text, '        for(auto candidate:devices){',
                '        qwen_native_stage("paired_Down_physical_device_list_returned");for(auto candidate:devices){')
    text = once(text, 'VkPhysicalDeviceProperties p{};properties_of(candidate,&p);',
                'VkPhysicalDeviceProperties p{};qwen_native_stage("paired_Down_before_physical_properties");properties_of(candidate,&p);qwen_native_stage("paired_Down_physical_properties_returned");')
    text = once(text, 'shader.at("workgroup"),result);valid=valid',
                'shader.at("workgroup"),result);qwen_native_driver_checkpoint();valid=valid')
    text = text.replace('for(;;)Sleep(1000);', 'qwen_native_driver_retain();qwen_native_halt("paired_Down_native_fence_unknown_resources_retained");')
    text = text.replace('{"PS5_operations",0}', '{"PS5_GPU_execution",true}')
    text = text.replace('"desktop_dispatch_and_fence_wall_us"', '"native_dispatch_and_fence_wall_us"')
    text = once(text, 'result["unknown_completion"]=false;save(argv[2],result);',
                'result["unknown_completion"]=false;result["native_PS5"]=true;result["model_loads"]=0;result["all_model_source_device_owners_positively_retired"]=true;result["device_ledger_live_bytes"]=0;save(argv[2],result);')
    text = once(text, '}catch(const std::exception&e){std::cerr<<e.what()<<\'\\n\';return 1;}}',
                '}catch(...){throw;}}')
    need(not any(token in text for token in ('LoadLibraryA(', 'GetProcAddress(', 'Sleep(')), 'Desktop OS calls must be absent')
    source = a.out / 'paired-down-native.private.cpp'
    source.write_text(text, encoding='utf-8', newline='\n')
    source_inputs += [record(source), record(assets), pack_record]
    retained = load(a.current / 'provenance/retained-relink-inputs.private.json')
    prior = load(a.current / 'provenance/native-link.receipt.private.json')
    mapping = {row['original_path']: row for row in retained}
    keep_tags = ('native_crt-', 'native_fault-', 'native-bootstrap-boot-qualified.o', 'native_gpu-',
                 'native_addr-', 'native_memory-', 'native_import_pool-', 'vulkan_bridge-', 'tables-e', 'registry-',
                 'lifecycle.o', 'sha256_backend-')
    selected = {name for name in mapping if name.endswith('.o') and any(tag in Path(name).name for tag in keep_tags)}
    # Select the exact current system-memory and table-restore providers by
    # their retained file identity, rather than ambiguous repeated budget names.
    for stem in ('cff3fd5b84c583f2-',):
        found = [name for name, row in mapping.items() if Path(row['path']).name.startswith(stem)]
        need(len(found) == 1, 'One exact selected native provider required')
        selected.add(found[0])
    recipe = prior.get('retained_link_command', prior['link_command'])
    archives = {Path(name).name for name in mapping if name.endswith('.a') and not Path(name).name.startswith(('libggml', 'libllama'))}
    sdk = a.workspace / 'toolchain/ps5-sdk-radv/ps5-payload-sdk/target/include'
    compiler = a.workspace / 'toolchain/llvm-mingw-20261006-ucrt-x86_64/bin'
    up = a.current.parent / 'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569'
    sha = a.workspace / 'native/model_hash/sha256.c'
    common = [str(compiler/'clang++.exe'), '--no-default-config', '--target=x86_64-sie-ps5', '-nostdinc++',
              '-isystem', str(sdk/'c++/v1'), '-isystem', str(sdk), '-std=c++17', '-fPIC', '-fno-stack-protector',
              '-fno-plt', '-femulated-tls', '-fexceptions', '-fcxx-exceptions', '-frtti', '-O2', '-ffunction-sections', '-fdata-sections', '-Wall', '-Wextra',
              '-Werror', '-Wno-unused-function', '-I', str(a.out), '-I', str(ROOT/'native/app'),
              '-I', str(ROOT/'native/qwen_flash_next'), '-I', str(sha.parent),
              '-I', str(a.workspace/'toolchain/Vulkan-Headers/include'), '-I', str(up/'vendor')]
    obj, sha_obj, integrity_obj = a.out/'component.o', a.out/'sha256.o', a.out/'integrity.o'
    commands = [common+['-c', str(source), '-o', str(obj)],
                [str(compiler/'clang.exe'), '--no-default-config', '--target=x86_64-sie-ps5', '-isystem', str(sdk),
                 '-O2', '-fPIC', '-fno-stack-protector', '-c', str(sha), '-o', str(sha_obj)]]
    integrity=a.out/'paired_down_integrity.private.c';shutil.copyfile(ROOT/'native/app/paired_down_integrity.c',integrity)
    commands.append([str(compiler/'clang.exe'),'--no-default-config','--target=x86_64-sie-ps5','-isystem',str(sdk),
        '-std=gnu11','-O2','-fPIC','-fno-stack-protector','-Wall','-Wextra','-Werror','-Wno-unused-function',
        '-I',str(ROOT/'native/qwen_flash_next'),'-I',str(sha.parent),'-c',str(integrity),'-o',str(integrity_obj)])
    link = []
    inputs = list(source_inputs) + [record(sha),record(integrity)]
    for argument in recipe:
        if argument.endswith('_stub_weak.so'):
            continue
        if argument.endswith('.o') and argument not in selected:
            continue
        if argument.endswith('.a') and Path(argument).name not in archives:
            continue
        if argument in ('--whole-archive', '--no-whole-archive') or argument.startswith('--wrap=gg'):
            continue
        if argument.startswith('-Map='):
            argument = '-Map=' + str(a.out/'native-link.private.map')
        if argument in mapping:
            row = mapping[argument]
            need(record(row['path']) == {k:row[k] for k in ('path','bytes','sha256')}, 'A retained relink input changed')
            argument = row['path']
            if record(argument) not in inputs: inputs.append(record(argument))
        elif argument.endswith('.so'):
            expected = [row for row in prior['formatter_stubs'] if Path(row['path']).name == Path(argument).name]
            actual=record(argument)
            need(len(expected)==1 and all(actual[k]==expected[0][k] for k in ('bytes','sha256')),
                 'An actual runtime provider changed')
            inputs.append(actual)
        if argument.endswith('.a') and Path(argument).name.endswith('libvulkan-cold-tables.a'):
            link += ['--whole-archive',argument,'--no-whole-archive']
        else:link.append(argument)
    image = a.out/'paired-down.pie.elf'
    link[link.index('-o')+1] = str(image)
    link[1:1] = [str(obj),str(sha_obj),str(integrity_obj)]
    commands.append(link)
    source_inputs += [record(ROOT/'native/app/post_device_retirement.h'),record(ROOT/'tests/post_device_retirement_test.cpp')]
    inputs += source_inputs[-2:]
    host=a.workspace/'toolchain/msys-clang64/clang64/bin'
    test=a.out/'post-device-retirement.exe'
    controls=[[str(host/'clang++.exe'),'-std=c++17','-O2','-Wall','-Wextra','-Werror',
               '-I',str(ROOT/'native/app'),str(ROOT/'tests/post_device_retirement_test.cpp'),'-o',str(test)],[str(test)]]
    reused_controls=None
    if a.reuse_retirement_controls:
        previous=load(a.reuse_retirement_controls)
        need(previous['completed'] and previous['new_post_device_controls']==15,'Exact completed retirement controls required')
        known={Path(row['path']).name:row for row in previous['inputs_before']}
        for name in ('post_device_retirement.h','post_device_retirement_test.cpp'):
            need(name in known and record(known[name]['path'])==known[name],'A passed retirement control source changed')
        reused_controls=record(a.reuse_retirement_controls);controls=[]
    host_env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''),TMP=str(a.out),TEMP=str(a.out))
    for i,job in enumerate(controls):
        result=subprocess.run(job,capture_output=True,timeout=30,env=host_env)
        (a.out/('new-control-'+str(i)+'.private.log')).write_bytes(result.stdout+result.stderr)
        need(result.returncode==0,result.stderr.decode(errors='replace')[-3500:])
    save(a.out/'host-build-plan.private.json',dict(commands=commands,inputs=inputs,PS5_operations=0))
    for i, job in enumerate(commands):
        result = subprocess.run(job,capture_output=True,timeout=120,env=dict(os.environ,TMP=str(a.out),TEMP=str(a.out)))
        (a.out/(str(i)+'.private.log')).write_bytes(result.stdout+result.stderr)
        need(result.returncode==0,result.stderr.decode(errors='replace')[-6000:])
    receipt = dict(artifact=record(image),inputs_before=inputs,runtime_providers=prior['runtime_providers'])
    save(a.out/'receipt.private.json',receipt)
    imported = audit(a.workspace,a.current.parent,a.out)
    need(not imported['missing'],'Every actual native import must resolve')
    # Preserve the successful client's full static-driver inclusion: generated
    # Vulkan tables contain weak references, which archive extraction alone
    # does not pull. Reuse its measured layout and check the actual new pointers.
    native=ELF(image);table=native.symbols['vk_common_physical_device_entrypoints'];callbacks=[]
    for row in prior['native_dispatch_audit']['required_physical_callbacks']:
        implementation=native.symbols.get('vk_common_'+row['callback'])
        pointer=native.pointer(table['value']+row['offset'])
        valid=implementation is not None and pointer!=0 and pointer==implementation['value']
        callbacks.append(dict(callback=row['callback'],offset=row['offset'],implementation_present=implementation is not None,
                              pointer_matches=valid))
    need(all(row['pointer_matches'] for row in callbacks),'Required actual Vulkan callback is missing; refuse packaging')
    names = subprocess.check_output([str(compiler/'llvm-nm.exe'),'--defined-only','--format=posix',str(image)],text=True)
    need(not any(re.match(r'^(llama_|ggml_)',line) for line in names.splitlines()),'No model engine may enter this native client')
    need(all(record(row['path'])==row for row in inputs),'A selected source/input changed during relink')
    receipt.update(completed=True,baseline_relink=False,CPU_only=False,driver_code_linked=True,model_engine_linked=False,model_loads=0,
        driver_revision='872cc1264ad8ba5d6b888b092968fa5858a38c58',driver_profile='cumulative-idle',persistent_caches=False,
        linked_driver=[r for r in inputs if r['sha256']=='a325dcd4584b1f1fccc6b46e90faa081ca86d18544aca610efea9e3ca3774f32'],
        lossless_driver_tables=prior['lossless_driver_tables'],real_module_import_audit=imported,
        component=record(a.component),software_proof=record(a.software_proof),source=record(source),commands=commands,
        link_command=link,component_pack=dict(local=pack_record,application_path=remote),parts=parts,
        original_case_geometry=original,maximum_GPU_dispatches=24,CPU_heap_cap=64<<20,device_owner_cap=128<<20,
        native_GPU_qualified=False,new_post_device_controls=15,unchanged_retirement_controls_reused=reused_controls,
        same_selected_Direct_table_mapping_and_incremental_restoration=True,
        CPU_startup_only_mode=True,successful_driver_whole_archive_preserved=True,
        actual_physical_dispatch_audit=callbacks,CPU_Direct_capacity_readmission=True,PS5_operations=0,production_adopted=False)
    (a.out/'receipt.private.json').write_text(json.dumps(receipt,indent=2)+'\n')
    save(a.out/'result.private.json',receipt)
    print(json.dumps(dict(completed=True,model_engine_linked=False,pack_bytes=pack_record['bytes'],maximum_GPU_dispatches=24,PS5_operations=0)))


if __name__=='__main__':main()
