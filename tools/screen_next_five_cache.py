#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Replay actual planner traces with relaxed uniform layer floors."""
import argparse,json,os,subprocess
from pathlib import Path
from expert_q4 import require,record,write_json
from build_speculative_batch_probe import once
from screen_four_next_placement import CPP
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('screen','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    for name in ('traces.private.json','actual-planner.private.h'):(a.out/name).write_bytes((a.screen/name).read_bytes())
    body=(ROOT/'native/app/indexed_probation_policy.h').read_text();body=once(body,'const auto floor=(slots_-selected.size())/cached_layers_;','const auto floor=NEXT_FLOOR_DIVISOR?(slots_-selected.size())/(cached_layers_*NEXT_FLOOR_DIVISOR):0;')
    (a.out/'indexed_probation_policy.h').write_text(body,newline='\n');cpp=a.out/'screen.private.cpp';cpp.write_text(once(CPP,'if(hits!=t["cache_hits"]||misses!=t["cache_misses"])','if(NEXT_FLOOR_DIVISOR==1&&(hits!=t["cache_hits"]||misses!=t["cache_misses"]))'),newline='\n')
    host=a.workspace/'toolchain/msys-clang64/clang64/bin';up=a.cache/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569';results=[]
    for divisor in (1,2,0):
        exe=a.out/f'floor-{divisor}.exe';out=a.out/f'floor-{divisor}.private.json';cmd=[str(host/'clang++.exe'),'-std=c++17','-O2','-DNEXT_FLOOR_DIVISOR='+str(divisor),'-I'+str(a.out),'-I'+str(ROOT/'native/app'),'-I'+str(up/'vendor'),str(cpp),'-o',str(exe)]
        for i,command in enumerate((cmd,[str(exe),str(a.out/'traces.private.json'),str(out)])):
            run=subprocess.run(command,capture_output=True,timeout=180,env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH','')));(a.out/f'floor-{divisor}-{i}.private.log').write_bytes(run.stdout+run.stderr);require(run.returncode==0,run.stderr.decode(errors='replace')[-2000:])
        rows=json.loads(out.read_text());results.append(dict(divisor=divisor,misses=[r['misses']for r in rows],hits=[r['hits']for r in rows],control_native_exact=divisor==1))
    base=results[0]['misses']
    for row in results:row['miss_reduction']=[x-y for x,y in zip(base,row['misses'])]
    write_json(a.out/'complete.private.json',dict(completed=True,actual_baseline_native_counts_reproduced=True,results=results,host_trace_only=True,native_speed_proven=False,inputs=[record(__file__),record(a.screen/'traces.private.json'),record(a.screen/'actual-planner.private.h')],PS5_operations=0));print(json.dumps(results))
if __name__=='__main__':main()
