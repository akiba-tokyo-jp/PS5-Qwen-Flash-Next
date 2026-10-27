#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compare a geometry-priced 54-slot hypothesis with actual 53-slot routing."""
import argparse,json,os,subprocess
from pathlib import Path
from check_model_checkpoint import record
from expert_route_result import validate_routes
from replay_expert_routes import RouteCache
ROOT=Path(__file__).resolve().parents[1]

def bound(row):
    p=Path(row['path']);
    if record(p)!=row:raise ValueError('Capacity evidence changed')
    return p

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in('workspace','cache','manifest','geometry-receipt','out'):p.add_argument('--'+n,type=Path,required=True)
    scope=p.add_mutually_exclusive_group()
    scope.add_argument('--research-capacity-sweep',action='store_true',help='Replay larger unqualified allocations; never alter a native capacity')
    scope.add_argument('--large-capacity-sweep',action='store_true',help='Metadata-only 53 to 1024 slots; no change to application memory caps')
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);manifest=json.loads(a.manifest.read_text())
    if manifest.get('schema')!='ps5-qwen-capacity-replay-inputs-v1'or len(manifest.get('requests',[]))!=3:raise ValueError('Three bound completed requests required')
    geometry=json.loads(a.geometry_receipt.read_text())
    if geometry.get('native_54_slot_quality_qualified')is not False or geometry.get('controls',{}).get('hypothetical_slots')!=54:raise ValueError('Exact unqualified byte-storage geometry receipt required')
    for row in geometry['inputs']:bound(row)
    records=[];files=[Path(__file__),a.manifest,a.geometry_receipt,ROOT/'tests/cache_capacity_replay.cpp',ROOT/'native/app/expert_policy.h',ROOT/'tools/replay_expert_routes.py']
    for index,row in enumerate(manifest['requests']):
        routes_path=bound(row['routes']);result_path=bound(row['result']);files.extend((routes_path,result_path))
        if routes_path.stat().st_size>2<<20 or result_path.stat().st_size>2<<20:raise ValueError('Completed metadata exceeds its bound')
        routes=json.loads(routes_path.read_text());result=json.loads(result_path.read_text())
        validate_routes(routes,result,width=4,pid=result['pid'],run_id=result['run_id'],cold=index<2);records.append(routes)
    inputs=a.out/'records.private.json';inputs.write_text(json.dumps(records,separators=(',',':'))+'\n');files.append(inputs)
    host=a.workspace/'toolchain/msys-clang64/clang64/bin';up=a.cache/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569';exe=a.out/'capacity-replay.exe'
    command=[str(host/'clang++.exe'),'-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'native/app'),'-I',str(up/'vendor'),str(ROOT/'tests/cache_capacity_replay.cpp'),'-o',str(exe)]
    fixed=[record(f)for f in files];env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''))
    execute=[str(exe),str(inputs)]+(['--large-capacity-sweep']if a.large_capacity_sweep else(['--research-capacity-sweep']if a.research_capacity_sweep else[]))
    for i,c in enumerate((command,execute)):
        r=subprocess.run(c,capture_output=True,env=env,timeout=120);(a.out/(str(i)+'.private.log')).write_bytes(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError('Capacity policy '+str(i)+': '+r.stderr.decode(errors='replace')[-3000:])
    actual=json.loads(r.stdout)
    for item in actual:
        totals=[];partitions=[];cache=None
        for index,rows in enumerate(records):
            if index<2:
                cache=RouteCache(slots=item['slots'],research_max_slots=1024 if a.large_capacity_sweep else 160)
            total=dict(hits=0,misses=0,unique=0)
            partition=dict(one_token_uploaded_bytes=0,multi_token_uploaded_bytes=0)
            for row in rows['records']:
                step=cache.step(row)
                for key in total:total[key]+=step[key]
                partition['one_token_uploaded_bytes'if row['tokens']==1 else'multi_token_uploaded_bytes']+=step['misses']*9830400
            totals.append(total)
            partitions.append(partition)
        if totals!=item['requests']:raise ValueError('Python replay differs from actual dynamic native policy')
        if a.large_capacity_sweep and partitions!=item['request_partitions']:
            raise ValueError('Actual single/multi-token payload differs from independent replay')
    for predicted,native in zip(actual[0]['requests'],records):
        if predicted!=dict(hits=native['cache_hits'],misses=native['cache_misses'],unique=native['unique_selected_experts']):raise ValueError('53-slot replay differs from real native transfers')
    reduction=1-actual[1]['external_uploaded_bytes']/actual[0]['external_uploaded_bytes']
    result=dict(schema='ps5-qwen-cache-capacity-screen-v1',policies=actual,baseline_53_native_counters_exact=True,
        actual_ExpertPolicy_matches_Python_at_both_capacities=True,external_byte_reduction_fraction=reduction,
        original_three_bank_bytes=geometry['controls']['same_three_bank_bytes'],requires_new_owned_bank_and_dispatch_qualification=True,
        geometry_only_no_54_slot_native_execution=True,native_speed_qualified=False,PS5_operations=0,model_arithmetic=False)
    if a.research_capacity_sweep or a.large_capacity_sweep:
        baseline_peak=1069547520;original_bank_bytes=geometry['controls']['same_three_bank_bytes'];cap=1792<<20
        # Arithmetic envelope only: existing checkpoint peak plus extra bank
        # planes. This assumes unchanged other lifetimes and is not admission.
        for row in actual:
            bank=3*(row['slots']+1)*3293184
            peak=baseline_peak+bank-original_bank_bytes
            row.update(hypothetical_three_bank_bytes=bank,hypothetical_device_peak_bytes=peak,
                fits_original_512MiB_cache_cap=bank<=(512<<20),fits_1792MiB_arithmetic_envelope=peak<=cap,
                external_byte_reduction_fraction=1-row['external_uploaded_bytes']/actual[0]['external_uploaded_bytes'],
                decode_soft_floor=(row['slots']-10)//48,prefill_top40_soft_floor=(row['slots']-40)//48)
            if a.large_capacity_sweep:
                for name in('one_token_uploaded_bytes','multi_token_uploaded_bytes'):
                    value=sum(p[name]for p in row['request_partitions'][1:])
                    reference=sum(p[name]for p in actual[0]['request_partitions'][1:])
                    row['external_'+name]=value
                    row['external_'+name+'_reduction_fraction']=1-value/reference
        result.update(research_sweep_only=True,larger_capacity_native_geometry_qualified=False,
            actual_ExpertPolicy_matches_Python_at_all_capacities=True,
            actual_ExpertPolicy_matches_Python_at_both_capacities=False,
            original_cache_allocation_cap_unchanged=True,hypothetical_peak_is_not_physical_admission=True)
        if a.large_capacity_sweep:
            result.update(metadata_capacity_screen_max_slots=1024,
                application_device_and_cache_caps_unchanged=True,
                old_selected_caps_are_not_physical_capacity=True,
                source_byte_reduction_is_not_speedup=True,
                actual_ExpertPolicy_single_multi_partitions_match_Python=True)
    assert fixed==[record(f)for f in files]
    (a.out/'receipt.private.json').write_text(json.dumps(dict(result,inputs=fixed,command=command),indent=2)+'\n')
    print(json.dumps(result),flush=True)
if __name__=='__main__':main()
