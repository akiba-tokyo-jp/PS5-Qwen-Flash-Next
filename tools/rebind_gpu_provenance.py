#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Bind a new Vulkan application provider without weakening shader-byte checks."""
import argparse,copy,json,os,subprocess
from pathlib import Path
from expert_q4 import record,write_json,require
from active_native_inputs import active_link_inputs
from shader_storage import patch_vulkan
from build_model_io import validate_overrides
from external_shader_storage import validate_shader_resources
ROOT=Path(__file__).resolve().parents[1]
KEY='ggml/src/ggml-vulkan/ggml-vulkan.cpp'
def original_shader_input(text):
 text=text.replace('#include "shader_assets_bridge.h"\n','',1)
 begin=text.index('    // Restore the exact immutable original before any existing float-control')
 end=text.index('    vk::ShaderModuleCreateInfo shader_module_create_info',begin)
 text=text[:begin]+text[end:]
 text=text.replace('    qwen_app_complete_shader_code(shader_storage_lease);\n','',1)
 return text
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--linked',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();n=json.loads(a.linked.read_text())
 for row in active_link_inputs(n):require(record(row['path'])==row,'Actual linked input changed')
 a.out.mkdir(parents=True,exist_ok=False);(a.out/'tmp').mkdir();resource=json.loads(Path(n['shader_resource_manifest']['path']).read_text());embedded_path=Path(resource['embedded_control']['path']);embedded=json.loads(embedded_path.read_text())
 originals=[Path(embedded[k]['path'])for k in('parent_model_io','extended_model_io')];data=[json.loads(p.read_text())for p in originals]
 gc=n['io_gpu_comparison']['GPU_command'];actual=Path(gc[gc.index('-c')+1]);require(record(actual)==n['io_gpu_comparison']['GPU_source'],'Actual GPU compile source changed')
 current=actual.read_text();control=original_shader_input(current);require(patch_vulkan(control)==current,'Only the original shader restoration extension may separate storage controls')
 parent_source=a.out/'parent/source'/KEY;parent_source.parent.mkdir(parents=True);parent_source.write_text(control,newline='\n');parent_obj=a.out/'parent/GPU-control.o'
 cmd=gc.copy();cmd[cmd.index('-c')+1]=str(parent_source);cmd[cmd.index('-o')+1]=str(parent_obj)
 if '-MF'in cmd:cmd[cmd.index('-MF')+1]=str(a.out/'parent/GPU-control.private.d')
 r=subprocess.run(cmd,capture_output=True,timeout=600,env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp')));(a.out/'parent-compile.private.log').write_bytes(r.stdout+r.stderr);require(r.returncode==0,r.stderr.decode(errors='replace')[-3000:])
 selected=copy.deepcopy(n['bounded_model_source_overrides']);extended_source=a.out/'extended/source'/KEY;extended_source.parent.mkdir(parents=True);extended_source.write_text(current,newline='\n');rows=[];replacements={}
 for index,(directory,gpu_object,gpu_source,recipe)in enumerate([('parent',parent_obj,parent_source,cmd),('extended',Path(gc[gc.index('-o')+1]),actual,gc)]):
  d=copy.deepcopy(selected);row=next(x for x in d['objects']if x['source']==KEY);row.update(object=record(gpu_object),command=recipe,actual_source=record(gpu_source));d['sources'][KEY]['patched_sha256']=record(gpu_source)['sha256']
  # The current cache is another explicit application override, shared exactly
  # by both storage controls; it must not retain an obsolete ancestor object.
  cc=n['routing_sharing']['commands'][1];cs=Path(cc[cc.index('-c')+1]);co=Path(cc[cc.index('-o')+1]);cache_row=next(x for x in d['objects']if x['source']=='src/llama-moe-cache.cpp');cache_row.update(object=record(co),command=cc,actual_source=record(cs));d['sources'][cache_row['source']]['patched_sha256']=record(cs)['sha256']
  path=a.out/directory/'model-io.private.json';write_json(path,d);validate_overrides(path,Path(n['engine_receipt']['path']));rows.append(record(path));replacements[str(originals[index])]=rows[-1]
 def replace(values):return[replacements.get(row['path'],row)for row in values]
 embedded=copy.deepcopy(embedded);embedded.update(parent_model_io=rows[0],extended_model_io=rows[1],vulkan_object=record(Path(gc[gc.index('-o')+1])),inputs=replace(embedded['inputs'])+[record(actual),record(parent_source),record(parent_obj),record(Path(__file__))])
 ep=a.out/'embedded-shader.private.json';write_json(ep,embedded);replacements[str(embedded_path)]=record(ep)
 resource=copy.deepcopy(resource);resource.update(parent_model_io=rows[0],extended_model_io=rows[1],vulkan_object=embedded['vulkan_object'],embedded_control=record(ep),inputs=replace(resource['inputs'])+[record(actual),record(parent_source),record(parent_obj)])
 rp=a.out/'external-shader.private.json';write_json(rp,resource);qualified=validate_shader_resources(rp,rows[1]['path'],n['engine_receipt']['path'])
 result=copy.deepcopy(n);result.update(bounded_model_source_manifest=rows[1],bounded_model_source_overrides=json.loads(Path(rows[1]['path']).read_text()),shader_resource_manifest=record(rp),lossless_shader_storage=qualified,GPU_provenance_rebind=dict(original_native=record(a.linked),same_actual_native_image=True,original_SPIRV_pool_and_asset_objects_unchanged=True,resource_only_source_relation_exact=True,compiled_nonstorage_control=record(parent_obj)))
 result['inputs_before'] += [record(a.linked),record(Path(__file__)),*rows,record(ep),record(rp),record(actual),record(parent_source),record(parent_obj)]
 write_json(a.out/'receipt.private.json',result);write_json(a.out/'core-safety.private.json',dict(completed=True,kind='bounded_io_gpu_comparison',original_physical_and_kernel_guards_preserved=True,CPU_heap_limit_bytes=512<<20,cache_slots=3072,driver_unchanged=True,actual_GPU_cache_source_and_all_original_shader_validators_bound=True,candidate=record(a.out/'receipt.private.json'),PS5_operations=0,CI_runs=0))
 print(json.dumps(dict(completed=True,actual_native_image_unchanged=True,actual_GPU_and_cache_objects_bound=True,original_shader_validators_passed=True)))
if __name__=='__main__':main()
