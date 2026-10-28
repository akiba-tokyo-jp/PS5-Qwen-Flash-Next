#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Restore qualified eight MiB model reads without changing startup admission."""
import argparse,copy,json,os,subprocess
from pathlib import Path
from shader_storage import record
from driver_table_storage import audit_linked_storage
from audit_native_imports import audit
from native_dispatch import audit as dispatch
ROOT=Path(__file__).resolve().parents[1]


def main():
 p=argparse.ArgumentParser();p.add_argument('--parent',type=Path,required=True);p.add_argument('--workspace',type=Path,required=True);p.add_argument('--cache',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 prior=json.loads(a.parent.read_text())
 for row in prior['inputs_before']+[prior['artifact']]:
  if record(row['path'])!=row:raise ValueError('Qualified original-window input changed: '+row['path'])
 if 'resident_early_SELF'in prior:raise ValueError('Use the original late SELF integrity parent')
 phase=prior['resident_phase_source'];assert phase['model_load_maximum_read_bytes']==1048576
 a.out.mkdir(parents=True);(a.out/'tmp').mkdir();commands=[];replacements={};extra=[record(Path(__file__)),record(a.parent)]
 def derive(recipe,original,text,name):
  source=a.out/(name+'.private.cpp');source.write_text(text,newline='\n');obj=a.out/(name+'.o');old=recipe[recipe.index('-o')+1]
  assert prior['link_command'].count(old)==1
  recipe[recipe.index('-c')+1]=str(source);recipe[recipe.index('-o')+1]=str(obj);recipe+=['-I',str(original.parent),'-I',str(ROOT/'native/app')]
  commands.append(recipe);replacements[old]=str(obj);extra.extend((record(original),record(source)));return source,obj
 matches=[c.copy()for c in prior['compile_commands']if '-c'in c and 'resident-comparison'in Path(c[c.index('-c')+1]).name];assert len(matches)==1
 recipe=matches[0];original=Path(recipe[recipe.index('-c')+1]);text=original.read_text()
 needle='qwen_app::require_resident_load_window(policy);';assert text.count(needle)==1
 text=text.replace(needle,'if(policy.contains("native_resident_model_load_window"))throw std::runtime_error("Original eight MiB model reads require no narrower window scope");')
 derive(recipe,original,text,'resident-comparison-original-window')
 phase_recipe=phase['command'].copy();phase_source=Path(phase['generated_source']['path']);text=phase_source.read_text()
 needle='required().set_resident_load_limit(1u<<20);';assert text.count(needle)==1
 phase_generated,phase_object=derive(phase_recipe,phase_source,text.replace(needle,'required().set_resident_load_limit(model_read_window);'),'mapped-source-original-window')
 image=a.out/'qwen-native.pie.elf';link=[replacements.get(x,x)for x in prior['link_command']];link[link.index('-o')+1]=str(image);link=[('-Map='+str(a.out/'native-link.private.map'))if x.startswith('-Map=')else x for x in link]
 frozen=prior['inputs_before']+extra
 for i,command in enumerate(commands+[link]):
  result=subprocess.run(command,cwd=ROOT,capture_output=True,timeout=600,env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp')))
  (a.out/(str(i)+'.private.log')).write_bytes(result.stdout+result.stderr)
  if result.returncode:raise RuntimeError(result.stderr.decode(errors='replace')[-4000:])
 for row in frozen:
  if record(row['path'])!=row:raise ValueError('Frozen original-window input changed')
 receipt=copy.deepcopy(prior);receipt.update(artifact=record(image),link_command=link,compile_commands=commands,source_parent=record(a.parent),inputs_before=frozen+[record(x)for x in replacements.values()],
  lossless_driver_table_geometry=audit_linked_storage(image,prior['lossless_driver_tables']))
 receipt['resident_phase_source'].update(object=record(phase_object),generated_source=record(phase_generated),command=phase_recipe,model_load_maximum_read_bytes=8388608,postload_maximum_read_bytes=8388608)
 target=a.out/'receipt.private.json';target.write_text(json.dumps(receipt,indent=2)+'\n')
 receipt['real_module_import_audit']=audit(a.workspace,a.cache,a.out);assert not receipt['real_module_import_audit']['missing']
 receipt['native_dispatch_audit']=dispatch(a.workspace,a.workspace/'driver-work/PS5-Vulkan-Inference-qwen-872cc126',image,a.out/'dispatch');assert receipt['native_dispatch_audit']['passed']
 target.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(dict(original_eight_MiB_reads=True,ordinary_admission_unchanged=True,PS5_operations=0)),flush=True)
if __name__=='__main__':main()
