#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Relink the qualified passive monitor on the explicit all-Expert Q2 parent."""
import json,sys
from pathlib import Path
from types import FunctionType
import build_expert_q2_monitor as qualified
from expert_all_q2_monitor_source import monitor_entry_source,MONITOR_SCOPE
from expert_q4 import record,require,write_json
ROOT=Path(__file__).resolve().parents[1]
def main():
 require('--parent'in sys.argv and '--out'in sys.argv,'Explicit parent and output required')
 parent=Path(sys.argv[sys.argv.index('--parent')+1]);out=Path(sys.argv[sys.argv.index('--out')+1]);prior=json.loads(parent.read_text());scope=prior['expert_q2_model']
 require(scope['scope']['Expert_format']=='Gate_Up_Q2_K_Down_Q2_0_MSE'and scope['Down_encoding']=='signed_FP16_scale_MSE_fit'and scope['active_cache_slots']==867 and scope['complete_prefix_metadata'],'Exact all-Expert Q2 parent required')
 captured=[record(ROOT/'tools/build_expert_q2_monitor.py'),record(ROOT/'tools/expert_all_q2_monitor_source.py')]
 def exact_require(value,message):
  if message=='Complete-prefix mixed parent required':require(scope['complete_prefix_metadata']and scope['scope']['Expert_format']=='Gate_Up_Q2_K_Down_Q2_0_MSE','Complete-prefix all-Expert Q2 parent required')
  else:require(value,message)
 env=dict(qualified.main.__globals__,__file__=__file__,require=exact_require,monitor_entry_source=monitor_entry_source,MONITOR_SCOPE=MONITOR_SCOPE)
 FunctionType(qualified.main.__code__,env)()
 for r in captured:require(record(r['path'])==r,'Qualified bounded monitor implementation changed')
 path=out/'receipt.private.json';result=json.loads(path.read_text());result['inputs_before']+=captured;result['expert_q2_model']['normal_application_validation_pending']=True;write_json(path,result)
if __name__=='__main__':main()
