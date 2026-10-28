#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Price only pre-GPU CPU metadata from the existing Direct calibration."""
import argparse,copy,json,os,re,subprocess
from pathlib import Path
from shader_storage import record
from driver_table_storage import audit_linked_storage
from audit_native_imports import audit
from native_dispatch import audit as dispatch
ROOT=Path(__file__).resolve().parents[1]


def main():
 p=argparse.ArgumentParser();p.add_argument('--parent',type=Path,required=True);p.add_argument('--workspace',type=Path,required=True);p.add_argument('--cache',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 prior=json.loads(a.parent.read_text());a.out.mkdir(parents=True);view=a.out/'app-view';view.mkdir();(a.out/'tmp').mkdir()
 for row in prior['inputs_before']+[prior['artifact']]:
  if record(row['path'])!=row:raise ValueError('Qualified CPU-scope input changed: '+row['path'])
 actual=ROOT.parent/'PS5-Qwen-Flash-Next-refill/native/app';extra=[record(Path(__file__)),record(a.parent)];origins={}
 for folder in (actual,ROOT/'native/app'):
  for path in sorted(folder.glob('*.h')):
   if path.name in origins:continue
   (view/path.name).write_bytes(path.read_bytes());origins[path.name]=path;extra.append(record(path))
 declaration='''// This declaration is active only in the explicit generated CPU test view.
extern "C" bool qwen_app_resident_CPU_metadata_scope_active();
extern "C" void qwen_app_select_resident_CPU_metadata_scope(bool);
'''
 (view/'resident_CPU_metadata_scope.h').write_text(declaration,newline='\n')
 path=view/'system_memory.h';text=path.read_text();needle='namespace qwen_app {';assert text.count(needle)==1;text=text.replace(needle,'#include "resident_CPU_metadata_scope.h"\n'+needle)
 needle='const auto extra=std::max<std::uint64_t>(s.kernel_reserved,kernel_memory_margin/s.page_size);';assert text.count(needle)==1
 text=text.replace(needle,'const auto extra=qwen_app_resident_CPU_metadata_scope_active()?21ull:std::max<std::uint64_t>(s.kernel_reserved,kernel_memory_margin/s.page_size);')
 path.write_text(text,newline='\n')
 # The existing source allocator pays its separate 19-page new-map allowance.
 path=view/'resident_phase_vm.h';text=path.read_text();needle='std::max<std::uint64_t>(m.kernel_reserved,256)';assert text.count(needle)==1
 text=text.replace(needle,'(qwen_app_resident_CPU_metadata_scope_active()?21ull:std::max<std::uint64_t>(m.kernel_reserved,256))');path.write_text(text,newline='\n')
 phase_impl='''#include <atomic>
static std::atomic<unsigned> resident_CPU_metadata_phase{0};
extern "C" bool qwen_app_resident_CPU_metadata_scope_active(){return resident_CPU_metadata_phase.load()==1;}
extern "C" void qwen_app_select_resident_CPU_metadata_scope(bool active){
    unsigned expected=active?0:1;
    if(!resident_CPU_metadata_phase.compare_exchange_strong(expected,active?1u:2u))
        throw std::runtime_error("CPU metadata scope is once-only and cannot reenter after GPU pricing");
}
'''
 recipes={};seen=set()
 def scan(value):
  if isinstance(value,dict):
   for key,item in value.items():
    if key in ('compile_command','command')and isinstance(item,list)and all(isinstance(x,str)for x in item)and '-c'in item and '-o'in item:recipes.setdefault(str(Path(item[item.index('-o')+1]).resolve()),item.copy())
    elif key in ('compile_commands','commands')and isinstance(item,list):
     for command in item:
      if isinstance(command,list)and all(isinstance(x,str)for x in command)and '-c'in command and '-o'in command:recipes.setdefault(str(Path(command[command.index('-o')+1]).resolve()),command.copy())
    if key not in ('inputs_before','inputs','application_headers','application_sources'):scan(item)
  elif isinstance(value,list):
   for item in value:scan(item)
 def ancestry(path):
  path=Path(path).resolve()
  if path in seen:return
  if len(seen)>=64:raise ValueError('Compile ancestry bound exceeded')
  seen.add(path);data=json.loads(path.read_text());extra.append(record(path));scan(data)
  for key in ('source_parent','parent_native','entry_parent'):
   if key in data:
    row=data[key]
    if record(row['path'])!=row:raise ValueError('Compile ancestry changed')
    ancestry(row['path'])
 ancestry(a.parent)
 def uses_system(path,visited=None):
  path=Path(path);visited=set()if visited is None else visited
  if path in visited:return False
  visited.add(path)
  if path.name=='system_memory.h':return True
  for name in re.findall(r'^\s*#\s*include\s*"([^"]+)"',path.read_text(errors='replace'),re.M):
   for child in (path.parent/name,actual/name,ROOT/'native/app'/name):
    if child.is_file():
     if uses_system(child,visited):return True
     break
  return False
 commands=[];replacements={};changed=[]
 for old in prior['link_command']:
  recipe=recipes.get(str(Path(old).resolve()))if old.endswith(('.o','.obj'))else None
  if not recipe:continue
  source=Path(recipe[recipe.index('-c')+1]);is_main='resident-comparison'in source.name
  if not source.is_file()or not(is_main or uses_system(source)):continue
  generated=view/source.name;text=source.read_text()
  if source.name=='system_memory.cpp':text=text.replace('namespace qwen_app {',phase_impl+'\nnamespace qwen_app {',1)
  if is_main:
   needle='        qwen_app_configure_resident_cache_reuse(true);';assert text.count(needle)==1
   text=text.replace(needle,needle+'''
        const Json CPU_scope={{"schema","ps5-qwen-CPU-metadata-21-v1"},{"enabled",true},{"sampled_Direct_metadata_pages",17},
            {"sampled_idle_pages",2},{"selected_extra_pages",2},{"selected_CPU_minimum_extra_pages",21},
            {"GPU_floor_unchanged",true},{"exit_before_original_GPU_price",true},{"universal_peak_bound_established",false},{"automatic_retries",0}};
        if(policy.at("native_resident_CPU_metadata")!=CPU_scope)throw std::runtime_error("Exact measured CPU metadata scope required");
        qwen_app_select_resident_CPU_metadata_scope(true);
''')
   needle='        resident_sample("phase_local_after_startup_settle");';assert text.count(needle)==1
   text=text.replace(needle,needle+'\n        qwen_app_select_resident_CPU_metadata_scope(false);\n        if(qwen_app_resident_CPU_metadata_scope_active())throw std::runtime_error("CPU scope must end before original GPU admission");')
   needle='\n        qwen_native_gpu_initialize((startup.admission_report+".driver.log").c_str());';assert text.count(needle)==1
   text=text.replace(needle,'\n        if(qwen_app_resident_CPU_metadata_scope_active())throw std::runtime_error("GPU initialization cannot use the CPU metadata floor");'+needle)
   needle='{"kernel_extra_margin_bytes",qwen_app::kernel_memory_margin}';assert text.count(needle)>=1
   text=text.replace(needle,
    '{"kernel_extra_margin_bytes",qwen_app_resident_CPU_metadata_scope_active()?21ull*16384:qwen_app::kernel_memory_margin},{"CPU_metadata_scope_active",qwen_app_resident_CPU_metadata_scope_active()}')
  generated.write_text(text,newline='\n');obj=a.out/(str(len(commands))+'-'+source.stem+'.o')
  command=recipe.copy();command[command.index('-c')+1]=str(generated);command[command.index('-o')+1]=str(obj);command[1:1]=['-I',str(view)];command+=['-I',str(source.parent)]
  commands.append(command);replacements[old]=str(obj);changed.append(dict(original=record(source),source=record(generated),object_path=str(obj),command=command))
 assert sum(Path(c[c.index('-c')+1]).name=='system_memory.cpp'for c in commands)==1
 assert sum('resident-comparison'in Path(c[c.index('-c')+1]).name for c in commands)==1
 link=[replacements.get(x,x)for x in prior['link_command']];image=a.out/'qwen-native.pie.elf';link[link.index('-o')+1]=str(image);link=[('-Map='+str(a.out/'native-link.private.map'))if x.startswith('-Map=')else x for x in link]
 frozen=prior['inputs_before']+extra+[record(x)for x in sorted(view.iterdir())]
 for i,command in enumerate(commands+[link]):
  result=subprocess.run(command,cwd=ROOT,capture_output=True,timeout=600,env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp')));(a.out/(str(i)+'.private.log')).write_bytes(result.stdout+result.stderr)
  if result.returncode:raise RuntimeError(result.stderr.decode(errors='replace')[-4500:])
  print(json.dumps(dict(CPU_scope_compiled_or_linked=i+1,total=len(commands)+1)),flush=True)
 for row in frozen:
  if record(row['path'])!=row:raise ValueError('Frozen CPU-scope input changed')
 receipt=copy.deepcopy(prior);receipt.update(artifact=record(image),link_command=link,compile_commands=commands,source_parent=record(a.parent),inputs_before=frozen+[record(x)for x in replacements.values()],
  CPU_metadata_scope=dict(selected_minimum_extra_pages=21,GPU_operational_floor_unchanged=True,once_only_before_GPU=True,changed_sources=changed),
  lossless_driver_table_geometry=audit_linked_storage(image,prior['lossless_driver_tables']))
 target=a.out/'receipt.private.json';target.write_text(json.dumps(receipt,indent=2)+'\n')
 receipt['real_module_import_audit']=audit(a.workspace,a.cache,a.out);assert not receipt['real_module_import_audit']['missing']
 receipt['native_dispatch_audit']=dispatch(a.workspace,a.workspace/'driver-work/PS5-Vulkan-Inference-qwen-872cc126',image,a.out/'dispatch');assert receipt['native_dispatch_audit']['passed']
 target.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(dict(CPU_metadata_only_scope_linked=True,GPU_floor_unchanged=True,PS5_operations=0)),flush=True)
if __name__=='__main__':main()
