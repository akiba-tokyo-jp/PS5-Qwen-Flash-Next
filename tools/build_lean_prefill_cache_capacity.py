#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Expand only CPU miss bookkeeping for the already scoped sixteen-token batch."""
import argparse,copy,json,os,subprocess
from pathlib import Path
from active_native_inputs import active_link_inputs
from expert_q4 import require,record,write_json
from build_speculative_batch_probe import once
from driver_table_storage import audit_linked_storage
from audit_native_imports import audit
from native_dispatch import audit as dispatch

def cache_source(text):
 text=once(text,'std::array<bool,40> delivered{};','std::array<bool,160> delivered{};')
 return once(text,'std::array<size_t,40>selected{};','std::array<size_t,160>selected{};')

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for key in ('parent','workspace','cache','out'):p.add_argument('--'+key,type=Path,required=True)
 a=p.parse_args();prior=json.loads(a.parent.read_text());old=prior['routing_sharing']['actual_sources']['cache']
 frozen=active_link_inputs(prior)+[r for r in prior['inputs_before']if Path(r['path']).suffix=='.so']+[record(a.parent),record(Path(__file__))]
 for r in frozen:require(record(r['path'])==r,'Completed native provider changed')
 a.out.mkdir(parents=True,exist_ok=False);(a.out/'tmp').mkdir()
 source=a.out/'cache.private.cpp';source.write_text(cache_source(Path(old['path']).read_text()),newline='\n')
 command=prior['routing_sharing']['commands'][1].copy();oldobj=command[command.index('-o')+1];obj=a.out/'cache.o';command[command.index('-c')+1]=str(source);command[command.index('-o')+1]=str(obj)
 if '-MF'in command:command[command.index('-MF')+1]=str(a.out/'cache.private.d')
 image=a.out/'qwen-native.pie.elf';link=[str(obj)if x==oldobj else x for x in prior['link_command']];link[link.index('-o')+1]=str(image)
 link=[('-Map='+str(a.out/'native-link.private.map'))if x.startswith('-Map=')else x for x in link]
 for i,cmd in enumerate((command,link)):
  run=subprocess.run(cmd,capture_output=True,timeout=600,env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp')))
  (a.out/f'{i}.private.log').write_bytes(run.stdout+run.stderr);require(run.returncode==0,run.stderr.decode(errors='replace')[-4500:]);print(json.dumps(dict(cache_capacity_build_step=i+1,total=2)),flush=True)
 for r in frozen:require(record(r['path'])==r,'Completed frozen source changed')
 r=copy.deepcopy(prior);entry=record(source);r.update(artifact=record(image),link_command=link,source_parent=record(a.parent),
  inputs_before=frozen+[record(source),record(obj)],lossless_driver_table_geometry=audit_linked_storage(image,prior['lossless_driver_tables']))
 r['expert_q2_model']['actual_cache']=entry;r['expert_q2_model']['commands'][1]=command
 r['routing_sharing']['actual_sources']['cache']=entry;r['routing_sharing']['commands'][1]=command
 r['lean_prefill']['actual_sources']['cache']=entry
 r['lean_prefill']['CPU_miss_bookkeeping_capacity']=dict(previous=40,selected=160,maximum_tokens=16,Experts_per_prefill_token=10,additional_stack_bytes=1080,physical_IO_and_GPU_allocations_unchanged=True)
 target=a.out/'receipt.private.json';write_json(target,r)
 r['real_module_import_audit']=audit(a.workspace,a.cache,a.out);r['native_dispatch_audit']=dispatch(a.workspace,a.workspace/'driver-work/PS5-Vulkan-Inference-qwen-872cc126',image,a.out/'dispatch')
 require(not r['real_module_import_audit']['missing']and r['native_dispatch_audit']['passed'],'Actual imports/dispatch required');write_json(target,r)
 print('Two CPU metadata arrays expanded; original source delivery and GPU providers unchanged.',flush=True)
if __name__=='__main__':main()
