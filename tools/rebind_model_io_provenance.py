#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Preserve immutable shader assets while recording the actual MoE overlay.

Create a new parent/extended manifest pair. Both select the same actual MoE
object; the existing shader validator still requires their only other object
difference to be its qualified Vulkan resource provider. No old file changes.
"""
import argparse,copy,json,shutil
from pathlib import Path
from shader_storage import record
from build_model_io import validate_overrides
from external_shader_storage import validate_shader_resources
ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser();p.add_argument('--linked',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();linked=json.loads(a.linked.read_text());a.out.mkdir(parents=True)
    for row in linked['inputs_before']+[linked['artifact']]:
        if record(row['path'])!=row:raise ValueError('Actual compiled overlay input changed: '+row['path'])
    resource=json.loads(Path(linked['shader_resource_manifest']['path']).read_text())
    embedded_path=Path(resource['embedded_control']['path']);embedded=json.loads(embedded_path.read_text())
    parent_path=Path(embedded['parent_model_io']['path']);extended_path=Path(embedded['extended_model_io']['path'])
    parent=json.loads(parent_path.read_text());extended=json.loads(extended_path.read_text())
    selected=next(x for x in linked['bounded_model_source_overrides']['objects']if x['source']=='src/llama-moe-cache.cpp')
    old=next(x for x in extended['objects']if x['source']==selected['source'])
    if record(selected['object']['path'])!=selected['object'] or selected['object']==old['object']:
        raise ValueError('A distinct actual compiled MoE overlay is required')
    recipe=selected['command'];actual=Path(recipe[recipe.index('-c')+1])
    if record(actual)!=selected['actual_source']:raise ValueError('Actual source does not match the compiled recipe')
    replacements={}
    def write(path,data):
        path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(data,indent=2)+'\n');return record(path)
    path_fields={'bridge':'mapped_source_bridge.h','logical_bridge':'logical_source_bridge.h','indexed_vector_policy':'indexed_vector.h',
        'mapped_copy_policy':'mapped_copy.h','padded_bank_bridge':'padded_bank_bridge.h','padded_cache_policy':'padded_cache_bridge.h',
        'padded_bank_layout':'padded_bank.h','padded_cache_geometry':'padded_cache_geometry.h'}
    new=[]
    for name,data,origin in [('parent',parent,parent_path),('extended',extended,extended_path)]:
        data=copy.deepcopy(data);row=next(x for x in data['objects']if x['source']==selected['source']);row.clear();row.update(selected)
        data['sources'][selected['source']]['patched_sha256']=record(actual)['sha256']
        for key,file in path_fields.items():data[key]=record(ROOT/'native/app'/file)
        data['predictive_cache_inputs']=[record(ROOT/'native/app'/file)for file in ('cross_layer_forecast.h','predictive_cache_bridge.h')]
        data['patches']=[record(file)for file in sorted((ROOT/'patches/native-model-io').glob('*.patch'))]
        data['actual_MoE_overlay']=dict(parent=record(origin),actual_source=record(actual),actual_object=selected['object'],
            compile_command=recipe,link_receipt=record(a.linked),immutable_original_sources_preserved=True)
        directory=a.out/name;source='ggml/src/ggml-vulkan/ggml-vulkan.cpp';target=directory/'source'/source
        target.parent.mkdir(parents=True);shutil.copyfile(origin.parent/'source'/source,target)
        path=directory/'model-io.private.json';row=write(path,data);validate_overrides(path,Path(linked['engine_receipt']['path']))
        replacements[str(origin)]=row;new.append(row)
    def replace_rows(rows):return [replacements.get(row['path'],row)for row in rows]
    embedded=copy.deepcopy(embedded);embedded.update(parent_model_io=new[0],extended_model_io=new[1],inputs=replace_rows(embedded['inputs']))
    embedded_row=write(a.out/'embedded-shader.private.json',embedded);replacements[str(embedded_path)]=embedded_row
    resource=copy.deepcopy(resource);resource.update(parent_model_io=new[0],extended_model_io=new[1],embedded_control=embedded_row,inputs=replace_rows(resource['inputs']))
    resource_row=write(a.out/'external-shader.private.json',resource)
    qualified=validate_shader_resources(resource_row['path'],new[1]['path'],linked['engine_receipt']['path'])
    result=copy.deepcopy(linked);result.update(bounded_model_source_manifest=new[1],bounded_model_source_overrides=json.loads(Path(new[1]['path']).read_text()),
        shader_resource_manifest=resource_row,lossless_shader_storage=qualified,
        immutable_model_IO_rebind=dict(parent_native=record(a.linked),original_parent_model_io=record(parent_path),
            original_extended_model_io=record(extended_path),original_shader_manifest=record(embedded_path),
            original_external_shader_manifest=record(Path(linked['shader_resource_manifest']['path'])),same_actual_native_image=True,
            existing_seven_object_and_shader_validation_retained=True))
    result['inputs_before'] += [record(Path(__file__)),record(a.linked),new[0],new[1],embedded_row,resource_row,record(actual)]
    write(a.out/'receipt.private.json',result)
    print(json.dumps(dict(actual_MoE_object_and_source_bound=True,original_shader_assets_unchanged=True,existing_validators_passed=True,PS5_operations=0)))
if __name__=='__main__':main()
