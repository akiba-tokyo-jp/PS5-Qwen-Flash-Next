#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reproduce1253 native misses before screening new frequency retention scores."""
import argparse,collections,json,os,subprocess
from pathlib import Path
from expert_q4 import require,record,write_json
from build_speculative_batch_probe import once
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('case','workspace','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    traces=[json.loads((a.case/f'native-arm{i}.routes.private.json').read_text())for i in (1,2)]
    reset=json.loads((a.case/'native-cache-reuse-1.private.json').read_text());slots=reset['slots'];require(slots==1253 and all(r['complete']for r in traces),'Completed actual1253 scope required')
    text=f'{slots} 2\n'
    for i,r in enumerate(traces):
        text+=f'{int(i==0)} {len(r["records"])}\n'
        for row in r['records']:text+=f'{row["layer"]} {len(row["ids"])} '+' '.join(map(str,row['ids']))+'\n'
    original=(ROOT/'native/app/expert_temporal_probation.h').read_text();marker='return counts_[key]>=2&&(!temporal_probation_window||tick_-recency_[key]<=temporal_probation_window);'
    host=a.workspace/'toolchain/msys-clang64/clang64/bin';env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''));rows=[]
    for label,expression in (('qualified',None),('frequency_cap4','return std::min<std::uint32_t>(counts_[key],4);'),('frequency','return counts_[key];')):
        folder=a.out/label;folder.mkdir();header=folder/'expert_temporal_probation.h';header.write_text(once(original,marker,expression)if expression else original,newline='\n')
        exe=folder/'replay.exe';cmd=[str(host/'clang++.exe'),'-std=c++17','-O2','-I',str(folder),'-I',str(ROOT/'native/app'),str(ROOT/'tools/replay_completed_routes.cpp'),'-o',str(exe)]
        build=subprocess.run(cmd,capture_output=True,timeout=120,env=env);require(build.returncode==0,build.stderr.decode()[-1200:])
        run=subprocess.run([str(exe)],input=text.encode(),capture_output=True,timeout=120,env=env);require(run.returncode==0,run.stderr.decode()[-1200:]);counts=[list(map(int,line.split()))for line in run.stdout.decode().splitlines()]
        if expression is None:require(all(h==t['cache_hits']and m==t['cache_misses']for (_,h,m),t in zip(counts,traces)),'Actual1253 native counts were not reproduced')
        misses=[collections.Counter(),collections.Counter()]
        for line in run.stderr.decode().splitlines():i,layer,expert=map(int,line.split());misses[i][f'{layer}:{expert}']+=1
        rows.append(dict(mode=label,slots=slots,counts=counts,policy_header=record(header),misses_by_layer_Expert=[dict(m.most_common())for m in misses]))
    write_json(a.out/'analysis.private.json',dict(completed=True,actual_1253_counts_reproduced=True,routing_frozen_screen_only=True,native_speedup_claimed=False,rows=rows,
        inputs=[record(a.case/f'native-arm{i}.routes.private.json')for i in (1,2)]+[record(ROOT/'native/app/expert_temporal_probation.h'),record(ROOT/'tools/replay_completed_routes.cpp')]))
    print(json.dumps(dict(actual_1253_counts_reproduced=True,modes=[dict(mode=r['mode'],counts=r['counts'])for r in rows])))
if __name__=='__main__':main()
