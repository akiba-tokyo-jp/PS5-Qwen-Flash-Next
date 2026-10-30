#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check that selected normal graph reuse retains original shape/input checks."""
import argparse,json
from pathlib import Path
from audit_expert_all_q2_safety import body
from expert_q4 import require,record,write_json

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for key in ('control','candidate','out'):p.add_argument('--'+key,type=Path,required=True)
 a=p.parse_args();old=json.loads(a.control.read_text());new=json.loads(a.candidate.read_text());proof=[]
 before=Path(old['routing_sharing']['actual_sources']['entry']['path']).read_text();after=Path(new['normal_performance']['actual_sources']['entry']['path']).read_text()
 for name in ('observed_system_headroom','require_model_CPU_budget','wait_for_initial_model_CPU_budget','model_file_identity','model_directory_identity','resident_reset_empty_context'):
  require(body(before,name)==body(after,name),'Original physical/owner body changed: '+name);proof.append(name)
 oldgraph=Path(old['routing_sharing']['actual_sources']['graph']['path']).read_text();newgraph=Path(new['normal_performance']['actual_sources']['graph']['path']).read_text()
 name='llm_graph_result::can_reuse';x=body(oldgraph,name);y=body(newgraph,name)
 y=y.replace('\n    if(!qwen_app_six_can_reuse(this))return false;','').replace('    if(res)qwen_app_six_reused();\n','')
 require(x==y,'Every original graph parameter/input/shape check must remain')
 routing=Path(new['normal_performance']['actual_sources']['routing']['path']).read_text()
 require('(six_mode<<5)|(qwen_app_route_mode()<<1)|unsigned(qwen_app_route_is_decode())'in routing,'Actual route and phase key required')
 for key in ('engine','cache','capture'):
  require(old['routing_sharing']['actual_sources'][key]==new['routing_sharing']['actual_sources'][key],'Qualified checkpoint/cache ABI changed')
 require(new['native_dispatch_audit']['passed']and not new['real_module_import_audit']['missing'],'Real imports/dispatch required')
 write_json(a.out,dict(completed=True,physical_guard_functions=proof,all_original_graph_shape_and_input_checks_retained=True,
  route_bits_and_phase_keyed=True,checkpoint_cache_and_capture_providers_unchanged=True,
  candidate=record(a.candidate),PS5_operations=0,CI_runs=0))
 print('Normal physical guards, original graph input/shape checks and checkpoint/cache providers passed.')

if __name__=='__main__':main()
