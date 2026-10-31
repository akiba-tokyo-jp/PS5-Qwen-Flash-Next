#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Rank a1024-triplet pack from actual Top-4 misses, retaining all348 old keys."""
import argparse,collections,json,os,subprocess
from pathlib import Path
from expert_q4 import require,record,write_json
from screen_expanded_miss_placement import keys
from screen_four_next_placement import CPP
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('parent','cache','workspace','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);r=json.loads(a.parent.read_text());src=Path(r['routing_sharing']['actual_sources']['cache']['path']);body=src.read_text();start=body.index('struct moe_cache_slru {');end=body.index('// gate, up, down or gate_up, down',start);(a.out/'actual-planner.private.h').write_text(body[start:end],newline='\n')
 inputs=[record(a.parent),record(src),record(__file__)];traces=[]
 for ordinal in (4,5,10,11,12,13):
  path=a.cache/f'hardware-first-generation-21300/native-arm{ordinal}.routes.private.json';t=json.loads(path.read_text());require(t['complete']and t['cache_slots']==3072,'Completed Top-4 route record required');traces.append(t);inputs.append(record(path))
 write_json(a.out/'traces.private.json',traces);cpp=a.out/'replay.private.cpp';cpp.write_text(CPP,newline='\n');exe=a.out/'replay.exe';host=a.workspace/'toolchain/msys-clang64/clang64/bin';up=a.cache/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569'
 for i,cmd in enumerate(([str(host/'clang++.exe'),'-std=c++17','-O2','-I'+str(a.out),'-I'+str(ROOT/'native/app'),'-I'+str(up/'vendor'),str(cpp),'-o',str(exe)],[str(exe),str(a.out/'traces.private.json'),str(a.out/'fills.private.json')])):
  run=subprocess.run(cmd,capture_output=True,timeout=180,env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH','')));(a.out/f'{i}.private.log').write_bytes(run.stdout+run.stderr);require(run.returncode==0,run.stderr.decode(errors='replace')[-2000:])
 rows=json.loads((a.out/'fills.private.json').read_text());base=json.loads((ROOT/'.local/q2-bundle-selection-9070/selection.private.json').read_text())['Experts'];extra=json.loads(Path(json.loads(Path(r['all_Q2_IO_normal']['extra_pack']['path']).read_text())['selection']['path']).read_text());extra=extra.get('Experts',extra.get('experts'))
 oc=r['all_Q2_optimized_monitor']['commands'][1];old=keys(Path(oc[oc.index('-c')+1]).parent/'limit-winner-bundle.private.h','Q2_current');existing={(int(x['layer']),int(x['expert']))for x in base+extra}|set(old);require(len(existing)==768 and len(old)==348,'Exact current placement required')
 counts=collections.Counter()
 for i,weight in ((0,1),(1,4)):
  for row in rows[i]['rows']:
   for e in row['fills']:
    key=(int(row['layer']),int(e))
    if key not in existing:counts[key]+=weight
 selected=old+[k for k,_ in sorted(counts.items(),key=lambda x:(-x[1],x[0]))[:676]];require(len(selected)==1024 and len(set(selected))==1024,'Exact1024 complete triplets required');new=set(selected)-set(old)
 coverage=[sum((int(row['layer']),int(e))in new for row in t['rows']for e in row['fills'])for t in rows]
 write_json(a.out/'selection.private.json',dict(completed=True,no_Experts_omitted=True,bundles=1024,Experts=[dict(layer=l,expert=e)for l,e in selected],old_keys_retained=348,new_keys=676))
 write_json(a.out/'complete.private.json',dict(completed=True,all_native_planner_hits_and_misses_exact=True,old_placement_keys=768,candidate_placement_keys=1444,pack_bytes=1024*1540096,covered_misses=coverage,fit_traces=[0,1],held_out_traces=[2,3,4,5],inputs=inputs,PS5_operations=0,native_speed_proven=False));print(json.dumps(dict(exact_native_planner=True,covered_misses=coverage,pack_bytes=1024*1540096)))
if __name__=='__main__':main()
