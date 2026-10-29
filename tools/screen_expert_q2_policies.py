#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Finite actual-route Q2 policy screen; never launches console or model work."""
import argparse,json,os,subprocess
from pathlib import Path
from expert_q4 import require,record
ROOT=Path(__file__).resolve().parents[1]

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for key in ('cache','workspace','out'):p.add_argument('--'+key,type=Path,required=True)
 a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 receipt=json.loads((a.cache/'build/Expert-all-Q2-IO-8872/receipt.private.json').read_text())
 cache=receipt['expert_q2_model']['actual_cache'];require(record(Path(cache['path']))==cache,'Actual closed all-Q2 cache source changed')
 source=Path(cache['path']).read_text();start=source.index('struct moe_cache_slru {');end=source.index('// gate, up, down or gate_up, down',start)
 plan=source[start:end];require(plan.count('qwen_app::ExpertPolicy')==1,'One actual policy member required')
 (a.out/'q2-control-plan.h').write_text(plan)
 (a.out/'q2-candidate-plan.h').write_text(plan.replace('qwen_app::ExpertPolicy','qwen_app::Q2ScreenPolicy'))
 (a.out/'q2-implementation-plan.h').write_text(plan.replace('qwen_app::ExpertPolicy','qwen_app::QualifiedProbationPolicy'))
 inputs=[];frozen=[Path(cache['path']),ROOT/'native/app/expert_policy.h',ROOT/'native/app/expert_q2_policy_screen.h',ROOT/'tests/expert_q2_policy_screen.cpp',Path(__file__)]
 for case in (8780,8700):
  root=a.cache/f'hardware-first-generation-{case}';terminal=json.loads((root/'native-model-terminal.private.json').read_text());close=json.loads((root/'restored-complete.private.json').read_text())
  require(terminal['completed']and terminal['all_model_source_device_owners_positively_retired']and close['completed']and not close['unknown_completion'],'Closed native source evidence required')
  for request in terminal['requests']:
   path=root/f"native-arm{request['ordinal']}.routes.private.json";trace=json.loads(path.read_text())
   require(trace['complete']and trace['sidecar_written_after_model_and_source_retirement']and trace['cache_reset_before_request']and trace['cache_slots']==867 and trace['pid']==terminal['pid']and trace['run_id']==terminal['run_id'],'Exact cold 867-slot native trace required')
   trace['case']=case;inputs.append(trace);frozen.append(path)
  frozen.extend((root/'native-model-terminal.private.json',root/'restored-complete.private.json'))
 captured=[record(x)for x in frozen];data=a.out/'inputs.private.json';data.write_text(json.dumps(inputs,separators=(',',':'))+'\n')
 host=a.workspace/'toolchain/msys-clang64/clang64/bin';up=a.cache/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569'
 exe=a.out/'policy-screen.exe';raw=a.out/'raw.private.json'
 commands=[[str(host/'clang++.exe'),'-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'native/app'),'-I',str(a.out),'-I',str(up/'vendor'),str(ROOT/'tests/expert_q2_policy_screen.cpp'),'-o',str(exe)],[str(exe),str(data),str(raw)]]
 env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''))
 for i,command in enumerate(commands):
  run=subprocess.run(command,capture_output=True,timeout=180,env=env);(a.out/f'{i}.private.log').write_bytes(run.stdout+run.stderr)
  require(run.returncode==0,run.stderr.decode(errors='replace')[-2000:])
 policies=json.loads(raw.read_text());baseline=policies[0]['requests'];rows=[]
 for policy in policies:
  requests=policy['requests'];train=[i for i,r in enumerate(requests)if r['case']==8780];held=[i for i,r in enumerate(requests)if r['case']==8700]
  result=dict(mode=policy['mode'],requests=[{k:v for k,v in r.items()if k!='fill_records'}for r in requests])
  for label,indices in [('counting',train),('held_out_quality',held)]:
   old=sum(baseline[i]['misses']for i in indices);new=sum(requests[i]['misses']for i in indices)
   result[label]=dict(baseline_misses=old,candidate_misses=new,reduction_fraction=1-new/old,every_request_fewer_misses=all(requests[i]['misses']<baseline[i]['misses']for i in indices))
  result['eligible_for_native_speed_comparison']=policy['mode']!='control'and all(result[k]['every_request_fewer_misses']for k in ('counting','held_out_quality'))
  rows.append(result)
 require(captured==[record(x)for x in frozen],'Source evidence changed')
 report=dict(schema='ps5-qwen-Q2-policy-screen-v1',completed=True,active_slots=867,Expert_triplet_bytes=1536000,actual_planner_control_and_fill_order_exact=True,native_counters_exact=True,all_active_top10_retained=True,future_routes_used_by_candidates=False,policies=rows,PS5_operations=0,CI_runs=0,production_changed=False,native_speed_qualified=False,inputs=captured,commands=commands)
 (a.out/'receipt.private.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({k:v for k,v in report.items()if k not in ('inputs','commands','policies')},indent=2))
 for r in rows:print(json.dumps({k:v for k,v in r.items()if k!='requests'}))
if __name__=='__main__':main()
