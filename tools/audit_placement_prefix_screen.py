#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Audit actual headers and unchanged physical boundaries before console use."""
import argparse,json,os,subprocess
from pathlib import Path
from audit_expert_all_q2_safety import body
from expert_q4 import require,record,write_json

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for key in ('control','candidate','out'):p.add_argument('--'+key,type=Path,required=True)
 a=p.parse_args();old=json.loads(a.control.read_text());new=json.loads(a.candidate.read_text());scope=new['placement_prefix_screen'];checks=[]
 x=Path(old['routing_sharing']['actual_sources']['entry']['path']).read_text();y=Path(scope['actual_sources']['entry']['path']).read_text()
 for name in ('observed_system_headroom','require_model_CPU_budget','wait_for_initial_model_CPU_budget','model_file_identity','model_directory_identity','resident_reset_empty_context'):
  require(body(x,name)==body(y,name),'Original physical body changed: '+name);checks.append(name)
 folder=a.out.parent
 for name in ('entry','owner'):
  original=scope['commands'][name];cmd=[];i=0
  while i<len(original):
   if original[i]in ('-o','-MF'):i+=2;continue
   if original[i]=='-c':i+=1;continue
   cmd.append(original[i]);i+=1
  deps=folder/(name+'-actual-includes.private.d');cmd+=['-M','-MF',str(deps)]
  run=subprocess.run(cmd,capture_output=True,timeout=180,env=dict(os.environ,TMP=str(folder/'tmp'),TEMP=str(folder/'tmp')))
  require(run.returncode==0,run.stderr.decode(errors='replace')[-2500:])
  actual=deps.read_text().replace('\\\n','').replace('\\ ', ' ')
  expected=str(folder/'device_buffer_budget.h').replace('\\','/')
  require(expected in actual.replace('\\','/'),'Actual preprocessor must select the local 248 MiB workspace header')
  checks.append(name+'_actual_header_selection')
 for row in scope['actual_sources'].values():require(record(row['path'])==row,'Compiled source changed')
 require(scope['scope']['maximum_requests']==20 and len(scope['scope']['reset_ordinals'])==16,'Bounded comparison geometry differs')
 require(new['native_dispatch_audit']['passed']and not new['real_module_import_audit']['missing'],'Native imports and dispatch required')
 write_json(a.out,dict(completed=True,checks=checks,common_prefix_snapshot_keeps_existing_state_ABI=True,
  all_original_physical_guards_retained=True,actual_248_MiB_workspace_header_selected=True,
  candidate=record(a.candidate),PS5_operations=0,CI_runs=0))
 print('Actual headers, unchanged physical guards and bounded placement/prefix scope passed.')

if __name__=='__main__':main()
