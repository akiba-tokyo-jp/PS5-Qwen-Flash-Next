#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build one bounded durable publication batch in a new Q8-only directory."""
import argparse
import json
import os
import re
import secrets
import subprocess
from pathlib import Path
from expert_q4 import require, record, write_json
from build_speculative_batch_probe import once


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('plan','selection','out'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--previous-seal',type=Path)
    a=p.parse_args();base=json.loads(a.plan.read_text());selected=json.loads(a.selection.read_text())
    require(base['completed_build'] and base['CPU_only'] and base['original_source_writes']==0,'New-only full publication plan required')
    require(record(base['artifact']['path'])==base['artifact'],'Original CPU publication artifact changed')
    rows=[];indices=[]
    for item in selected:
        index=item['index'];require(type(index) is int and 0<=index<len(base['files']) and index not in indices,'Unique bounded publication index required')
        row=dict(base['files'][index]);source=item.get('source',row['source'])
        require(re.fullmatch(r'/data/ai/moss-qwen-layout-[0-9a-f]{32}-512-[01]\.bin',source),'New raw transfer namespace required')
        row['source']=source;rows.append(row);indices.append(index)
    require(0<len(rows)<=64,'Bounded nonempty batch required')
    previous=None
    if a.previous_seal:
        previous=json.loads(a.previous_seal.read_text());require(previous['completed'] and previous['new_directory']==base['new_directory'] and previous['CPU_owners_positively_closed'],'Completed same-directory native batch required')
        key=previous['directory_identity'];require(len(key)==10 and key[2]==0o40755 and key[3]==key[4]==0,'Exact owned new directory identity required')
    a.out.mkdir(parents=True,exist_ok=False);(a.out/'tmp').mkdir();nonce=secrets.token_hex(16);remote='/data/ai/moss-qwen-Q8-batch-'+nonce
    text=(a.plan.parent/'resident_output_Q8_publish_plan.h').read_text()
    text,n=re.subn(r'(?<=#define OUTPUT_Q8_PUBLISH_NONCE )"[0-9a-f]+"',json.dumps(nonce),text);require(n==1,'One fresh publisher nonce required')
    arr='inline constexpr OutputQ8PublicationFile output_Q8_files[]={'+','.join('{'+json.dumps(row['source'])+','+json.dumps(row['destination'])+','+str(row['local']['bytes'])+'ULL,'+json.dumps(row['local']['sha256'])+'}' for row in rows)+'};'
    text,n=re.subn(r'inline constexpr OutputQ8PublicationFile output_Q8_files\[\]=\{.*?\};',lambda _:arr,text);require(n==1,'One exact file array required')
    if previous:text+='\ninline constexpr std::array<std::uint64_t,10>batch_expected_directory={'+','.join(str(v)+'ULL' for v in previous['directory_identity'])+'};\n'
    header=a.out/'resident_output_Q8_publish_plan.h';header.write_text(text,newline='\n')
    source=(a.plan.parent/'publication.private.cpp').read_text();source=once(source,f'for(unsigned i=0;i<{len(base["files"])};++i)',f'for(unsigned i=0;i<{len(rows)};++i)')
    source=once(source,'immutable_files='+str(len(base['files']))+' whole_file_SHA256_and_EOF=1','immutable_files='+str(len(rows))+' whole_file_SHA256_and_EOF=1')
    if previous:
        source=once(source,'need(lstat(output_Q8_directory,&absent)&&errno==ENOENT,"Fresh Q8 directory required");','need(named(output_Q8_directory,true)==batch_expected_directory,"Existing owned Q8 batch directory changed");')
        source=once(source,'need(!mkdir(output_Q8_directory,0755),"Exclusive new Q8 directory creation failed");const auto root=named(output_Q8_directory,true);','const auto root=named(output_Q8_directory,true);need(root==batch_expected_directory,"New batch directory identity changed");')
    actual=a.out/'publication.private.cpp';actual.write_text(source,newline='\n')
    for name in ('CPU-only-headroom.private.c','qualified_context_guard.c','close_context.h'):(a.out/name).write_bytes((a.plan.parent/name).read_bytes())
    (a.out/'source_split_context.h').write_text('#pragma once\n#define SPLIT_LOG '+json.dumps(remote+'.log')+'\n',newline='\n')
    commands=[[v.replace(str(a.plan.parent),str(a.out)) for v in command] for command in base['commands']];commands[1][commands[1].index('-c')+1]=str(actual)
    for i,command in enumerate(commands):
        result=subprocess.run(command,capture_output=True,timeout=180,env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp')));(a.out/f'{i}.private.log').write_bytes(result.stdout+result.stderr);require(result.returncode==0,result.stderr.decode(errors='replace')[-3000:])
    artifact=a.out/'source-contention.elf';nm=Path(commands[1][0]).parent/'llvm-nm.exe';names={r.split()[0] for r in subprocess.check_output([str(nm),'-D','--undefined-only','--format=posix',str(artifact)],text=True).splitlines() if r.split()}
    require(names<=base['runtime_imports'].keys(),'New unaudited CPU batch import')
    write_json(a.out/'manifest.private.json',dict(completed_build=True,CPU_only=True,artifact=record(artifact),commands=commands,nonce=nonce,files=rows,indices=indices,new_directory=base['new_directory'],app0_directory=base['app0_directory'],
        full_plan=record(a.plan),previous_batch=record(a.previous_seal) if a.previous_seal else None,owned_Direct_bytes=8<<20,remote_elf=remote+'.elf',remote_log=remote+'.log',GPU_calls=0,title_launches=0,original_source_writes=0,maximum_executions=1,automatic_retries=0,
        inputs=[record(x) for x in (Path(__file__),a.plan,a.selection,header,actual,*[a.out/name for name in ('CPU-only-headroom.private.c','qualified_context_guard.c','close_context.h','source_split_context.h')])]))
    print('New-only durable Q8 batch built; existing owned directory requires its exact previous seal.')


if __name__=='__main__':main()
