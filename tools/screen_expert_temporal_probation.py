#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Screen bounded causal protection on the exact already captured native routes."""
import argparse,json,os,subprocess,collections
from pathlib import Path
from expert_q4 import require,record,write_json
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for key in ('cache','workspace','out'):p.add_argument('--'+key,type=Path,required=True)
 a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 inputs=ROOT/'.local/q2-policy-screen-8891/inputs.private.json';prior=ROOT/'.local/q2-policy-screen-8891/raw.private.json'
 require(inputs.is_file()and prior.is_file(),'Closed source traces required')
 receipt=json.loads((a.cache/'build/Expert-all-Q2-IO-8872/receipt.private.json').read_text());row=receipt['expert_q2_model']['actual_cache'];require(record(row['path'])==row,'Actual planner changed')
 text=Path(row['path']).read_text();start=text.index('struct moe_cache_slru {');end=text.index('// gate, up, down or gate_up, down',start)
 (a.out/'q2-temporal-plan.h').write_text(text[start:end].replace('qwen_app::ExpertPolicy','qwen_app::TemporalProbationPolicy'),newline='\n')
 source=(ROOT/'tests/expert_q2_policy_screen.cpp').read_text().split('int main(int argc,char**argv)')[0]
 source=source.replace('#include "expert_q2_policy_screen.h"','#include "expert_q2_policy_screen.h"\n#include "expert_temporal_probation.h"')
 source+='''namespace temporal {
#include "q2-temporal-plan.h"
}
int main(int argc,char**argv){try{if(argc!=3)throw std::runtime_error("Two paths required");std::ifstream f(argv[1]);Json traces;f>>traces;Json result=Json::array();
for(unsigned window:{0,48,72,96,144,192,288,384,576,768}){qwen_app::temporal_probation_window=window;Json rows=Json::array();
for(const auto&t:traces){auto r=replay<temporal::moe_cache_slru>(t,true);r["case"]=t["case"];r["ordinal"]=t["ordinal"];rows.push_back(r);}result.push_back({{"window",window},{"requests",rows}});}
std::ofstream out(argv[2]);out<<result.dump()<<'\\n';}catch(const std::exception&e){std::cerr<<e.what();return 1;}}
'''
 cpp=a.out/'screen.private.cpp';cpp.write_text(source,newline='\n');raw=a.out/'raw.private.json';host=a.workspace/'toolchain/msys-clang64/clang64/bin'
 command=[str(host/'clang++.exe'),'-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'native/app'),'-I',str(a.out),'-I',str(ROOT/'.local/q2-policy-screen-8891'),'-I',str(a.cache/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569/vendor'),str(cpp),'-o',str(a.out/'screen.exe')]
 for i,cmd in enumerate([command,[str(a.out/'screen.exe'),str(inputs),str(raw)]]):
  run=subprocess.run(cmd,capture_output=True,timeout=300,env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH','')));(a.out/f'{i}.private.log').write_bytes(run.stdout+run.stderr);require(run.returncode==0,run.stderr.decode(errors='replace')[-2500:])
 values=json.loads(raw.read_text());old=next(x for x in json.loads(prior.read_text())if x['mode']=='two_touch_probation')
 for x,y in zip(values[0]['requests'],old['requests']):
  require(all(x[k]==y[k]for k in ('hits','misses','unique','Expert_uploaded_bytes')),'Zero-window selected probation must be exact')
 summary=[]
 for v in values:
  r=dict(window=v['window'])
  for label,case in [('counting',8780),('heldout',8700)]:
   rows=[x for x in v['requests']if x['case']==case];baseline=[x for x in values[0]['requests']if x['case']==case]
   r[label]=dict(misses=sum(x['misses']for x in rows),baseline_misses=sum(x['misses']for x in baseline),every_request_no_more_misses=all(x['misses']<=y['misses']for x,y in zip(rows,baseline)))
  summary.append(r)
 # Rank on the counting traces; disclose held-out changes without filtering them away.
 winner=min(summary[1:],key=lambda x:x['counting']['misses'])
 write_json(a.out/'receipt.private.json',dict(completed=True,zero_window_control_exact=True,selected_window=winner['window'],results=summary,inputs=[record(x)for x in (inputs,prior,Path(__file__),ROOT/'native/app/expert_temporal_probation.h',Path(row['path']))],PS5_operations=0,CI_runs=0))
 baseline=values[0]['requests'];existing=json.loads((ROOT/'.local/q2-bundle-selection-9070/selection.private.json').read_text());retained={(x['layer'],x['expert'])for x in existing['Experts']}
 counts=collections.Counter()
 for request in baseline:
  if request['case']!=8780:continue
  for route in request['fill_records']:
   for expert,slot in route['fills']:
    if (route['layer'],expert)not in retained:counts[(route['layer'],expert)]+=1
 chosen=sorted(key for key,value in counts.most_common(84))
 write_json(a.out/'additional-bundles.private.json',dict(completed=True,no_Experts_omitted=True,bundles=84,Experts=[dict(layer=l,expert=e)for l,e in chosen],original_pack_untouched=True,selection_uses_counting_routes_only=True,physical_bytes=84*1540096))
 print(json.dumps(dict(selected_window=winner['window'],results=summary,additional_bundles=84,additional_bytes=84*1540096),indent=2))
if __name__=='__main__':main()
