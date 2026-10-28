#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Move the one complete SELF read before C++ initialization, then bind SHA."""
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
  if record(row['path'])!=row:raise ValueError('Qualified source changed: '+row['path'])
 a.out.mkdir(parents=True);(a.out/'tmp').mkdir();commands=[];replacements={};inputs=[record(Path(__file__)),record(a.parent),record(ROOT/'native/app/resident_early_SELF.h'),record(ROOT/'native/app/resident_early_SELF.c')]
 def recipe_for(obj,data,seen=None):
  seen=set()if seen is None else seen
  found=[c.copy()for c in data['compile_commands']if '-c'in c and c[c.index('-o')+1]==obj]
  if len(found)==1:return found[0]
  for key in ('source_parent','parent_native'):
   if key in data and data[key]['path']not in seen:
    path=data[key]['path'];seen.add(path)
    if record(path)!=data[key]:raise ValueError('Compile provenance parent changed')
    try:return recipe_for(obj,json.loads(Path(path).read_text()),seen)
    except LookupError:pass
  raise LookupError('Exact linked compile recipe absent: '+obj)
 def derive(recipe,original,text,name):
  source=a.out/(name+'.private.cpp');source.write_text(text,newline='\n');obj=a.out/(name+'.o');old=recipe[recipe.index('-o')+1]
  if prior['link_command'].count(old)!=1:raise ValueError('Unique linked entry/bootstrap required')
  recipe[recipe.index('-c')+1]=str(source);recipe[recipe.index('-o')+1]=str(obj);recipe+=['-I',str(original.parent),'-I',str(ROOT/'native/app')]
  commands.append(recipe);replacements[old]=str(obj);inputs.extend([record(original),record(source)]);return source,obj
 boot=prior['resident_bootstrap_namespace'];recipe=recipe_for(boot['object']['path'],prior);original=Path(recipe[recipe.index('-c')+1]);text=original.read_text()
 needle='    qwen_native_stage("bootstrap_completed before_CXX_initializers");'
 assert text.count(needle)==1
 text='extern "C" int qwen_resident_hash_SELF_before_CXX();\n'+text.replace(needle,
  '    if(!qwen_resident_hash_SELF_before_CXX())stop_bootstrap("early_SELF_Direct_integrity_failed_before_CXX");\n'+needle)
 boot_source,boot_obj=derive(recipe,original,text,'native-bootstrap-early-SELF')
 candidates=[c.copy()for c in prior['compile_commands']if '-c'in c and 'resident-comparison'in Path(c[c.index('-c')+1]).name];assert len(candidates)==1
 recipe=candidates[0];original=Path(recipe[recipe.index('-c')+1]);text=original.read_text();main_at=text.index('int main(int argc, char ** argv)')
 helper='''static Json bind_resident_early_SELF(const Json &policy){
    const Json expected={{"schema","ps5-qwen-early-SELF-v1"},{"enabled",true},{"window_bytes",65536},
        {"sampled_Direct_metadata_pages",17},{"sampled_idle_pages",2},{"selected_extra_pages",2},
        {"CPU_floor","kernel_minimum_plus_21"},{"GPU_and_ordinary_floor_unchanged",true},
        {"whole_SHA_bound_to_current_launch",true},{"automatic_retries",0}};
    if(policy.at("native_resident_early_SELF")!=expected)throw std::runtime_error("Exact early CPU SELF scope required");
    const auto *r=qwen_resident_early_SELF_result();const auto &binding=policy.at("native_first_generation_validation");
    if(!r||!r->completed||!r->Direct_flag_verified||!r->bytes||r->bytes!=binding.at("candidate_SELF_bytes")||
       r->read_calls!=(r->bytes+65535)/65536+1||r->minimum_free<r->selected_floor||r->selected_floor!=r->minimum+21)
        throw std::runtime_error("Complete early whole SELF proof required");
    std::string sha;for(const auto b:r->sha256){sha.push_back("0123456789abcdef"[b>>4]);sha.push_back("0123456789abcdef"[b&15]);}
    if(sha!=binding.at("candidate_SELF_sha256"))throw std::runtime_error("Early SELF full SHA differs from current launch");
    const int fd=open("/app0/eboot.bin",O_RDONLY|O_NOFOLLOW);struct stat current{};
    if(fd<0||fstat(fd,&current))throw std::runtime_error("Early SELF current descriptor unavailable");
    const auto identity=qwen_app::resident_file_identity(current);if(close(fd))throw std::runtime_error("Early SELF descriptor close failed");
    if(!std::equal(identity.begin(),identity.end(),r->identity))throw std::runtime_error("Early SELF current inode identity changed");
    return {{"completed",true},{"SELF_bytes",r->bytes},{"SELF_sha256",sha},{"maximum_read_window_bytes",65536},
        {"read_calls",r->read_calls},{"elapsed_ns",r->elapsed_ns},{"free_before",r->free_before},{"free_after",r->free_after},
        {"minimum_sampled_free",r->minimum_free},{"kernel_minimum",r->minimum},{"kernel_reserved",r->reserved},
        {"selected_CPU_floor",r->selected_floor},{"GPU_and_ordinary_floor_unchanged",true},
        {"full_current_SELF_SHA256_passed",true},{"source_phase","before_CXX_initializers"},{"GPU_calls",0},{"passes",1}};
}
'''
 text='#include "resident_early_SELF.h"\n'+text[:main_at]+helper+text[main_at:]
 needle='        qwen_app::require_resident_direct_table_policy(policy);';assert text.count(needle)==1
 text=text.replace(needle,'        const auto early_SELF=bind_resident_early_SELF(policy);\n'+needle)
 begin=text.index('                const auto before_postloader=');end=text.index('        qwen_native_stage("complete_SELF_and_receipt_direct_SHA256_passed',begin)
 text=text[:begin]+'''                write_fresh_report(startup.admission_report+".resident.postloader-SELF",early_SELF);
                qwen_native_stage("early_SELF_SHA_bound_to_current_launch_without_duplicate_payload_read_GPU_not_started=1");
'''+text[end:]
 main_source,main_obj=derive(recipe,original,text,'resident-comparison-early-SELF')
 c=commands[-1].copy();clean=[];i=0
 while i<len(c):
  arg=c[i]
  if arg in ('-nostdinc++','-fexceptions','-fcxx-exceptions','-frtti')or arg.startswith('-std='):i+=1;continue
  if arg=='-isystem'and '/c++/'in c[i+1].replace('\\','/') :i+=2;continue
  clean.append(arg);i+=1
 clean[0]=str(Path(clean[0]).with_name('clang.exe'));clean[clean.index('-c')+1]=str(ROOT/'native/app/resident_early_SELF.c');cobj=a.out/'early-SELF.o';clean[clean.index('-o')+1]=str(cobj);clean+=['-std=c11'];commands.append(clean)
 image=a.out/'qwen-native.pie.elf';link=[replacements.get(x,x)for x in prior['link_command']];link.insert(link.index('--start-group'),str(cobj));link[link.index('-o')+1]=str(image);link=[('-Map='+str(a.out/'native-link.private.map'))if x.startswith('-Map=')else x for x in link]
 frozen=prior['inputs_before']+inputs
 for index,command in enumerate(commands+[link]):
  result=subprocess.run(command,cwd=ROOT,capture_output=True,timeout=600,env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp')))
  (a.out/(str(index)+'.private.log')).write_bytes(result.stdout+result.stderr)
  if result.returncode:raise RuntimeError(result.stderr.decode(errors='replace')[-4000:])
 for row in frozen:
  if record(row['path'])!=row:raise ValueError('Frozen early SELF source changed')
 receipt=copy.deepcopy(prior);receipt.update(artifact=record(image),link_command=link,compile_commands=commands,
  source_parent=record(a.parent),inputs_before=frozen+[record(x)for x in [*replacements.values(),cobj]],
  resident_early_SELF=dict(pure_C_source=record(ROOT/'native/app/resident_early_SELF.c'),bootstrap=record(boot_source),
   current_launch_SHA_and_identity_bound_before_GPU=True,read_window_bytes=65536,selected_CPU_minimum_extra_pages=21,
   original_GPU_and_ordinary_floor_preserved=True,late_duplicate_payload_read_removed=True),
  lossless_driver_table_geometry=audit_linked_storage(image,prior['lossless_driver_tables']))
 receipt['resident_bootstrap_namespace'].update(object=record(boot_obj),generated=record(boot_source))
 target=a.out/'receipt.private.json';target.write_text(json.dumps(receipt,indent=2)+'\n')
 receipt['real_module_import_audit']=audit(a.workspace,a.cache,a.out);assert not receipt['real_module_import_audit']['missing']
 receipt['native_dispatch_audit']=dispatch(a.workspace,a.workspace/'driver-work/PS5-Vulkan-Inference-qwen-872cc126',image,a.out/'dispatch');assert receipt['native_dispatch_audit']['passed']
 target.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(dict(early_SELF_native_link_passed=True,ordinary_GPU_floor_unchanged=True,PS5_operations=0)),flush=True)
if __name__=='__main__':main()
