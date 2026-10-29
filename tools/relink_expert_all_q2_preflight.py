#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Replace only the all-Q2 source owner's physical preflight selection."""
import argparse,copy,json,os,subprocess
from pathlib import Path
from expert_q4 import record,require,write_json
from expert_all_q2_preflight import reader_header
from active_native_inputs import active_link_inputs
from driver_table_storage import audit_linked_storage
from native_dispatch import audit as dispatch
from audit_native_imports import audit
ROOT=Path(__file__).resolve().parents[1]

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('parent','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 p.add_argument('--reuse-owner',type=Path);a=p.parse_args();prior=json.loads(a.parent.read_text());details=prior['expert_q2_model']
 require(details['scope']['Expert_format']=='Gate_Up_Q2_K_Down_Q2_0_MSE','Separate all-Q2 candidate required')
 frozen=active_link_inputs(prior)+[r for r in prior['inputs_before']if Path(r['path']).suffix=='.so']+[record(a.parent),record(__file__),record(ROOT/'tools/expert_all_q2_preflight.py')]
 for r in frozen:require(record(r['path'])==r,'Actual parent changed')
 a.out.mkdir(parents=True,exist_ok=False);(a.out/'tmp').mkdir()
 original=Path(details['reader_header']['path']);header=a.out/'resident-mapped-source.private.h';header.write_text(reader_header(original.read_text()),newline='\n')
 command=details['packed_source_commands'][1].copy();source=Path(details['source_owner']['path']);require(record(source)==details['source_owner'],'Qualified source owner changed')
 old_object=command[command.index('-o')+1];obj=a.out/'owner.o';command[command.index('-o')+1]=str(obj)
 if '-MF'in command:command[command.index('-MF')+1]=str(a.out/'owner.private.d')
 aliases={original.resolve()}
 for i,arg in enumerate(command[:-1]):
  if arg=='-I':
   path=Path(command[i+1])/header.name
   if path.is_file():aliases.add(path.resolve())
  if arg=='-ivfsoverlay':
   for row in json.loads(Path(command[i+1]).read_text()).get('roots',[]):
    if Path(row.get('name','')).name==header.name:aliases.add(Path(row['name']).resolve())
 overlay=a.out/'reader-overlay.private.json';write_json(overlay,dict(version=0,**{'case-sensitive':'false','use-external-names':False},roots=[dict(type='file',name=str(x).replace('\\','/'),**{'external-contents':str(header).replace('\\','/')})for x in sorted(aliases)]))
 command[1:1]=['-I',str(a.out)];command+=['-ivfsoverlay',str(overlay)]
 if a.reuse_owner:
  saved=json.loads(a.reuse_owner.read_text())['all_Q2_payload_preflight'];require(Path(saved['header']['path']).read_bytes()==header.read_bytes()and record(saved['object']['path'])==saved['object'],'Exact compiled preflight owner required');obj=Path(saved['object']['path']);command=saved['command'];frozen +=[record(a.reuse_owner),saved['header'],saved['object']]
 else:
  run=subprocess.run(command,capture_output=True,timeout=300,env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp')));(a.out/'owner.private.log').write_bytes(run.stdout+run.stderr);require(run.returncode==0,run.stderr.decode(errors='replace')[-6000:])
 require(prior['link_command'].count(old_object)==1,'Exactly one original owner replacement required')
 link=[str(obj)if x==old_object else x for x in prior['link_command']];image=a.out/'qwen-native.pie.elf';link[link.index('-o')+1]=str(image);link=[('-Map='+str(a.out/'native-link.private.map'))if x.startswith('-Map=')else x for x in link]
 run=subprocess.run(link,capture_output=True,timeout=300,env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp')));(a.out/'link.private.log').write_bytes(run.stdout+run.stderr);require(run.returncode==0,run.stderr.decode(errors='replace')[-6000:])
 for r in frozen:require(record(r['path'])==r,'An actual native input changed during relink')
 result=copy.deepcopy(prior);result.update(artifact=record(image),link_command=link,source_parent=record(a.parent),inputs_before=frozen+[record(header),record(source),record(overlay),record(obj)],lossless_driver_table_geometry=audit_linked_storage(image,prior['lossless_driver_tables']))
 result['expert_q2_model'].update(reader_header=record(header))
 result['all_Q2_payload_preflight']=dict(header=record(header),object=record(obj),source=record(source),command=command,overlay=record(overlay),physical_payload_minimum_bytes=16<<20,original_byte_checks_and_parallel_coalesced_counters_preserved=True,GPU_and_memory_guards_unchanged=True,entry_cache_and_GPU_objects_unchanged=True)
 target=a.out/'receipt.private.json';write_json(target,result);result['real_module_import_audit']=audit(a.workspace,a.cache,a.out);result['native_dispatch_audit']=dispatch(a.workspace,a.workspace/'driver-work/PS5-Vulkan-Inference-qwen-872cc126',image,a.out/'dispatch');require(not result['real_module_import_audit']['missing']and result['native_dispatch_audit']['passed'],'Real native import/dispatch audit failed');write_json(target,result)
 print(json.dumps(dict(all_Q2_payload_preflight_relinked=True,PS5_operations=0)),flush=True)
if __name__=='__main__':main()
