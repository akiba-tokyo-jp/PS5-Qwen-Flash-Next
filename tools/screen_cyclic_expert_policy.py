#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Finite original-route screen of same-capacity causal cyclic eviction ideas."""
import argparse,json,os,subprocess
from pathlib import Path
from check_model_checkpoint import record
from check_cache_capacity import bound
from expert_route_result import validate_routes
from replay_expert_routes import RouteCache
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in('workspace','cache','manifest','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();manifest=json.loads(a.manifest.read_text())
    if manifest.get('schema')!='ps5-qwen-capacity-replay-inputs-v1'or len(manifest.get('requests',[]))!=3:raise ValueError('Three frozen original requests required')
    rows=[];files=[Path(__file__),a.manifest,ROOT/'native/app/cyclic_expert_policy.h',ROOT/'native/app/expert_policy.h',ROOT/'tests/cyclic_expert_policy.cpp',ROOT/'tools/replay_expert_routes.py']
    for i,row in enumerate(manifest['requests']):
        rp=bound(row['routes']);tp=bound(row['result']);files.extend((rp,tp))
        if rp.stat().st_size>2<<20 or tp.stat().st_size>2<<20:raise ValueError('Bounded completed metadata required')
        trace=json.loads(rp.read_text());terminal=json.loads(tp.read_text())
        validate_routes(trace,terminal,width=4,pid=terminal['pid'],run_id=terminal['run_id'],cold=i<2);rows.append(trace)
    a.out.mkdir(parents=True,exist_ok=False);data=a.out/'records.private.json';data.write_text(json.dumps(rows,separators=(',',':'))+'\n');files.append(data)
    inputs=[record(f)for f in files];host=a.workspace/'toolchain/msys-clang64/clang64/bin';up=a.cache/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569';exe=a.out/'cyclic-policy.exe'
    commands=[[str(host/'clang++.exe'),'-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'native/app'),'-I',str(up/'vendor'),
        str(ROOT/'tests/cyclic_expert_policy.cpp'),'-o',str(exe)],[str(exe),str(data)]]
    env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''))
    for i,c in enumerate(commands):
        r=subprocess.run(c,capture_output=True,timeout=120,env=env);(a.out/f'{i}.private.log').write_bytes(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace')[-1600:])
    actual=json.loads(r.stdout);names=['lfu','layer_distance','frequency_over_distance']
    for item in actual:
        mode=names[item['mode']];totals=[]
        for i,trace in enumerate(rows):
            if i<2:cache=RouteCache(eviction_mode=mode)
            total=dict(hits=0,misses=0,unique=0)
            for row in trace['records']:
                step=cache.step(row)
                for k in total:total[k]+=step[k]
            totals.append(total)
        if totals!=item['requests']:raise ValueError('Independent Python/native policy differs: '+mode)
        item['mode']=mode
    for predicted,native in zip(actual[0]['requests'],rows):
        if predicted!=dict(hits=native['cache_hits'],misses=native['cache_misses'],unique=native['unique_selected_experts']):raise ValueError('Control differs from native counters')
    baseline=sum(x['misses']for x in actual[0]['requests'][1:])
    for item in actual:
        misses=sum(x['misses']for x in item['requests'][1:]);item.update(external_uploaded_bytes=misses*9830400,
            external_byte_reduction_fraction=1-misses/baseline,both_external_requests_fewer_misses=all(item['requests'][i]['misses']<actual[0]['requests'][i]['misses']for i in(1,2)))
    assert inputs==[record(f)for f in files]
    result=dict(schema='ps5-qwen-cyclic-policy-screen-v1',policies=actual,original_53_slots_and_banks_unchanged=True,
        actual_aged_frequency_observer_used=True,independent_Cpp_Python_match=True,control_native_counters_exact=True,
        future_expert_IDs_used=False,additional_prediction_reads=0,extra_recency_metadata_bytes=49*512*8,
        no_policy_integrated_or_adopted=True,native_speed_qualified=False,PS5_operations=0,CI_runs=0)
    (a.out/'receipt.private.json').write_text(json.dumps(dict(result,inputs=inputs,commands=commands),indent=2)+'\n');print(json.dumps(result),flush=True)
if __name__=='__main__':main()
