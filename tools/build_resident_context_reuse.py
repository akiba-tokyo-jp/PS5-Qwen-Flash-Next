#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compile metadata reset on qualified complete app dependencies and link once."""
import argparse,copy,json,os,subprocess
from pathlib import Path
from shader_storage import record
from driver_table_storage import audit_linked_storage
from audit_native_imports import audit
from native_dispatch import audit as dispatch
from resident_cache_reuse import generate as model_source
from resident_context_entry import generate as entry_source
ROOT=Path(__file__).resolve().parents[1]


def main():
 p=argparse.ArgumentParser();p.add_argument('--parent',type=Path,required=True);p.add_argument('--entry-parent',type=Path,required=True);p.add_argument('--reuse-model-object',type=Path);p.add_argument('--workspace',type=Path,required=True);p.add_argument('--cache',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 prior=json.loads(a.parent.read_text());entry=json.loads(a.entry_parent.read_text())
 for row in prior['inputs_before']+entry['inputs_before']+[prior['artifact'],entry['artifact']]:
  if record(row['path'])!=row:raise ValueError('Qualified reuse input changed: '+row['path'])
 a.out.mkdir(parents=True);(a.out/'tmp').mkdir();commands=[];extra=[record(x)for x in (Path(__file__),a.parent,a.entry_parent,ROOT/'tools/resident_cache_reuse.py',ROOT/'tools/resident_context_entry.py',ROOT/'native/app/resident_cache_reset.h')]
 # The parent owns all ten ABI-consistent app dependencies for six-demand I/O.
 view=ROOT.parent/'PS5-Qwen-Flash-Next-refill/native/app';assert view.is_dir()
 extra +=[record(x)for x in sorted(view.glob('*.h'))]
 moerow=copy.deepcopy(next(x for x in prior['bounded_model_source_overrides']['objects']if x['source']=='src/llama-moe-cache.cpp'))
 recipe=moerow['command'].copy();original=Path(recipe[recipe.index('-c')+1]);generated_text=model_source(original.read_text())
 if a.reuse_model_object:
  reused=json.loads(a.reuse_model_object.read_text());actual=next(x for x in reused['bounded_model_source_overrides']['objects']if x['source']=='src/llama-moe-cache.cpp')
  for row in reused['inputs_before']+[reused['artifact']]:
   if record(row['path'])!=row:raise ValueError('Reused reset compilation changed')
  if Path(actual['actual_source']['path']).read_text()!=generated_text:raise ValueError('The actual reused MoE source differs')
  moerow=copy.deepcopy(actual);extra.extend((record(a.reuse_model_object),actual['actual_source'],actual['object']))
 else:
  generated=a.out/'llama-moe-cache-reuse.private.cpp';generated.write_text(generated_text,newline='\n');obj=a.out/'llama-moe-cache-reuse.o'
  recipe[recipe.index('-c')+1]=str(generated);recipe[recipe.index('-o')+1]=str(obj);recipe[1:1]=['-I',str(view),'-I',str(ROOT/'native/app')];recipe+=['-I',str(original.parent)]
  commands.append(recipe);extra.extend((record(original),record(generated)));moerow.update(command=recipe,actual_source=record(generated),object={'path':str(obj)})
 select=lambda r:[c.copy()for c in r['compile_commands']if '-c'in c and 'resident-comparison'in Path(c[c.index('-c')+1]).name]
 current=select(prior);templates=select(entry);assert len(current)==len(templates)==1
 recipe=templates[0];original=Path(recipe[recipe.index('-c')+1]);generated=a.out/'resident-comparison-context-reuse.private.cpp';generated.write_text(entry_source(original.read_text()),newline='\n');obj=a.out/'resident-comparison-context-reuse.o'
 recipe[recipe.index('-c')+1]=str(generated);recipe[recipe.index('-o')+1]=str(obj);recipe[1:1]=['-I',str(view),'-I',str(ROOT/'native/app')];recipe+=['-I',str(original.parent)]
 commands.append(recipe);extra.extend((record(original),record(generated)))
 oldmain=current[0][current[0].index('-o')+1];oldmoe=next(x for x in prior['bounded_model_source_overrides']['objects']if x['source']=='src/llama-moe-cache.cpp')['object']['path']
 link=prior['link_command'].copy();assert link.count(oldmain)==link.count(oldmoe)==1
 link=[str(obj)if x==oldmain else moerow['object']['path']if x==oldmoe else x for x in link];image=a.out/'qwen-native.pie.elf';link[link.index('-o')+1]=str(image);link=[('-Map='+str(a.out/'native-link.private.map'))if x.startswith('-Map=')else x for x in link]
 frozen=prior['inputs_before']+entry['inputs_before']+extra
 for i,command in enumerate(commands+[link]):
  result=subprocess.run(command,cwd=ROOT,capture_output=True,timeout=600,env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp')));(a.out/(str(i)+'.private.log')).write_bytes(result.stdout+result.stderr)
  if result.returncode:raise RuntimeError(result.stderr.decode(errors='replace')[-4500:])
 for row in frozen:
  if record(row['path'])!=row:raise ValueError('Frozen reset input changed')
 moerow['object']=record(moerow['object']['path']);receipt=copy.deepcopy(prior)
 selected=next(x for x in receipt['bounded_model_source_overrides']['objects']if x['source']=='src/llama-moe-cache.cpp');selected.clear();selected.update(moerow)
 receipt.update(artifact=record(image),link_command=link,compile_commands=commands,source_parent=record(a.parent),entry_parent=record(a.entry_parent),inputs_before=frozen+[record(obj),moerow['object']],
  resident_context_reuse=dict(original_contexts=1,metadata_only_reset=True,MoE=moerow,entry=record(generated),complete_app_header_view=str(view),no_driver_or_memory_floor_change=True),
  lossless_driver_table_geometry=audit_linked_storage(image,prior['lossless_driver_tables']))
 target=a.out/'receipt.private.json';target.write_text(json.dumps(receipt,indent=2)+'\n')
 receipt['real_module_import_audit']=audit(a.workspace,a.cache,a.out);assert not receipt['real_module_import_audit']['missing']
 receipt['native_dispatch_audit']=dispatch(a.workspace,a.workspace/'driver-work/PS5-Vulkan-Inference-qwen-872cc126',image,a.out/'dispatch');assert receipt['native_dispatch_audit']['passed']
 target.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(dict(original_context_reuse_linked=True,metadata_only_reset=True,PS5_operations=0)),flush=True)
if __name__=='__main__':main()
