#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Tighten the internal workspace bound; retain the original total device cap."""
import argparse,copy,json,os,subprocess
from pathlib import Path
from expert_q4 import require,record,write_json
from active_native_inputs import active_link_inputs
from build_speculative_batch_probe import once
from driver_table_storage import audit_linked_storage
from audit_native_imports import audit
from native_dispatch import audit as dispatch
ROOT=Path(__file__).resolve().parents[1]
def workspace_header_source(text):
 return once(text,'model_internal_workspace_budget = 256ull << 20','model_internal_workspace_budget = 248ull << 20')
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('parent','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();prior=json.loads(a.parent.read_text());require(prior['prefill16_normal']['selected_mode']==4,'Corrected normal width16/all provider required')
 frozen=active_link_inputs(prior)+[r for r in prior['inputs_before']if Path(r['path']).suffix=='.so']+[record(a.parent),record(Path(__file__)),record(ROOT/'native/app/device_buffer_budget.h')]
 for r in frozen:require(record(r['path'])==r,'Qualified normal provider changed')
 a.out.mkdir(parents=True,exist_ok=False);(a.out/'tmp').mkdir()
 folder=Path(prior['artifact']['path']).parent
 for name in ('causal_expert_sharing.h','completed_expert_routes.h'):(a.out/name).write_bytes((folder/name).read_bytes())
 header=a.out/'device_buffer_budget.h';header.write_text(workspace_header_source((ROOT/'native/app/device_buffer_budget.h').read_text()),newline='\n')
 jobs={};replacements={};sources={};added=[record(a.out/n)for n in ('causal_expert_sharing.h','completed_expert_routes.h','device_buffer_budget.h')]
 for key,command in [('entry',prior['compile_commands'][0]),('owner',prior['all_Q2_optimized_monitor']['commands'][1])]:
  cmd=command.copy();oldsrc=Path(cmd[cmd.index('-c')+1]);oldobj=cmd[cmd.index('-o')+1];source=a.out/(key+'.private.cpp');source.write_bytes(oldsrc.read_bytes());obj=a.out/(key+'.o')
  cmd[cmd.index('-c')+1]=str(source);cmd[cmd.index('-o')+1]=str(obj);cmd[1:1]=['-I',str(a.out),'-I',str(oldsrc.parent)]
  if '-MF'in cmd:cmd[cmd.index('-MF')+1]=str(a.out/(key+'.private.d'))
  require(prior['link_command'].count(oldobj)==1,'Exactly one current normal provider must be replaced')
  jobs[key]=cmd;replacements[oldobj]=str(obj);sources[key]=record(source);added.append(record(source))
 image=a.out/'qwen-native.pie.elf';link=[replacements.get(x,x)for x in prior['link_command']];link[link.index('-o')+1]=str(image);link=[('-Map='+str(a.out/'native-link.private.map'))if x.startswith('-Map=')else x for x in link]
 for i,cmd in enumerate([*jobs.values(),link]):
  run=subprocess.run(cmd,capture_output=True,timeout=600,env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp')));(a.out/f'{i}.private.log').write_bytes(run.stdout+run.stderr)
  require(run.returncode==0,run.stderr.decode(errors='replace')[-5000:]);print(json.dumps(dict(tighter_workspace_build_step=i+1,total=3)),flush=True)
 for r in frozen:require(record(r['path'])==r,'Frozen provider changed during build')
 r=copy.deepcopy(prior);r.update(artifact=record(image),compile_commands=[jobs['entry']],link_command=link,source_parent=record(a.parent),inputs_before=frozen+added+[record(a.out/(k+'.o'))for k in jobs],lossless_driver_table_geometry=audit_linked_storage(image,prior['lossless_driver_tables']))
 r['expert_q2_model']['actual_entry']=sources['entry'];r['expert_q2_model']['commands'][0]=jobs['entry']
 r['all_Q2_optimized_monitor']['actual_entry']=sources['entry'];r['all_Q2_optimized_monitor']['commands'][:2]=[jobs['entry'],jobs['owner']]
 r['routing_winners_normal']['actual_entry']=sources['entry'];r['routing_winners_normal']['shared_providers']['entry']=sources['entry']
 r['routing_sharing']['actual_sources']['entry']=sources['entry'];r['routing_sharing']['commands'][0]=jobs['entry']
 r['prefill16_normal']['actual_sources']['entry']=sources['entry'];r['prefill16_normal']['causal_header']=record(a.out/'causal_expert_sharing.h')
 r['prefill16_normal']['workspace_budget']=dict(previous_MiB=256,selected_MiB=248,aggregate_device_MiB=1792,single_device_buffer_MiB=512,CPU_MiB=512,
  capacity_checks_tightened=True,physical_allocations_not_claimed_reduced=True,header=record(header),owner_source=sources['owner'],original_owner_source=record(Path(prior['all_Q2_optimized_monitor']['commands'][1][prior['all_Q2_optimized_monitor']['commands'][1].index('-c')+1])),owner_object=record(a.out/'owner.o'))
 target=a.out/'receipt.private.json';write_json(target,r);r['real_module_import_audit']=audit(a.workspace,a.cache,a.out);r['native_dispatch_audit']=dispatch(a.workspace,a.workspace/'driver-work/PS5-Vulkan-Inference-qwen-872cc126',image,a.out/'dispatch')
 require(not r['real_module_import_audit']['missing']and r['native_dispatch_audit']['passed'],'Native imports and dispatch required');write_json(target,r)
 print('Internal workspace cap tightened256->248MiB; total1792MiB and physical reserves unchanged.',flush=True)
if __name__=='__main__':main()
