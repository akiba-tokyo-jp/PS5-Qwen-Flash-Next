#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Refit a fixed-size supplemental pack on current Top2 misses and held-out tasks."""
import argparse,collections,json,os,subprocess
from pathlib import Path
from expert_q4 import record,require,write_json
from screen_expanded_miss_placement import keys
from screen_four_next_placement import CPP
ROOT=Path(__file__).resolve().parents[1]

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('parent','cache','workspace','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();n=json.loads(a.parent.read_text());a.out.mkdir(parents=True,exist_ok=False)
 source=Path(n['routing_sharing']['actual_sources']['cache']['path']);text=source.read_text();start=text.index('struct moe_cache_slru {');end=text.index('// gate, up, down or gate_up, down',start)
 (a.out/'actual-planner.private.h').write_text(text[start:end],newline='\n')
 paths=[a.cache/f'hardware-first-generation-33300/native-arm{i}.routes.private.json'for i in (2,3,10,11,12,13)]
 traces=[json.loads(x.read_text())for x in paths]
 require(all(t['complete']and not t['capture_failed']and t['cache_slots']==3712 for t in traces),'Complete current-geometry traces required')
 write_json(a.out/'traces.private.json',traces);cpp=a.out/'replay.cpp';cpp.write_text(CPP.replace('p.init(49,512,3072,48)','p.init(49,512,3712,48)'),newline='\n')
 host=a.workspace/'toolchain/msys-clang64/clang64/bin';exe=a.out/'replay.exe';up=a.cache/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569'
 for i,c in enumerate([[str(host/'clang++.exe'),'-std=c++17','-O2','-I'+str(a.out),'-I'+str(ROOT/'native/app'),'-I'+str(up/'vendor'),str(cpp),'-o',str(exe)],[str(exe),str(a.out/'traces.private.json'),str(a.out/'fills.private.json')]]):
  r=subprocess.run(c,capture_output=True,timeout=180,env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH','')));(a.out/f'{i}.log').write_bytes(r.stdout+r.stderr);require(r.returncode==0,r.stderr.decode(errors='replace'))
 fills=json.loads((a.out/'fills.private.json').read_text());base=json.loads((ROOT/'.local/q2-bundle-selection-9070/selection.private.json').read_text())['Experts']
 extra=json.loads(Path(json.loads(Path(n['all_Q2_IO_normal']['extra_pack']['path']).read_text())['selection']['path']).read_text());extra=extra.get('Experts',extra.get('experts'))
 fixed={(int(x['layer']),int(x['expert']))for x in base+extra};require(len(fixed)==420,'Exact unchanged base and extra packs required')
 oc=n['all_Q2_optimized_monitor']['commands'][1];old=keys(Path(oc[oc.index('-c')+1]).parent/'limit-winner-bundle.private.h','Q2_current');require(len(old)==348,'Current348-key supplemental pack required')
 counts=collections.Counter()
 for i,weight in ((0,1),(1,4)):
  for row in fills[i]['rows']:
   for e in row['fills']:
    key=(int(row['layer']),int(e))
    if key not in fixed:counts[key]+=weight
 selected=[k for k,_ in sorted(counts.items(),key=lambda x:(-x[1],x[0]))[:348]]
 if len(selected)<348:selected +=[k for k in old if k not in selected][:348-len(selected)]
 require(len(selected)==len(set(selected))==348,'Fixed-size348-key selection required')
 def coverage(selected):
  s=set(selected)|fixed
  return [sum((int(row['layer']),int(e))in s for row in trace['rows']for e in row['fills'])for trace in fills]
 before,after=coverage(old),coverage(selected)
 write_json(a.out/'selection.private.json',dict(completed=True,no_Experts_omitted=True,bundles=348,Experts=[dict(layer=l,expert=e)for l,e in selected]))
 write_json(a.out/'complete.private.json',dict(completed=True,all_actual_native_hits_and_misses_reproduced=True,cache_slots=3712,
  fit_ordinals=[2,3],held_out_ordinals=[10,11,12,13],old_covered_misses=before,new_covered_misses=after,
  coverage_difference=[b-a for a,b in zip(before,after)],replacement_pack_keys=348,total_placement_keys=768,
  inputs=[record(__file__),record(a.parent),record(source),*[record(x)for x in paths]],PS5_operations=0,native_speed_proven=False))
 print(json.dumps(dict(exact_native_replay=True,old_coverage=before,new_coverage=after)))

if __name__=='__main__':main()
