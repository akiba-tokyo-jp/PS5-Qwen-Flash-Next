#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Index recorded refusals and successful resource observations without replay."""
import argparse,hashlib,json,re
from pathlib import Path

def objects(value,path=''):
    if isinstance(value,dict):
        yield path,value
        for key,child in value.items():yield from objects(child,path+'/'+key)
    elif isinstance(value,list):
        for i,child in enumerate(value):yield from objects(child,path+'/'+str(i))

def record(path,root):
    data=path.read_bytes()
    return dict(label=path.relative_to(root).as_posix(),bytes=len(data),sha256=hashlib.sha256(data).hexdigest())

def first(row,names):
    for name in names:
        value=row.get(name)
        if isinstance(value,int) and not isinstance(value,bool):return value
    return None

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cache',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--index',type=Path,help='Reconcile an existing immutable scan without rereading the native reports')
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    cases=[];observations=[];relevant=[]
    for directory in ([] if a.index else sorted(a.cache.glob('hardware-first-generation-*'))):
        if not re.fullmatch(r'hardware-first-generation-\d+',directory.name):continue
        terminal=directory/'native-model-terminal.private.json'
        if not terminal.is_file():continue
        t=json.loads(terminal.read_text('utf-8-sig'));number=int(directory.name.rsplit('-',1)[1])
        completed=t.get('completed') is True;back=t.get('memory_backpressure',{})
        close=directory/'restored-complete.private.json'
        closed=json.loads(close.read_text('utf-8-sig')) if close.is_file() else {}
        case=dict(case=number,completed=completed,requests=len(t.get('requests',[])),
                  message=t.get('message'),model_loaded=t.get('model_loaded'),
                  backpressure=back,ordinary_close=closed.get('CPU_title_normally_closed'),
                  model_receipt_sha256=t.get('model_receipt_sha256'),
                  terminal=record(terminal,a.cache),min_kernel_pages=None,peak_CPU_heap_bytes=0,
                  peak_device_ledger_bytes=0,actual_workspace_peak_bytes=0)
        paths={terminal}
        for pattern in ('native*memory*.private.json','native.resident.OS-reserve.private.json',
                        'native.resident.before-GPU.private.json','native.resident.loader-VM.private.json'):
            paths.update(directory.glob(pattern))
        for path in sorted(paths):
            data=t if path==terminal else json.loads(path.read_text('utf-8-sig'))
            for location,row in objects(data):
                free=first(row,('kernel_free_pages','kernel_free'))
                minimum=first(row,('kernel_minimum_pages','kernel_minimum'))
                reserved=first(row,('kernel_reserved_pages','kernel_reserved'))
                if free is not None:
                    observation=dict(case=number,completed_case=completed,file=path.name,
                        object=location,phase=row.get('phase'),free=free,minimum=minimum,reserved=reserved)
                    observations.append(observation)
                    case['min_kernel_pages']=free if case['min_kernel_pages'] is None else min(free,case['min_kernel_pages'])
                for key,destination in (('CPU_heap_peak_bytes','peak_CPU_heap_bytes'),
                                        ('device_ledger_peak_bytes','peak_device_ledger_bytes'),
                                        ('actual_workspace_capacity_peak_bytes','actual_workspace_peak_bytes')):
                    n=row.get(key)
                    if isinstance(n,int):case[destination]=max(case[destination],n)
        cases.append(case)
    if a.index:
        previous=json.loads(a.index.read_text('utf-8-sig'))
        cases,observations=previous['cases'],previous['observations']
    cases.sort(key=lambda row:row['case'])
    for case in cases:
        back=case['backpressure']
        if not case['completed'] and (re.search(r'memory|quota|budget|capacity|reserve|headroom|limit|checkpoint',str(case['message']),re.I)
                or (back.get('last_qualified')is False and back.get('pressure_events',0)>0)):
            relevant.append(case)
    result=dict(schema='ps5-qwen-limit-evidence-index-v1',completed=True,cases=cases,
                resource_refusals=relevant,observations=observations,PS5_operations=0,CI_runs=0,
                reconciled_index=record(a.index,a.cache)if a.index else None,
                source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                interpretation='Recorded successful observations are finite demonstrated points, not physical failure thresholds. Predicate counterfactuals do not establish later completion.')
    (a.out/'index.private.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n')
    positives=[x for x in cases if x['completed']]
    summary=dict(indexed_cases=len(cases),successful_terminals=len(positives),resource_refusals=len(relevant),
        indexed_observations=len(observations),max_successful_CPU_heap_bytes=max((x['peak_CPU_heap_bytes']for x in positives),default=0),
        latest_successful=[{k:x[k]for k in ('case','requests','min_kernel_pages','peak_CPU_heap_bytes','peak_device_ledger_bytes','actual_workspace_peak_bytes')}for x in positives[-12:]],
        refusals=[{k:x[k]for k in ('case','message','requests','min_kernel_pages')}for x in relevant])
    (a.out/'summary.private.json').write_text(json.dumps(summary,indent=2)+'\n',newline='\n')
    print(json.dumps(summary))

if __name__=='__main__':main()
