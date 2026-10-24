#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Describe external original shader frames without changing Vulkan or driver objects."""
import json,struct
from pathlib import Path
from shader_storage import record,validate_storage,elf_objects
TOKEN_MAGIC=b'QWSPVX01'
SCHEMA='ps5-qwen-external-shader-storage-v1'

def external_sources(control):
    pool=Path(control['pool']['path']);assembly=Path(control['assembly']['path']).read_text()
    for row in control['shaders']:
        name=row['name'];size=row['storage_bytes']
        if size<48 or size>=row['original_bytes']or row['offset']%4 or row['offset']+size>control['stored_bytes']:
            raise ValueError('Every external location must retain a complete individually hashed original frame')
        if not row['alias_of']:
            before=f'.incbin {json.dumps(pool.as_posix())},{row["offset"]},{size}'
            after='.ascii "QWSPVX01"\n.quad '+str(row['offset'])+'\n.long '+str(size)+'\n.long '+str(row['original_bytes'])
            if assembly.count(before)!=1:raise ValueError('The original unique shader storage directive changed')
            assembly=assembly.replace(before,after)
        before=f'.size {name}_data,{size}'
        if assembly.count(before)!=1:raise ValueError('The original shader symbol size changed')
        assembly=assembly.replace(before,f'.size {name}_data,24')
    if '.incbin'in assembly:raise ValueError('An external shader image still embeds resource payload')
    window=max(((r['offset']%16384+r['storage_bytes']+16383)//16384)*16384 for r in control['shaders'])
    registry=Path(control['registry']['path']).read_text();include='#include "shader_assets_bridge.h"'
    if registry.count(include)!=1:raise ValueError('The immutable resource registration include changed')
    registry=registry.replace(include,include+'\n#include "shader_file_bridge.h"')
    marker='__attribute__((constructor)) static void register_original_shader_storage() {'
    if registry.count(marker)!=1:raise ValueError('The original resource-only constructor changed')
    digest=','.join(str(v)for v in bytes.fromhex(control['pool']['sha256']))
    declaration='static const qwen_shader_file_plan external_file_plan={'+str(control['stored_bytes'])+','+str(window)+',{'+digest+'}};\n'
    registry=registry.replace(marker,declaration+marker+'\n    qwen_app_register_shader_file_plan(&external_file_plan);')
    return assembly,registry,window

def validate_external_storage(path,model_io_path,base_receipt):
    path=Path(path);data=json.loads(path.read_text())
    if data.get('schema')!=SCHEMA or data.get('state')!='compiled_not_console_admitted':
        raise ValueError('Complete external shader compilation and an explicit format are required')
    old=data['embedded_control'];old_path=Path(old['path'])
    if record(old_path)!=old:raise ValueError('The admitted embedded data control changed')
    control=json.loads(old_path.read_text())
    control=validate_storage(old_path,control['extended_model_io']['path'],base_receipt)
    for key in ('parent_model_io','extended_model_io','vulkan_object','original_engine','original_shader_archive',
                'original_shader_members','shader_count','original_bytes','stored_bytes','logical_stored_bytes',
                'unique_originals','maximum_shader_bytes','maximum_ordering_buffer_bytes','registry_sha256',
                'shaders','lookup_tables','lookup_entries','pool'):
        if data[key]!=control[key]:raise ValueError('External resources changed original bytes, lookups or engine provenance: '+key)
    if record(model_io_path)!=control['extended_model_io']:raise ValueError('External resources changed the actual Vulkan extension')
    assembly,registry,window=external_sources(control)
    if Path(data['assembly']['path']).read_text()!=assembly or Path(data['registry']['path']).read_text()!=registry:
        raise ValueError('External symbol generation changed more than exact locations and file registration')
    if data['external_token_bytes']!=24 or data['external_file_input_window_bytes']!=window or window>(2<<20):
        raise ValueError('External resource input exceeds its exact bounded window')
    for row in data['inputs']+[data['pool'],data['assembly'],data['registry'],*data['asset_objects'],data['vulkan_object']]:
        if record(row['path'])!=row:raise ValueError('An external shader input changed')
    symbols=elf_objects(Path(data['asset_objects'][0]['path']).read_bytes())
    for row in data['shaders']:
        token=struct.pack('<8sQII',TOKEN_MAGIC,row['offset'],row['storage_bytes'],row['original_bytes'])
        if symbols.get(row['name']+'_data')!=token or symbols.get(row['name']+'_len')!=struct.pack('<Q',row['storage_bytes']):
            raise ValueError('An actual external location, alias or original length differs')
    return data

def validate_shader_resources(path,model_io_path,base_receipt):
    schema=json.loads(Path(path).read_text()).get('schema')
    if schema==SCHEMA:return validate_external_storage(path,model_io_path,base_receipt)
    if schema=='ps5-qwen-shader-storage-v1':return validate_storage(path,model_io_path,base_receipt)
    raise ValueError('Unknown shader resource storage schema; no fallback is allowed')
