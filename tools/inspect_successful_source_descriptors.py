#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Observe two exact read-only source descriptors with no payload reads or writes."""
import argparse
import json
from pathlib import Path

from build_performance_quantizer import record
from start_success_route import load,need,save
from success_case_control import ALIAS,PHYSICAL,build,current_files,execute,lan_module


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','mount-plan','source-proof','out'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--execute',action='store_true');a=p.parse_args();state=load(a.current/'active-console.private.json')
    need(state['original_restored'] and not state['native_running'] and not state['model_loaded'] and not state['unknown_completion'],
         'Positively restored idle deployment required')
    source=load(a.source_proof);need(source['completed'] and source['full_native_original_SHA256_and_EOF_preserved'] and
        source['path'].startswith(PHYSICAL+'/'),'One exact prior-sealed owned backing required')
    a.out.mkdir(parents=True,exist_ok=False);paths=[source['path'],ALIAS+source['path'][len(PHYSICAL):]]
    current=current_files(a.current)
    plan=build(a.workspace,a.mount_plan,current,current,[],'inspect-descriptors',a.out/'native',dependencies=paths)
    save(a.out/'intent.private.json',dict(source_proof=record(a.source_proof),paths=paths,payload_reads=0,payload_writes=0,
        title_launches=0,GPU_calls=0,initializer_requests=0))
    if not a.execute:return
    result=execute(lan_module(),plan,a.out/'native')
    need(result['completed'] and result['operation_calls']==0,'Read-only returned metadata observation required')
    save(a.out/'result.private.json',dict(completed=True,native=record(a.out/'native/result.private.json'),
        source_proof=record(a.source_proof),current_seven_unchanged_and_native_hashed=True,payload_reads=0,payload_writes=0,
        title_launches=0,GPU_calls=0,initializer_requests=0))
    print(json.dumps(dict(completed=True,descriptors=2,payload_reads=0,payload_writes=0,GPU_calls=0)))


if __name__=='__main__':main()
