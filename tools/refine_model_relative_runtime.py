#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Cache predictor metadata while preserving fresh worker and scratch-use checks."""
import argparse
import copy
import os
from pathlib import Path
import shutil
import subprocess
from build_performance_quantizer import record
from build_speculative_batch_probe import once
from driver_table_storage import sections
from start_success_route import load, need, save

ROOT=Path(__file__).resolve().parents[1]


def refined_header(text):
    text=once(text,'if(row.candidate){before=s.hooks.inspect(fd);row.before=before.fields;row.flags_before=before.flags;row.before_valid=before.valid;}',
        '''if(row.candidate){
            // This cached identity is only a prediction hint. It is never a
            // receipt for original I/O or permission to copy scratch bytes.
            lock.lock();const auto known=s.known_fd.find(fd);
            if(known!=s.known_fd.end())before=known->second;lock.unlock();
            if(!before.valid)before=s.hooks.inspect(fd);
            row.before=before.fields;row.flags_before=before.flags;row.before_valid=before.valid;
        }''')
    text=once(text,'if(same(after,key)){std::memcpy(destination,s.scratch,bytes);hit=true;++s.stats.hits;s.stats.hit_bytes+=bytes;}',
        'if(same(after,key)&&same(s.hooks.inspect(fd),key)){std::memcpy(destination,s.scratch,bytes);hit=true;++s.stats.hits;s.stats.hit_bytes+=bytes;}')
    text=once(text,'if(row.candidate){const auto after=s.hooks.inspect(fd);row.after=after.fields;row.flags_after=after.flags;row.after_valid=after.valid;}',
        '''if(row.candidate){
            // The immutable expected descriptor key trains only the predictor.
            // Both worker read boundaries and both cache-use boundaries remain fresh.
            row.after=before.fields;row.flags_after=before.flags;row.after_valid=before.valid;
        }''')
    return text


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','provider','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();old=load(a.provider)
    need(old['completed'] and old['new_global_constructors']==0 and
         all(record(x['path'])==x for x in old['inputs']),'The complete immutable qualified native provider is required')
    a.out.mkdir(parents=True,exist_ok=False)
    original=Path(old['artifact']['path']).parent
    for row in old['inputs']:shutil.copyfile(row['path'],a.out/Path(row['path']).name)
    header=a.out/'model_relative_prefetch.h';header.write_text(refined_header(header.read_text()),encoding='utf-8',newline='\n')
    text=(ROOT/'tests/model_relative_prefetch_test.cpp').read_text()
    text=once(text,'WORKER_ADMISSION};','WORKER_ADMISSION,HIT_IDENTITY_CHANGE};')
    text=once(text,'unsigned demand_entered=0,active=0,peak=0,closed=0,worker_reads=0;',
        'unsigned demand_entered=0,active=0,peak=0,closed=0,worker_reads=0,inspections=0;')
    text=once(text,'std::lock_guard<std::mutex>lock(mutex);if(!demand&&mode==IDENTITY&&worker_reads)++i.fields[1];return i;',
        'std::lock_guard<std::mutex>lock(mutex);++inspections;if((!demand&&mode==IDENTITY&&worker_reads)||mode==HIT_IDENTITY_CHANGE)++i.fields[1];return i;')
    marker='    std::cout<<"model_relative_prefetch_controls="'
    insert='''    {
        Fixture f(GOOD);for(unsigned i:{0u,1u,3u,7u,15u,31u,63u,127u})f.read(i);
        auto stats=f.owner->finish_request();check(stats.original_reads==8&&!stats.predictions&&f.inspections==1);
        check(!f.owner->close_source(3));f.owner->begin_request();f.read(0);
        stats=f.owner->finish_request();check(stats.original_reads==9&&f.inspections==2);
        f.owner->close_source(3);f.owner->close_completed();
    }
    {
        Fixture f(GOOD);f.train();f.ready();f.mode=HIT_IDENTITY_CHANGE;f.read(4);
        auto stats=f.owner->finish_request();check(!stats.hits&&stats.original_reads==5);
        f.owner->close_source(3);f.owner->close_completed();
    }
'''
    need(text.count(marker)==1,'One new refinement control insertion required');text=text.replace(marker,insert+marker,1)
    test=a.out/'refined-prefetch-test.private.cpp';test.write_text(text,encoding='utf-8',newline='\n')
    host=a.workspace/'toolchain/msys-clang64/clang64/bin';exe=a.out/'refined-prefetch-controls.exe'
    jobs=[[str(host/'clang++.exe'),'-std=c++17','-O2','-Wall','-Wextra','-Werror','-pthread','-I',str(a.out),str(test),'-o',str(exe)],[str(exe)]]
    env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''),TMP=str(a.out),TEMP=str(a.out))
    for i,job in enumerate(jobs):
        r=subprocess.run(job,capture_output=True,timeout=60,env=env);(a.out/f'host-{i}.private.log').write_bytes(r.stdout+r.stderr)
        need(r.returncode==0,(r.stdout+r.stderr).decode(errors='replace')[-4000:])
    need(b'model_relative_prefetch_controls=9' in r.stdout,'All changed-implementation concurrency cases must pass')
    controls=a.out/'controls.private.json';save(controls,dict(completed=True,new_concurrent_controls=9,
        new_refinement_controls=3,source=record(header),test=record(test),commands=jobs,ancestor=old['controls'],
        fresh_worker_before_after_checks=True,fresh_scratch_use_checks=2,close_invalidates_cached_descriptor=True,
        cached_metadata_is_predictor_hint_only=True,PS5_operations=0))
    command=[str(a.out) if x==str(original) else x for x in old['command']]
    obj=a.out/'model-relative-prefetch.o';source=a.out/'model_relative_prefetch_runtime.cpp'
    command[command.index('-c')+1]=str(source);command[command.index('-o')+1]=str(obj)
    r=subprocess.run(command,capture_output=True,timeout=90,env=env);(a.out/'native-compile.private.log').write_bytes(r.stdout+r.stderr)
    need(r.returncode==0,(r.stdout+r.stderr).decode(errors='replace')[-4000:])
    need(not any(s['name'].startswith(('.init_array','.ctors')) and s['bytes'] for s in sections(obj.read_bytes())),
         'The refined provider must not add a global initializer')
    result=copy.deepcopy(old);result.update(artifact=record(obj),controls=record(controls),command=command,
        inputs=[record(a.out/Path(x['path']).name) for x in old['inputs']],
        refinement='Cached immutable prediction keys; fresh worker and scratch-use identities',
        ancestor=record(a.provider),cached_metadata_is_predictor_hint_only=True,native_model_integration_qualified=False,
        model_decode_tok_s_measured=False,production_adopted=False,PS5_operations=0)
    save(a.out/'result.private.json',result)
    print(dict(completed=True,changed_implementation_concurrency_cases=9,new_refinement_cases=3,PS5_operations=0))


if __name__=='__main__':main()
