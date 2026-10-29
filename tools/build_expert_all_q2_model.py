#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build the isolated all-Expert Q2 entry, cache and F32-input providers."""
import argparse,copy,json,os,re,subprocess
from pathlib import Path
from expert_q4 import record,require,write_json
from expert_all_q2_model_source import entry_source,cache_source,provider_source,SCOPE,PACKED_SCOPE
from active_native_inputs import active_link_inputs
from build_model_io import validate_overrides
from external_shader_storage import validate_shader_resources
from shader_storage import patch_vulkan
from driver_table_storage import audit_linked_storage
from native_dispatch import audit as dispatch
from audit_native_imports import audit
ROOT=Path(__file__).resolve().parents[1]

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for key in ('parent','workspace','cache','out'):p.add_argument('--'+key,type=Path,required=True)
 p.add_argument('--reuse-compiled-providers',type=Path)
 p.add_argument('--finalize-existing',action='store_true')
 a=p.parse_args();prior=json.loads(a.parent.read_text());require(prior['expert_q2_model']['scope']['Expert_format']=='Gate_Up_Q2_K_Down_Q4_0','Exact closed mixed model parent required')
 frozen=active_link_inputs(prior)+[r for r in prior['inputs_before']if Path(r['path']).suffix=='.so']+[record(a.parent),record(__file__),record(ROOT/'tools/expert_all_q2_model_source.py')]
 for row in frozen:require(record(row['path'])==row,'Qualified mixed native input changed')
 completed=None
 if a.finalize_existing:
  completed=json.loads((a.out/'receipt.private.json').read_text());require(record(completed['artifact']['path'])==completed['artifact'],'Completed image changed before audit-only finalization')
  snapshot=ROOT/'.local/build_expert_all_q2_model_8630.snapshot.py'
  for row in completed['inputs_before']:
   if row['path']==str(Path(__file__)):require((record(snapshot)['bytes'],record(snapshot)['sha256'])==(row['bytes'],row['sha256']),'Exact compiled generator snapshot required')
   else:require(record(row['path'])==row,'A compiled native input changed before audit-only finalization')
 a.out.mkdir(parents=True,exist_ok=a.finalize_existing);(a.out/'tmp').mkdir(exist_ok=a.finalize_existing)
 external=json.loads(Path(prior['shader_resource_manifest']['path']).read_text());embedded=json.loads(Path(external['embedded_control']['path']).read_text())
 ios=[json.loads(Path(embedded[k]['path']).read_text())for k in ('parent_model_io','extended_model_io')]
 key='ggml/src/ggml-vulkan/ggml-vulkan.cpp';provider_objects=[];provider_commands=[];provider_sources=[]
 for label,role,data in zip(('parent','extended'),('parent_model_io','extended_model_io'),ios):
  before=Path(embedded[role]['path']).parent/'source'/key;target=a.out/label/'source'/key;target.parent.mkdir(parents=True,exist_ok=a.finalize_existing);target.write_text(provider_source(before.read_text()),newline='\n');frozen +=[record(before),record(target)]
  row=next(r for r in data['objects']if r['source']==key);cmd=row['command'];obj=a.out/label/'ggml-vulkan.cpp.o';require(isinstance(cmd,str),'Captured actual Vulkan compile command required')
  for flag,path in [('c',target),('o',obj)]:
   cmd,count=re.subn(r'(?<=\s)-'+flag+r'\s+(?:"[^"]+"|\S+)',lambda _: '-'+flag+' '+subprocess.list2cmdline([str(path)]),cmd);require(count==1,'One exact provider compile argument required')
  if a.reuse_compiled_providers:
   saved=a.reuse_compiled_providers/label/'source'/key;saved_obj=a.reuse_compiled_providers/label/'ggml-vulkan.cpp.o';saved_log=a.reuse_compiled_providers/(str(len(provider_objects))+'.private.log')
   require(saved.read_bytes()==target.read_bytes()and saved_obj.is_file()and saved_log.is_file(),'Reused provider must retain the exact already compiled source/object/log')
   cmd=cmd.replace(str(target),str(saved)).replace(str(obj),str(saved_obj));obj=saved_obj;frozen +=[record(saved),record(saved_obj),record(saved_log)]
  provider_objects.append(obj);provider_commands.append(cmd);provider_sources.append(target);row.update(command=cmd,actual_source=record(target));data['sources'][key]['patched_sha256']=record(target)['sha256']
 require(provider_sources[1].read_text()==patch_vulkan(provider_sources[0].read_text()),'Packed shader restoration must remain the sole provider-view difference')
 old_entry=Path(prior['expert_q2_model']['actual_entry']['path']);old_cache=Path(prior['expert_q2_model']['actual_cache']['path']);require(record(old_entry)==prior['expert_q2_model']['actual_entry']and record(old_cache)==prior['expert_q2_model']['actual_cache'],'Exact mixed entry/cache source required')
 entry=a.out/'Expert-all-Q2-model.private.cpp';cache=a.out/'Expert-all-Q2-cache.private.cpp';entry.write_text(entry_source(old_entry.read_text()),newline='\n');cache.write_text(cache_source(old_cache.read_text()),newline='\n')
 old_cache_row=next(r for r in ios[1]['objects']if r['source']=='src/llama-moe-cache.cpp');commands=[];objects=[]
 for original,src,name in [(prior['compile_commands'][0],entry,'entry'),(old_cache_row['command'],cache,'cache')]:
  cmd=original.copy();require(isinstance(cmd,list),'Captured actual native compile command required');obj=a.out/(name+'.o');cmd[cmd.index('-c')+1]=str(src);cmd[cmd.index('-o')+1]=str(obj)
  if '-MF'in cmd:cmd[cmd.index('-MF')+1]=str(a.out/(name+'.private.d'))
  cmd[1:1]=['-I',str(a.out)];cmd+=['-I',str(old_entry.parent),'-I',str(old_cache.parent),'-I',str(ROOT/'native/app')];commands.append(cmd);objects.append(obj)
 replacements={prior['compile_commands'][0][prior['compile_commands'][0].index('-o')+1]:str(objects[0]),old_cache_row['object']['path']:str(objects[1]),prior['lossless_shader_storage']['vulkan_object']['path']:str(provider_objects[1])}
 for name in replacements:require(prior['link_command'].count(name)==1,'Exactly one selected native object replacement required: '+name)
 link=[replacements.get(x,x)for x in prior['link_command']];image=a.out/'qwen-native.pie.elf';link[link.index('-o')+1]=str(image);link=[('-Map='+str(a.out/'native-link.private.map'))if x.startswith('-Map=')else x for x in link]
 frozen +=[record(x)for x in (old_entry,old_cache,entry,cache,ROOT/'native/app/expert_all_q2_receipt.h',ROOT/'native/app/expert_all_q2_source_integrity.h',ROOT/'native/app/expert_all_q2_cache_reset.h')]
 for i,cmd in enumerate(provider_commands+commands+[link]):
  if a.finalize_existing:
   if i>=2:require((a.out/f'{i}.private.log').is_file(),'Completed compiler/link log required')
   continue
  if i<2 and a.reuse_compiled_providers:
   print(json.dumps(dict(exact_compiled_provider_reused=i+1,recompiled=False)),flush=True);continue
  run=subprocess.run(cmd,cwd=ROOT,capture_output=True,timeout=600,env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp')));(a.out/f'{i}.private.log').write_bytes(run.stdout+run.stderr);require(run.returncode==0,run.stderr.decode(errors='replace')[-6500:]);print(json.dumps(dict(all_Q2_native_build_step=i+1,total=5,PS5_operations=0)),flush=True)
 for row in frozen:require(record(row['path'])==row,'An actual native input changed during the all-Q2 link')
 io_rows=[]
 for i,(label,data)in enumerate(zip(('parent','extended'),ios)):
  row=next(r for r in data['objects']if r['source']==key);row['object']=record(provider_objects[i])
  row=next(r for r in data['objects']if r['source']=='src/llama-moe-cache.cpp');row.update(object=record(objects[1]),command=commands[1],actual_source=record(cache),logical_source_before_VFS=record(cache));data['sources']['src/llama-moe-cache.cpp']['patched_sha256']=record(cache)['sha256']
  path=a.out/label/'model-io.private.json';write_json(path,data);validate_overrides(path,prior['engine_receipt']['path']);io_rows.append(record(path))
 replace={embedded['parent_model_io']['path']:io_rows[0],embedded['extended_model_io']['path']:io_rows[1],embedded['vulkan_object']['path']:record(provider_objects[1])}
 def updated(rows):return[replace.get(r['path'],r)for r in rows]
 added=[record(x)for x in provider_sources+provider_objects+objects+[cache,entry]]
 embedded.update(parent_model_io=io_rows[0],extended_model_io=io_rows[1],vulkan_object=record(provider_objects[1]),inputs=updated(embedded['inputs'])+added)
 ep=a.out/'embedded-shader.private.json';write_json(ep,embedded);replace[external['embedded_control']['path']]=record(ep)
 external.update(parent_model_io=io_rows[0],extended_model_io=io_rows[1],vulkan_object=record(provider_objects[1]),embedded_control=record(ep),inputs=updated(external['inputs'])+added)
 xp=a.out/'external-shader.private.json';write_json(xp,external);storage=validate_shader_resources(xp,io_rows[1]['path'],prior['engine_receipt']['path'])
 result=copy.deepcopy(prior);result.update(artifact=record(image),compile_commands=[commands[0]],link_command=link,source_parent=record(a.parent),inputs_before=frozen+added+io_rows+[record(ep),record(xp)],bounded_model_source_manifest=io_rows[1],bounded_model_source_overrides=ios[1],shader_resource_manifest=record(xp),lossless_shader_storage=storage,lossless_driver_table_geometry=audit_linked_storage(image,prior['lossless_driver_tables']))
 result['expert_q2_model'].update(scope=SCOPE,actual_entry=record(entry),actual_cache=record(cache),commands=commands,packed_source_scope=PACKED_SCOPE,GPU_math_and_provider_objects_unchanged=False,all_Q2_provider_commands=provider_commands,Down_encoding='signed_FP16_scale_MSE_fit',same_GPU_cache_budget=True,active_cache_slots=867,full_model_native_validation_pending=True,production_adopted=False)
 if completed:
  require(result['artifact']==completed['artifact']and result['link_command']==completed['link_command'],'Audit-only finalization cannot change the native link')
  result['completed_compile_generator_snapshot']=record(ROOT/'.local/build_expert_all_q2_model_8630.snapshot.py')
 target=a.out/'receipt.private.json';write_json(target,result);result['real_module_import_audit']=audit(a.workspace,a.cache,a.out);result['native_dispatch_audit']=dispatch(a.workspace,a.workspace/'driver-work/PS5-Vulkan-Inference-qwen-872cc126',image,a.out/'dispatch')
 require(not result['real_module_import_audit']['missing']and result['native_dispatch_audit']['passed'],'Actual native imports/driver dispatch audit failed');write_json(target,result)
 print(json.dumps(dict(all_Expert_Q2_full_model_candidate_built=True,active_cache_slots=867,PS5_operations=0,CI_runs=0)),flush=True)
if __name__=='__main__':main()
