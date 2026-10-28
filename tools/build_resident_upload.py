#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Add load-only GPU copies to an already qualified finite comparison image."""
import argparse,copy,json,os,shlex,subprocess
from pathlib import Path
from shader_storage import record
from resident_upload_copy import generate
from driver_table_storage import audit_linked_storage
from audit_native_imports import audit
from native_dispatch import audit as dispatch
ROOT=Path(__file__).resolve().parents[1]


def main():
 p=argparse.ArgumentParser();p.add_argument('--parent',type=Path,required=True);p.add_argument('--workspace',type=Path,required=True);p.add_argument('--cache',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 prior=json.loads(a.parent.read_text())
 for row in prior['inputs_before']+[prior['artifact']]:
  if record(row['path'])!=row:raise ValueError('Qualified parent input changed: '+row['path'])
 a.out.mkdir(parents=True);(a.out/'tmp').mkdir();recipes=[];replacements={};inputs=[record(Path(__file__)),record(ROOT/'tools/resident_upload_copy.py'),record(a.parent)]
 main_recipe=next(c.copy()for c in prior['compile_commands']if '-c'in c and Path(c[c.index('-c')+1]).name=='resident-comparison.private.cpp')
 original=Path(main_recipe[main_recipe.index('-c')+1]);text=original.read_text()
 declaration='''extern "C" void qwen_app_resident_GPU_load_copy_counters(std::uint64_t *,std::uint64_t *);
static Json resident_GPU_upload_report(){std::uint64_t calls=0,bytes=0;qwen_app_resident_GPU_load_copy_counters(&calls,&bytes);
    return {{"completed_copy_calls",calls},{"completed_copy_bytes",bytes},{"original_fence_wait_reset_and_cleanup",true},{"resident_destination_CPU_memcpy",false}};}
'''
 main_at=text.index('int main(int argc, char ** argv)');text=text[:main_at]+declaration+text[main_at:]
 changes=[('        qwen_app::enable_resident_source_VM();','''        const Json upload_scope={{"schema","ps5-qwen-resident-GPU-load-copy-v1"},{"enabled",true},
            {"maximum_staging_bytes",67108864},{"fixture_must_pass_before_model",true},
            {"original_fence_wait_reset_and_cleanup",true},{"disabled_after_model_load",true},{"automatic_retries",0}};
        if(policy.at("native_resident_GPU_load_copy")!=upload_scope)throw std::runtime_error("Exact load-only GPU copy scope required");
        qwen_app::enable_resident_source_VM();'''),
 ('            const auto after_fixture=qwen_app::admit_native_system_memory();','''            const auto upload_fixture=resident_GPU_upload_report();
            if(!upload_fixture.at("completed_copy_calls").get<std::uint64_t>())throw std::runtime_error("Original indexed fixture did not qualify the GPU copy path");
            write_fresh_report(startup.admission_report+".resident.GPU-upload-fixture",upload_fixture);
            const auto after_fixture=qwen_app::admit_native_system_memory();'''),
 ('        qwen_native_stage("model_load_completed");','''        qwen_native_stage("model_load_completed");
        write_fresh_report(startup.admission_report+".resident.GPU-upload-loaded",resident_GPU_upload_report());'''),
 ('{"last_model_load_error",qwen_app::resident_last_model_error()},','{"last_model_load_error",qwen_app::resident_last_model_error()},{"resident_GPU_upload",resident_GPU_upload_report()},')]
 for old,new in changes:
  if text.count(old)!=1:raise ValueError('Unique native load-copy boundary required: '+old[:70])
  text=text.replace(old,new)
 def derived(recipe,source,text,name):
  generated=a.out/(name+'.private.cpp');generated.write_text(text,newline='\n');obj=a.out/(name+'.o')
  old=recipe[recipe.index('-o')+1];recipe[recipe.index('-c')+1]=str(generated);recipe[recipe.index('-o')+1]=str(obj)
  recipe+=['-I',str(source.parent)]
  if prior['link_command'].count(old)!=1:raise ValueError('Unique actual linked source object required')
  recipes.append(recipe);replacements[old]=str(obj);inputs.extend([record(source),record(generated)])
  return generated,obj,recipe
 derived(main_recipe,original,text,'resident-comparison-upload')
 phase=prior['resident_phase_source'];recipe=phase['command'].copy();source=Path(phase['generated_source']['path'])
 text='#include "native_gpu.h"\n'+source.read_text()+'''
extern "C" bool qwen_app_resident_GPU_load_copy(){return resident_VM_scope.load()&&!compute_limits.load();}
extern "C" void qwen_app_resident_GPU_upload_completed(std::uint64_t bytes){
    static std::uint64_t since_checkpoint=0;
    if(!qwen_app_resident_GPU_load_copy()||!bytes||bytes>(64u<<20))throw std::runtime_error("Completed bounded resident GPU upload required");
    since_checkpoint+=bytes;
    if(since_checkpoint>=(64u<<20)){qwen_native_driver_checkpoint();since_checkpoint=0;}
}
'''
 phase_generated,phase_obj,phase_recipe=derived(recipe,source,text,'mapped-source-upload')
 row=next(x for x in prior['bounded_model_source_overrides']['objects']if x['source']=='ggml/src/ggml-vulkan/ggml-vulkan-buffers.cpp')
 recipe=row['command']
 if isinstance(recipe,str):recipe=[x[1:-1]if x.startswith('"')and x.endswith('"')else x for x in shlex.split(recipe,posix=False)]
 else:recipe=recipe.copy()
 source=Path(recipe[recipe.index('-c')+1]);gpu_generated,gpu_obj,gpu_recipe=derived(recipe,source,generate(source.read_text()),'vulkan-buffer-upload')
 frozen=prior['inputs_before']+inputs;link=[replacements.get(x,x)for x in prior['link_command']];image=a.out/'qwen-native.pie.elf'
 link[link.index('-o')+1]=str(image);link=[('-Map='+str(a.out/'native-link.private.map'))if x.startswith('-Map=')else x for x in link]
 (a.out/'plan.private.json').write_text(json.dumps(dict(frozen=frozen,commands=recipes+[link]),indent=2)+'\n')
 for index,command in enumerate(recipes+[link]):
  result=subprocess.run(command,cwd=ROOT,capture_output=True,timeout=600,env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp')))
  (a.out/(str(index)+'.private.log')).write_bytes(result.stdout+result.stderr)
  if result.returncode:raise RuntimeError(result.stderr.decode(errors='replace')[-4500:])
 for row in frozen:
  if record(row['path'])!=row:raise ValueError('Frozen upload input changed: '+row['path'])
 receipt=copy.deepcopy(prior);replacement=next(x for x in receipt['bounded_model_source_overrides']['objects']if x['source']=='ggml/src/ggml-vulkan/ggml-vulkan-buffers.cpp')
 replacement.update(object=record(gpu_obj),command=gpu_recipe,actual_source=record(gpu_generated),original_object=replacement['object'])
 receipt.update(artifact=record(image),link_command=link,compile_commands=recipes,source_parent=record(a.parent),inputs_before=frozen+[record(x)for x in replacements.values()],
  resident_GPU_load_copy=dict(source=record(source),generated=record(gpu_generated),actual_object=record(gpu_obj),
   original_queue_fence_cleanup_preserved=True,large_resident_CPU_first_touch_avoided=True,only_enabled_before_compute_limits=True),
  lossless_driver_table_geometry=audit_linked_storage(image,prior['lossless_driver_tables']))
 receipt['resident_phase_source'].update(object=record(phase_obj),generated_source=record(phase_generated),command=phase_recipe)
 target=a.out/'receipt.private.json';target.write_text(json.dumps(receipt,indent=2)+'\n')
 receipt['real_module_import_audit']=audit(a.workspace,a.cache,a.out);assert not receipt['real_module_import_audit']['missing']
 receipt['native_dispatch_audit']=dispatch(a.workspace,a.workspace/'driver-work/PS5-Vulkan-Inference-qwen-872cc126',image,a.out/'dispatch');assert receipt['native_dispatch_audit']['passed']
 target.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(dict(resident_GPU_upload_linked=True,original_compute_unchanged=True,PS5_operations=0)),flush=True)
if __name__=='__main__':main()
