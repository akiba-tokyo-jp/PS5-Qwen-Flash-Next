#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Price and screen cache capacities beyond the current software quotas."""
import argparse,json,os,subprocess
from pathlib import Path
from expert_q4 import record,require,write_json

ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('planner','traces','compiler','json_include','preflight','out'):
        p.add_argument('--'+key.replace('_','-'),type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    before=json.loads(a.preflight.read_text());base=3072;stride=537600;triplet=1536000
    slack=before['driver_free_bytes']-before['planned_resident_headroom_bytes']
    bounds=dict(current_slots=base,software_single_buffer_cap=before['maximum_postload_device_buffer_bytes'],
        reported_buffer_batch_limit=before['device_buffer_batch_limit_bytes'],
        single_buffer_software_max_slots=before['maximum_postload_device_buffer_bytes']//stride-1,
        batch_limit_geometry_max_slots=before['device_buffer_batch_limit_bytes']//stride-1,
        unchanged_preflight_envelope_max_slots=base+slack//triplet,
        unchanged_weight_saving_and_24MiB_allowance_max_slots=1381+(3163852800-(24<<20)-1)//triplet,
        preflight_slack_bytes=slack,not_a_native_capacity_qualification=True)
    capacities=sorted({base,3328,bounds['unchanged_weight_saving_and_24MiB_allowance_max_slots'],
                       3584,bounds['unchanged_preflight_envelope_max_slots'],bounds['batch_limit_geometry_max_slots']})
    require(capacities==[3072,3328,3424,3584,3665,3993],'Bounded expected geometry and captured preflight required')
    screen=ROOT/'tools/screen_adaptive_prefill.cpp';inputs=[record(x)for x in (Path(__file__),screen,a.planner,a.traces,a.preflight)]
    env=dict(os.environ,PATH=str(a.compiler.parent)+os.pathsep+os.environ.get('PATH',''))
    rows=[];commands=[]
    for slots in capacities:
        out=a.out/str(slots);out.mkdir();(out/'screen-cache.private.h').write_bytes(a.planner.read_bytes())
        code=screen.read_text().replace('for(unsigned mode=0;mode<7;++mode)','for(unsigned mode:{0u,1u})')
        require(code.count('49,512,3072,48')==2 and code.count('p,48,3072')==1,'Exact selected planner screen required')
        code=code.replace('49,512,3072,48',f'49,512,{slots},48').replace('p,48,3072',f'p,48,{slots}')
        if slots!=base:code=code.replace('if(mode==cohort.at("native_mode")&&','if(false&&mode==cohort.at("native_mode")&&')
        source=out/'screen.private.cpp';source.write_text(code,newline='\n');exe=out/'screen.exe'
        recipes=[[str(a.compiler),'-std=c++17','-O2','-I'+str(out),'-I'+str(ROOT/'native/app'),
                  '-I'+str(a.json_include),str(source),'-o',str(exe)],
                 [str(exe),str(a.traces),str(out/'result.private.json')]]
        for i,command in enumerate(recipes):
            r=subprocess.run(command,capture_output=True,timeout=240,env=env)
            (out/f'{i}.private.log').write_bytes(r.stdout+r.stderr)
            require(r.returncode==0,(r.stdout+r.stderr).decode(errors='replace')[-1800:])
        results=json.loads((out/'result.private.json').read_text())
        rows.extend(dict(slots=slots,cohort=x['cohort'],mode=x['mode'],misses=x['total_misses'])for x in results)
        commands.extend(recipes)
    for r in inputs:require(record(r['path'])==r,'Cache-limit input changed')
    write_json(a.out/'complete.private.json',dict(completed=True,bounds=bounds,rows=rows,
        original_planner_and_accepted_history=True,current_native_controls_exact=True,
        ownership_maps_validated=True,host_trace_screen_not_native_speed=True,
        inputs=inputs,commands=commands,PS5_operations=0,CI_runs=0))
    print(json.dumps(dict(bounds=bounds,rows=rows)))
if __name__=='__main__':main()
