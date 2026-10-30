#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Relink only the corrected finite entry; reuse every completed GPU provider."""
import argparse,copy,json,os,subprocess
from pathlib import Path
from active_native_inputs import active_link_inputs
from expert_q4 import require,record,write_json
from build_speculative_batch_probe import once
from driver_table_storage import audit_linked_storage
from audit_native_imports import audit
from native_dispatch import audit as dispatch
ROOT=Path(__file__).resolve().parents[1]

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for key in ('parent','workspace','cache','out'):p.add_argument('--'+key,type=Path,required=True)
 a=p.parse_args();prior=json.loads(a.parent.read_text());old=prior['lean_prefill']['actual_sources']['entry']
 require(prior['lean_prefill']['scope']['maximum_requests']==31,'Exact prior finite entry required')
 frozen=active_link_inputs(prior)+[r for r in prior['inputs_before']if Path(r['path']).suffix=='.so']+[record(a.parent),record(Path(__file__))]
 for r in frozen:require(record(r['path'])==r,'Completed native provider changed')
 a.out.mkdir(parents=True,exist_ok=False);(a.out/'tmp').mkdir()
 source=a.out/'entry.private.cpp';source.write_text(once(Path(old['path']).read_text(),'llama_n_batch(context)!=4||','llama_n_batch(context)!=16||'),newline='\n')
 command=prior['compile_commands'][0].copy();oldobj=command[command.index('-o')+1];obj=a.out/'entry.o';command[command.index('-c')+1]=str(source);command[command.index('-o')+1]=str(obj)
 if '-MF'in command:command[command.index('-MF')+1]=str(a.out/'entry.private.d')
 image=a.out/'qwen-native.pie.elf';link=[str(obj)if x==oldobj else x for x in prior['link_command']];link[link.index('-o')+1]=str(image)
 link=[('-Map='+str(a.out/'native-link.private.map'))if x.startswith('-Map=')else x for x in link]
 for i,cmd in enumerate((command,link)):
  r=subprocess.run(cmd,capture_output=True,timeout=600,env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp')))
  (a.out/f'{i}.private.log').write_bytes(r.stdout+r.stderr);require(r.returncode==0,r.stderr.decode(errors='replace')[-4500:]);print(json.dumps(dict(entry_continuation_step=i+1,total=2)),flush=True)
 for r in frozen:require(record(r['path'])==r,'Completed frozen source changed')
 r=copy.deepcopy(prior);entry=record(source);r.update(artifact=record(image),compile_commands=[command],link_command=link,source_parent=record(a.parent),
  inputs_before=frozen+[record(source),record(obj)],lossless_driver_table_geometry=audit_linked_storage(image,prior['lossless_driver_tables']))
 r['expert_q2_model']['actual_entry']=entry;r['all_Q2_IO_measurement']['entry']=entry
 r['routing_sharing']['actual_sources']['entry']=entry;r['routing_sharing']['commands'][0]=command
 r['lean_prefill']['actual_sources']['entry']=entry
 r['lean_prefill']['context_reuse_capacity_policy_corrected_from_4_to_16']=True
 target=a.out/'receipt.private.json';write_json(target,r)
 r['real_module_import_audit']=audit(a.workspace,a.cache,a.out);r['native_dispatch_audit']=dispatch(a.workspace,a.workspace/'driver-work/PS5-Vulkan-Inference-qwen-872cc126',image,a.out/'dispatch')
 require(not r['real_module_import_audit']['missing']and r['native_dispatch_audit']['passed'],'Actual imports/dispatch required');write_json(target,r)
 print('Corrected finite entry linked; completed cache/engine/graph/driver objects reused.',flush=True)
if __name__=='__main__':main()
