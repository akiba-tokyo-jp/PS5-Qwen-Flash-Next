#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Screen smaller accepted-decode histories against the same frozen planner."""
import argparse,json,os,subprocess
from pathlib import Path
from expert_q4 import record,require,write_json

ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('planner','traces','compiler','json_include','out'):
        p.add_argument('--'+key.replace('_','-'),type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    screen=ROOT/'tools/screen_adaptive_prefill.cpp'
    adaptive=ROOT/'native/app/adaptive_prefill_protection.h'
    history=ROOT/'native/app/decode_prefill_protection.h'
    inputs=[record(x)for x in (Path(__file__),screen,adaptive,history,a.planner,a.traces)]
    env=dict(os.environ,PATH=str(a.compiler.parent)+os.pathsep+os.environ.get('PATH',''))
    rows=[];commands=[]
    for capacity in (512,1024):
        out=a.out/str(capacity);out.mkdir()
        original=history.read_text()
        require(original.count('1536')==3,'Exact accepted-history capacity implementation required')
        (out/'capacity_decode.private.h').write_text(original.replace('1536',str(capacity)).replace(
            'DecodePrefillProtection','ScreenDecodePrefillProtection'),newline='\n')
        text=adaptive.read_text().replace('#include "decode_prefill_protection.h"',
            '#include "capacity_decode.private.h"').replace('DecodePrefillProtection','ScreenDecodePrefillProtection')
        (out/'capacity_adaptive.private.h').write_text(text,newline='\n')
        (out/'screen-cache.private.h').write_bytes(a.planner.read_bytes())
        code=screen.read_text().replace('#include "adaptive_prefill_protection.h"',
            '#include "capacity_adaptive.private.h"')
        before='if(mode==cohort.at("native_mode")&&'
        require(code.count(before)==1,'Exact native counter validation boundary required')
        # Cap1536 controls were already validated. Smaller histories must still
        # reproduce the native unprotected control; no fixed1536 equivalence is claimed.
        code=code.replace(before,'if(mode==0&&mode==cohort.at("native_mode")&&')
        source=out/'screen.private.cpp';source.write_text(code,newline='\n');exe=out/'screen.exe'
        recipes=[[str(a.compiler),'-std=c++17','-O2','-I'+str(out),'-I'+str(ROOT/'native/app'),
                  '-I'+str(a.json_include),str(source),'-o',str(exe)],
                 [str(exe),str(a.traces),str(out/'result.private.json')]]
        for i,command in enumerate(recipes):
            result=subprocess.run(command,capture_output=True,env=env,timeout=240)
            (out/f'{i}.private.log').write_bytes(result.stdout+result.stderr)
            require(result.returncode==0,(result.stdout+result.stderr).decode(errors='replace')[-2200:])
        data=json.loads((out/'result.private.json').read_text())
        rows.extend(dict(capacity=capacity,cohort=r['cohort'],mode=r['mode'],total_misses=r['total_misses'])for r in data)
        commands.extend(recipes)
    for row in inputs:require(record(row['path'])==row,'Capacity screen input changed')
    write_json(a.out/'complete.private.json',dict(completed=True,capacities=[512,1024],results=rows,
        original_planner_unchanged=True,accepted_only_history_semantics_preserved=True,
        runtime_source_default_unchanged=True,native_unprotected_control_exact=True,
        host_trace_screen_not_native_speed=True,inputs=inputs,commands=commands,PS5_operations=0,CI_runs=0))
    print(json.dumps(rows))

if __name__=='__main__':main()
