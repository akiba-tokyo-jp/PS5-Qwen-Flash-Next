#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Relink and package both completed-stage variants, optionally with full-F32 observation."""
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
    for name in ('workspace','current','build','formatter-from','identity-provider','out'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--full-F32-observer',type=Path);a=p.parse_args();compiled=load(a.build)
    need(compiled['completed'] and compiled['host_durable_boundary_controls_passed'],'Completed paired compilation required')
    need(record(compiled['bootstrap']['path'])==compiled['bootstrap'],'Selected journal provider changed')
    observer=None
    if a.full_F32_observer:
        observer=load(a.full_F32_observer)
        need(observer['completed'] and observer['qualification_only'] and observer['extra_GPU_downloads']==0 and
             record(observer['artifact']['path'])==observer['artifact'],'Exact qualification-only F32 provider required')
    a.out.mkdir(parents=True,exist_ok=False);packages={}
    for label in ('control','candidate'):
        selected=compiled['variants'][label]
        for key in ('entry','profile'):need(record(selected[key]['path'])==selected[key],'Compiled entry or policy changed')
        profile=load(selected['profile']['path']);reader=profile['CPU_SELF_provider']['artifact']
        folder=a.out/label;folder.mkdir()
        arguments=['--current',a.current,'--out',folder/'link',
            '--replace','entry.o='+selected['entry']['path'],'--replace','early-SELF.o='+reader['path'],
            '--replace','native-bootstrap-boot-qualified.o='+compiled['bootstrap']['path'],
            '--application-policy',selected['profile']['path']]
        if observer:
            arguments+=['--add-object',observer['artifact']['path']]
            arguments+=['--link-flag='+value for value in observer['link_flags']]
        jobs=[('link','relink_retained_current.py',arguments),('package','package_retained_current.py',[
            '--workspace',a.workspace,'--current',a.current,'--relink',folder/'link/result.private.json',
            '--out',folder/'SELF','--formatter-from',a.formatter_from,'--identity-provider',a.identity_provider])]
        for name,script,args in jobs:
            command=[sys.executable,'-B',str(ROOT/'tools'/script),*map(str,args)]
            with (folder/(name+'.private.log')).open('xb') as stream:
                result=subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT,timeout=600)
            need(result.returncode==0,'Host '+name+' failed; inspect '+str(folder/(name+'.private.log')))
        packages[label]=record(folder/'SELF/result.private.json')
        print(json.dumps(dict(variant=label,packaged=True,full_F32_qualification=bool(observer),PS5_operations=0)),flush=True)
    save(a.out/'result.private.json',dict(completed=True,compiled=record(a.build),packages=packages,
        full_F32_qualification=bool(observer),PS5_operations=0,production_adopted=False))


if __name__=='__main__':main()
