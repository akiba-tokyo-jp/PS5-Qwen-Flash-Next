#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Package one explicitly compiled finite audit against the selected current inputs."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

from build_performance_quantizer import record
from start_success_route import load,need,save

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','build','identity-provider','out'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--full-F32-observer',type=Path)
    a=p.parse_args();compiled=load(a.build);policy=load(compiled['application_policy']['path'])
    need(compiled['completed'] and policy['completed'] and policy['kind']=='headless-model-audit' and
         policy['headless_model_audit'] and policy['model_and_GPU_guards_preserved'],'Exact guarded headless audit required')
    for key in ('entry','reader','provider','source','application_policy'):
        need(record(compiled[key]['path'])==compiled[key],'A compiled audit provider changed')
    a.out.mkdir(parents=True,exist_ok=False)
    arguments=['--current',a.current,'--out',a.out/'link','--replace','entry.o='+compiled['entry']['path'],
        '--replace','early-SELF.o='+compiled['reader']['path'],'--add-object',compiled['provider']['path'],
        '--application-policy',compiled['application_policy']['path']]
    if 'graph' in compiled:
        need(record(compiled['graph']['path'])==compiled['graph'],'Compiled graph changed')
        arguments+=['--replace','graph.o='+compiled['graph']['path']]
    if a.full_F32_observer:
        observer=load(a.full_F32_observer)
        need(observer['completed'] and observer['qualification_only'] and observer['extra_GPU_downloads']==0 and
             record(observer['artifact']['path'])==observer['artifact'],'Exact existing-row qualification observer required')
        arguments+=['--add-object',observer['artifact']['path']]+['--link-flag='+flag for flag in observer['link_flags']]
    jobs=[('link','relink_retained_current.py',arguments),('SELF','package_retained_current.py',[
        '--workspace',a.workspace,'--current',a.current,'--relink',a.out/'link/result.private.json','--out',a.out/'SELF',
        '--formatter-from',a.current/'provenance/current-package.private.json','--identity-provider',a.identity_provider])]
    for label,tool,args in jobs:
        with (a.out/(label+'.private.log')).open('xb') as stream:
            result=subprocess.run([sys.executable,'-B',str(ROOT/'tools'/tool),*map(str,args)],stdout=stream,stderr=subprocess.STDOUT,timeout=600)
        need(result.returncode==0,'Host '+label+' failed; inspect '+str(a.out/(label+'.private.log')))
        print(json.dumps(dict(phase=label,completed=True,PS5_operations=0)),flush=True)
    save(a.out/'result.private.json',dict(completed=True,build=record(a.build),package=record(a.out/'SELF/result.private.json'),
        full_F32_qualification=bool(a.full_F32_observer),PS5_operations=0,native_qualified=False,production_adopted=False))


if __name__=='__main__':main()
