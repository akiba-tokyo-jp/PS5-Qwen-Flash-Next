#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build separate full-model Q4 admission/cache code with qualified Vulkan objects."""
import argparse,copy,json,os,subprocess
from pathlib import Path
from expert_q4 import record,require,write_json
from expert_q4_model_source import entry_source,cache_source,SCOPE
from active_native_inputs import active_link_inputs
from build_model_io import validate_overrides
from external_shader_storage import validate_shader_resources
from driver_table_storage import audit_linked_storage
from native_dispatch import audit as dispatch
from audit_native_imports import audit
from build_expert_q4_model_providers import build as build_model_providers
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('parent','providers','workspace','cache','out'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--reuse-model-providers',type=Path)
    a=p.parse_args();prior=json.loads(a.parent.read_text());provider=json.loads(a.providers.read_text())
    require(provider['expert_q4_fixture']['preserve_F32_activation_input'] and provider['expert_q4_fixture']['actual_parent_and_extended_providers_compiled'],
        'The explicitly compiled and native-qualified F32-input Q4 provider is required')
    # The complete source ancestry was already qualified by the parent builds.
    # Recheck every current explicit link input and new source, excluding old
    # executables that cannot affect this link's bits.
    frozen=list({r['path']:r for r in active_link_inputs(prior)+active_link_inputs(provider)+
        [r for r in prior['inputs_before'] if Path(r['path']).suffix=='.so']}.values())
    for r in frozen:require(record(r['path'])==r,'Current qualified link input changed')
    a.out.mkdir(parents=True,exist_ok=False);(a.out/'tmp').mkdir()
    provider_receipt=a.reuse_model_providers or a.out/'model-providers/receipt.private.json'
    if a.reuse_model_providers:
        model_providers=json.loads(provider_receipt.read_text())
        require(model_providers['schema']=='ps5-qwen-expert-q4-model-providers-v1'and model_providers['completed']and
            model_providers['original_BF16_dispatch_byte_exact']and model_providers['Q4_F32_input_predicate_preserved']and
            model_providers['source_parent']==record(a.providers)and model_providers['BF16_control']==record(a.parent),
            'Only exact completed model-specific providers may be reused')
        for row in model_providers['inputs']:require(record(row['path'])==row,'Completed model provider changed')
        print(json.dumps(dict(qualified_model_providers_reused=True,recompiled=False)),flush=True)
    else:model_providers=build_model_providers(a.providers,a.parent,a.out/'model-providers')
    frozen +=model_providers['inputs']+[record(provider_receipt)]
    external=json.loads(Path(model_providers['shader_resource_manifest']['path']).read_text());embedded=json.loads(Path(external['embedded_control']['path']).read_text())
    ios=[json.loads(Path(embedded[k]['path']).read_text())for k in('parent_model_io','extended_model_io')]
    cache_key='src/llama-moe-cache.cpp';old_row=next(r for r in ios[1]['objects']if r['source']==cache_key)
    old_cache=Path(old_row['actual_source']['path']);old_entry=Path(prior['additional_cache_layout']['actual_entry']['path'])
    cache=a.out/'Expert-Q4-cache.private.cpp';entry=a.out/'Expert-Q4-model.private.cpp'
    cache.write_text(cache_source(old_cache.read_text()),newline='\n');entry.write_text(entry_source(old_entry.read_text()),newline='\n')
    require('isolated_large_cache_layout(startup,policy,native_resources_started)'not in entry.read_text()and
        'The isolated 134-slot fixture cannot enter model initialization'not in entry.read_text(),
        'The separate full-model entry must reach the complete metadata/memory/model path')
    commands=[];objects=[]
    for command,source,label in((prior['compile_commands'][0],entry,'entry'),(old_row['command'],cache,'cache')):
        require(isinstance(command,list),'Captured actual native compile command required')
        command=command.copy();obj=a.out/(label+'.o');command[command.index('-c')+1]=str(source);command[command.index('-o')+1]=str(obj)
        if '-MF'in command:command[command.index('-MF')+1]=str(a.out/(label+'.private.d'))
        command[1:1]=['-I',str(a.out)];command+=['-I',str(old_entry.parent),'-I',str(old_cache.parent)]
        commands.append(command);objects.append(obj)
    old_main=prior['compile_commands'][0][prior['compile_commands'][0].index('-o')+1]
    old_backend=prior['lossless_shader_storage']['vulkan_object']['path'];new_backend=model_providers['lossless_shader_storage']['vulkan_object']['path']
    old_cache_object=old_row['object']['path']
    replacements={old_main:str(objects[0]),old_backend:new_backend,old_cache_object:str(objects[1])}
    for key in replacements:require(prior['link_command'].count(key)==1,'One exact current application object must be replaced: '+key)
    link=[replacements.get(x,x)for x in prior['link_command']];image=a.out/'qwen-native.pie.elf';link[link.index('-o')+1]=str(image)
    link=[('-Map='+str(a.out/'native-link.private.map'))if x.startswith('-Map=')else x for x in link]
    source_inputs=[a.parent,a.providers,Path(__file__),ROOT/'tools/expert_q4_model_source.py',old_cache,old_entry,cache,entry,
        *[ROOT/'native/app'/n for n in('expert_q4_receipt.h','expert_q4_source_integrity.h','expert_q4_geometry.h','expert_q4_cache_reset.h','resident_cache_reset.h','model_receipt.h','split_model_integrity.h')]]
    frozen +=[record(x)for x in source_inputs]
    for i,command in enumerate(commands+[link]):
        result=subprocess.run(command,cwd=ROOT,capture_output=True,timeout=600,env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp')))
        (a.out/f'{i}.private.log').write_bytes(result.stdout+result.stderr);require(result.returncode==0,result.stderr.decode(errors='replace')[-6000:])
        print(json.dumps(dict(Expert_Q4_model_build_step=i+1,total=3)),flush=True)
    for row in frozen:require(record(row['path'])==row,'Frozen Q4 model input changed during the new native link')
    require(b'ps5-qwen-expert-q4-model-result-v1'in image.read_bytes(),
        'The actual native image must retain full-model generation and completion code')
    nm=Path(commands[0][0]).parent/'llvm-nm.exe'
    defined=subprocess.check_output([str(nm),'--defined-only','--format=posix',str(image)],text=True)
    require(any(line.split()[0]=='llama_model_load_from_splits'for line in defined.splitlines()if line.split()),
        'The actual full-model split loader must be defined in the final image')
    map_text=(a.out/'native-link.private.map').read_text().replace('\\','/').lower()
    require(str(objects[1]).replace('\\','/').lower()in map_text and 'libllama.a(llama-moe-cache.cpp.o)'not in map_text,
        'The Q4 cache override must win the actual final link')
    io_rows=[]
    for label,data,original_row in zip(('parent','extended'),ios,(embedded['parent_model_io'],embedded['extended_model_io'])):
        row=next(r for r in data['objects']if r['source']==cache_key)
        row.update(object=record(objects[1]),command=commands[1],actual_source=record(cache),logical_source_before_VFS=record(cache))
        data['sources'][cache_key]['patched_sha256']=record(cache)['sha256']
        # The shader validator also compares the original and restored source
        # text relative to each I/O manifest. Preserve both qualified views.
        directory=a.out/label;directory.mkdir();key='ggml/src/ggml-vulkan/ggml-vulkan.cpp'
        source=directory/'source'/key;source.parent.mkdir(parents=True)
        source.write_bytes((Path(original_row['path']).parent/'source'/key).read_bytes())
        path=directory/'model-io.private.json';write_json(path,data);validate_overrides(path,prior['engine_receipt']['path']);io_rows.append(record(path))
    replace={embedded['parent_model_io']['path']:io_rows[0],embedded['extended_model_io']['path']:io_rows[1]}
    def updated(rows):return[replace.get(r['path'],r)for r in rows]
    embedded.update(parent_model_io=io_rows[0],extended_model_io=io_rows[1],inputs=updated(embedded['inputs'])+[record(cache),record(objects[1])])
    embedded_path=a.out/'embedded-shader.private.json';write_json(embedded_path,embedded);replace[external['embedded_control']['path']]=record(embedded_path)
    external.update(parent_model_io=io_rows[0],extended_model_io=io_rows[1],embedded_control=record(embedded_path),inputs=updated(external['inputs'])+[record(cache),record(objects[1])])
    external_path=a.out/'external-shader.private.json';write_json(external_path,external)
    storage=validate_shader_resources(external_path,io_rows[1]['path'],prior['engine_receipt']['path'])
    receipt=copy.deepcopy(prior)
    receipt.update(artifact=record(image),compile_commands=[commands[0]],link_command=link,source_parent=record(a.parent),
        inputs_before=frozen+[record(x)for x in objects]+io_rows+[record(embedded_path),record(external_path)],
        bounded_model_source_manifest=io_rows[1],bounded_model_source_overrides=ios[1],shader_resource_manifest=record(external_path),lossless_shader_storage=storage,
        expert_q4_model=dict(scope=SCOPE,actual_entry=record(entry),actual_cache=record(cache),commands=commands,
            providers_reused_from=record(a.providers),model_providers=record(provider_receipt),
            original_BF16_dispatch_preserved=True,non_Expert_shaders_unchanged=True,full_model_native_validation_pending=True,production_adopted=False),
        lossless_driver_table_geometry=audit_linked_storage(image,prior['lossless_driver_tables']))
    target=a.out/'receipt.private.json';write_json(target,receipt)
    receipt['real_module_import_audit']=audit(a.workspace,a.cache,a.out)
    receipt['native_dispatch_audit']=dispatch(a.workspace,a.workspace/'driver-work/PS5-Vulkan-Inference-qwen-872cc126',image,a.out/'dispatch')
    require(not receipt['real_module_import_audit']['missing'] and receipt['native_dispatch_audit']['passed'],'Actual native import/dispatch audit failed')
    write_json(target,receipt);print(json.dumps(dict(Expert_Q4_full_model_candidate_built=True,PS5_operations=0,CI_runs=0)),flush=True)

if __name__=='__main__':main()
