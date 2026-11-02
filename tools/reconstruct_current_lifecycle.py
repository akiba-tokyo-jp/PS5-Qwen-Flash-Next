#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Recover the selected positive-boundary provider without changing its source or object."""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess

from audit_expert_all_q2_safety import body
from build_frontier_owner import transform as frontier
from build_service_completion import transform as idle
import build_throughput_owner as owner
from build_performance_quantizer import record
from build_speculative_batch_probe import once
from start_success_route import load,need,save

ROOT=Path(__file__).resolve().parents[1]


def source_text():
    source=owner.transform(frontier(idle((ROOT/'native/app/driver_lifecycle.cpp').read_text(encoding='utf-8'))))
    function=next(node for node in ast.parse(Path(owner.__file__).read_text(encoding='utf-8')).body if isinstance(node,ast.FunctionDef) and node.name=='transform')
    literals={node.targets[0].id:ast.literal_eval(node.value) for node in function.body if isinstance(node,ast.Assign) and
        isinstance(node.targets[0],ast.Name) and node.targets[0].id in ('old','new')}
    declaration='        ps5_ai_arena_stats owner{};\n'
    wrapper=declaration+'        if(!(qwen_throughput::mode.load(std::memory_order_relaxed)&4)){\n'+literals['old'].replace(declaration,'')+'\n        }else{\n'+literals['new'].replace(declaration,'')+'\n        }'
    return once(source,literals['new'],wrapper)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();native=load(a.current/'provenance/native-link.receipt.private.json')
    selected=native['frontier']['actual_sources']['lifecycle'];text=source_text()
    need(len(text.encode())==selected['bytes'] and hashlib.sha256(text.encode()).hexdigest()==selected['sha256'],
         'The complete selected positive-boundary source must reproduce byte-for-byte')
    finish=text[text.index('void DriverLifecycle::finish_boundary(bool end_producer) {'):]
    need('void DriverLifecycle::complete_work() { finish_boundary(true); }' in text and
         'void DriverLifecycle::checkpoint_work() { finish_boundary(false); }' in text and finish.count('end_producer')==3 and
         'ops_.stage(end_producer ?' in finish and 'if(end_producer)producer_active_.store(false);' in finish and
         'ops_.device_wait_idle(device)' in finish and 'ops_.kick_snapshot(&kick)' in finish and 'ops_.checkpoint()' in finish and
         'ops_.retire_quiet(kick.completed_epoch)' in finish,
         'Both APIs must retain the same full positive completion and ownership path')
    a.out.mkdir(parents=True,exist_ok=False);source=a.out/Path(selected['path']).name;source.write_text(text,encoding='utf-8',newline='\n')
    obj=a.out/'lifecycle.o';command=native['frontier']['commands']['lifecycle'].copy()
    command[command.index('-c')+1]=str(source);command[command.index('-o')+1]=str(obj)
    command[1:1]=['-I',str(ROOT/'native/app')]
    run=subprocess.run(command,capture_output=True,timeout=240,env=dict(os.environ,TMP=str(a.out),TEMP=str(a.out)))
    (a.out/'compile.private.log').write_bytes(run.stdout+run.stderr);need(run.returncode==0,run.stderr.decode(errors='replace')[-3500:])
    retained=load(a.current/'provenance/retained-relink-inputs.private.json');actual=next(row for row in retained if Path(row['original_path']).name=='lifecycle.o')
    need(record(actual['path'])=={key:actual[key] for key in ('path','bytes','sha256')},'The selected positive-boundary object changed')
    exact=all(record(obj)[key]==actual[key] for key in ('bytes','sha256'))
    save(a.out/'result.private.json',dict(completed=exact,selected_source_byte_exact=True,selected_object_byte_exact=exact,
        source=record(source),artifact=record(obj),actual_provider={key:actual[key] for key in ('path','bytes','sha256')},command=command,
        complete_and_checkpoint_use_same_positive_boundary=True,mandatory_device_worker_owner_journal_checks_preserved=True,
        producer_release_only_in_complete=True,PS5_operations=0,shared_driver_archive_changed=False))
    need(exact,'The recovered positive-boundary object is not byte-identical; do not qualify a completion-policy change')
    print(json.dumps(dict(completed=True,selected_object_byte_exact=True,same_full_positive_boundary=True,PS5_operations=0)))


if __name__=='__main__':main()
