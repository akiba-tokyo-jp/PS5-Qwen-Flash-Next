#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Screen capacities only after reproducing actual 997-slot hit/miss counts."""
import argparse,json,os,subprocess,collections
from pathlib import Path
from expert_q4 import require,record,write_json
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('case','workspace','out'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    routes=[json.loads((a.case/f'native-arm{i}.routes.private.json').read_text())for i in (1,2)]
    require(all(r['complete']and r['sidecar_written_after_model_and_source_retirement']for r in routes),'Closed complete native routes required')
    reset=json.loads((a.case/'native-cache-reuse-1.private.json').read_text());require(reset['slots']==997,'Actual reset must bind the capacity; sidecar label is historical')
    host=a.workspace/'toolchain/msys-clang64/clang64/bin';exe=a.out/'route-replay.exe'
    cmd=[str(host/'clang++.exe'),'-std=c++17','-O2','-I',str(ROOT/'native/app'),str(ROOT/'tools/replay_completed_routes.cpp'),'-o',str(exe)]
    env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''))
    build=subprocess.run(cmd,capture_output=True,timeout=120,env=env);require(build.returncode==0,build.stderr.decode())
    text='2\n'
    for i,r in enumerate(routes):
        text+=f'{int(i==0)} {len(r["records"])}\n'
        for row in r['records']:text+=f'{row["layer"]} {len(row["ids"])} '+' '.join(map(str,row['ids']))+'\n'
    rows=[]
    for slots in (997,1125,1253):
        run=subprocess.run([str(exe)],input=(str(slots)+' '+text).encode(),capture_output=True,timeout=120,env=env)
        require(run.returncode==0,run.stderr.decode()[-800:]);counts=[list(map(int,line.split()))for line in run.stdout.decode().splitlines()]
        require(len(counts)==2,'Both independent and retained requests required')
        if slots==997:
            require(all(h==r['cache_hits']and m==r['cache_misses']for (_,h,m),r in zip(counts,routes)),'Replay did not reproduce actual selected cache policy')
        misses=[collections.Counter(),collections.Counter()]
        for line in run.stderr.decode().splitlines():i,layer,expert=map(int,line.split());misses[i][f'{layer}:{expert}']+=1
        rows.append(dict(slots=slots,additional_payload_bytes=(slots-997)*1536000,counts=counts,
            misses_by_layer_Expert=[dict(c.most_common())for c in misses]))
    write_json(a.out/'analysis.private.json',dict(completed=True,actual_997_hits_and_misses_reproduced=True,
        routing_frozen_screen_only=True,native_speedup_established=False,rows=rows,
        inputs=[record(a.case/f'native-arm{i}.routes.private.json')for i in (1,2)]+[record(ROOT/'native/app/expert_temporal_probation.h')]))
    print(json.dumps(dict(replay_verified=True,capacities=[dict(slots=r['slots'],counts=r['counts'])for r in rows])))
if __name__=='__main__':main()
