#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Validate independently bound 128-slot model evidence, without console access."""
import hashlib
from pathlib import Path

from expert_route_result import validate_routes
from padded_bank_result import validate_layout_report

CACHE_BYTES=1274462208
MODEL_REQUIREMENT=12042833408


def require(ok,message):
    if not ok:raise ValueError(message)


def digest(value):
    return type(value)is str and len(value)==64 and set(value)<=set('0123456789abcdef')


def validate_binding(scope):
    require(type(scope)is dict and set(scope)=={'schema','active_slots','physical_planes',
        'cache_request_bytes','context_allowance_bytes','layout_qualification'},'Exact independent 128-slot binding required')
    exact=dict(schema='ps5-qwen-cache128-model-binding-v1',active_slots=128,physical_planes=129,
        cache_request_bytes=CACHE_BYTES,context_allowance_bytes=256<<20)
    require(all(type(scope[k])is type(v)and scope[k]==v for k,v in exact.items()),'128-slot model geometry differs')
    proof=scope['layout_qualification']
    require(type(proof)is dict and set(proof)=={'run_id','pid','report_path','report_bytes','report_sha256','SELF_sha256'},
        'The complete original native layout qualification must be bound')
    run=proof['run_id']
    require(type(run)is str and len(run)==32 and set(run)<=set('0123456789abcdef') and
        proof['report_path']=='/app0/qwen-runtime/plan-'+run+'.json.padded-layout' and
        type(proof['pid'])is int and 0<proof['pid']<2**31 and
        type(proof['report_bytes'])is int and 0<proof['report_bytes']<=131072 and
        digest(proof['report_sha256'])and digest(proof['SELF_sha256']),'The native layout provenance differs')
    return proof


def validate_model(path,expected,result,read_record):
    proof=validate_binding(expected['cache128'])
    path=Path(path)
    saved=Path(str(path)+'.cache128.layout-qualification')
    require(saved.is_file()and saved.stat().st_size==proof['report_bytes'],'The complete layout proof is missing')
    require(hashlib.sha256(saved.read_bytes()).hexdigest()==proof['report_sha256'],'The bound layout SHA256 differs')
    layout=read_record(saved)
    require(layout.get('candidate_SELF_sha256')==proof['SELF_sha256'],'The layout producer differs')
    try:validate_layout_report(layout,proof['pid'],proof['run_id'],expected_slots=128)
    except (AssertionError,KeyError,TypeError,ValueError)as error:
        raise ValueError('The complete 128-slot numerical/layout qualification failed')from error
    after=read_record(Path(str(path)+'.memory.after-load'))
    require(after.get('model_loaded')is True and type(after.get('expert_cache_requested_bytes'))is int and
        after['expert_cache_requested_bytes']==CACHE_BYTES,'The model did not request the complete 128-slot cache')
    require(after.get('remaining_context_workspace_staging_reserve_bytes')==1152<<20 and
        after.get('device_budget_source')=='canary-validated native Direct allocator','The independently retained postload reserves differ')
    counters=[after.get(k)for k in ('native_Direct_available_bytes','native_Direct_owned_bytes','native_Direct_pool_bytes')]
    require(all(type(x)is int and 0<x<2**63 for x in counters)and
        counters[0]+counters[1]<=counters[2]and counters[0]>=(1152<<20)+CACHE_BYTES,
        'The actual postload Direct pool does not retain cache and working reserves')
    summaries=[]
    for ordinal,suffix in enumerate(('.first','.demo1','.demo2')):
        route=read_record(Path(str(path)+suffix+'.expert-routes'))
        require(route.get('sidecar_written_after_model_and_source_retirement')is True and
            route.get('JSON_created_after_model_and_source_retirement')is True,
            'Routes must be captured after model/source retirement')
        if ordinal:require(type(route.get('ordinal'))is int and route['ordinal']==ordinal,'The route ordinal differs')
        request=result if ordinal==0 else result['demonstration']['requests'][ordinal-1]
        summaries.append(validate_routes(route,request,width=4,pid=expected['pid'],run_id=expected['run_id'],
            cold=ordinal<2,expected_slots=128))
    return dict(active_slots=128,physical_planes=129,cache_request_bytes=CACHE_BYTES,
        complete_layout_SHA256_verified=True,requests=summaries,model_speed_qualified=False)
