#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compare the selected composition using every actual installed normal provider."""
import argparse,copy,json,subprocess,sys
from pathlib import Path
from active_native_inputs import active_link_inputs
from build_speculative_batch_probe import once
from expert_q4 import record,require,write_json
ROOT=Path(__file__).resolve().parents[1]

def command(receipt,obj):
 found={}
 def walk(v):
  if isinstance(v,dict):
   for item in v.values():walk(item)
  elif isinstance(v,list):
   if all(isinstance(x,str)for x in v)and '-c'in v and '-o'in v and v[v.index('-o')+1]==obj:found[tuple(v)]=v
   else:
    for item in v:walk(item)
 walk(receipt);require(len(found)==1,'One exact actual linked provider recipe required');return next(iter(found.values()))

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in('normal','prototype','certificate','bundles','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();normal=json.loads(a.normal.read_text());n=copy.deepcopy(json.loads(a.prototype.read_text()));certificate=json.loads(a.certificate.read_text());a.out.mkdir(parents=True,exist_ok=False)
 providers={Path(x).name:x for x in normal['link_command']if Path(x).suffix in('.o','.a')};entry=n['compile_commands'][0].copy();entry_obj=entry[entry.index('-o')+1];life=certificate['frontier']['commands']['lifecycle'];life_obj=life[life.index('-o')+1]
 template=a.out/'current-entry-template.private.cpp';body=Path(entry[entry.index('-c')+1]).read_text()
 body=once(body,'qwen_app_select_current_bundle(true);','qwen_app_select_current_bundle(true);qwen_app_io_trial_select(!keep);')
 template.write_text(body,newline='\n');entry[entry.index('-c')+1]=str(template);n['compile_commands'][0]=entry
 require(certificate['throughput']['original_control_operation_order_preserved']and certificate['throughput']['extra_control_owner_snapshots']==0,'Unbiased original-order lifecycle provider required')
 n['link_command']=[entry_obj if x==providers['entry.o']else life_obj if x==providers['lifecycle.o']else x for x in normal['link_command']]
 n['inputs_before']+=active_link_inputs(normal)+active_link_inputs(certificate)+[record(template)]
 owner=command(normal,providers['owner.o']);engine=command(normal,providers['engine.o']);n['all_Q2_optimized_monitor']['commands'][1]=owner
 n['frontier']['commands'].update(owner=owner,lifecycle=life,engine=engine);n['frontier']['actual_sources'].update({k:record(v[v.index('-c')+1])for k,v in dict(owner=owner,lifecycle=life,engine=engine).items()})
 n['routing_sharing']['commands'][2]=engine;n['routing_sharing']['actual_sources']['engine']=record(engine[engine.index('-c')+1])
 n['current_installed_provider_integration']=dict(normal=record(a.normal),actual_original_owner=record(providers['owner.o']),actual_engine=record(providers['engine.o']),all_normal_link_objects_preserved_except_entry_owner_and_certificate=True,unbiased_disabled_certificate_branch=True)
 seed=a.out/'current-provider-seed.private.json';write_json(seed,n)
 subprocess.run([sys.executable,'-X','utf8','-B',str(ROOT/'tools/build_throughput_bundles.py'),'--parent',str(seed),'--workspace',str(a.workspace),'--cache',str(a.cache),'--bundles',str(a.bundles),'--out',str(a.out/'variant'),'--candidate-throughput-mode','5'],check=True)
if __name__=='__main__':main()
