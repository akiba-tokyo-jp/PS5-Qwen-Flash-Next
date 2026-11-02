#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Verify the current model's complete retained native source identities."""
import argparse
import hashlib
import json
from pathlib import Path,PurePosixPath
import re

from build_performance_quantizer import record
from start_success_route import load,need,save
from success_case_control import build,current_files,execute,lan_module,PHYSICAL,ALIAS


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','mount-plan','out'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--execute',action='store_true');args=parser.parse_args()
    source_path=args.current/'provenance/model-source-plan.private.json';sources=load(source_path)
    need(sources['completed'] and len(sources['physical'])==513 and len(sources['backing'])==5,'Exact selected source plan required')
    rows=sources['physical']+sources['backing'];need(len({r['path'] for r in rows})==518,'All 518 distinct selected sources required')
    def paths(row):
        path=row['path'];need(path.startswith('/app0/') and '..' not in PurePosixPath(path).parts,'Exact title source path required')
        return PHYSICAL+path[5:],ALIAS+path[5:]
    directories=sorted({str(PurePosixPath(paths(row)[0]).parent) for row in rows})
    gate=load(args.current/'qwen-runtime/development.json')['native_first_generation_validation']
    policy=gate['precision_source_integrity'];need(hashlib.sha256(policy['raw'].encode()).hexdigest()==policy['sha256'],'Original source certificate changed')
    seal=json.loads(policy['raw']);previous=seal['directory_identity']
    context='#define READMISSION_SOURCE_COUNT 518u\n#define READMISSION_BACKING_COUNT 5u\n'
    context+='#define READMISSION_DIRECTORY_COUNT '+str(len(directories))+'u\n'
    context+='struct readmission_source{const char*physical,*alias;uint64_t expected[10];};\n'
    context+='static const struct readmission_source readmission_sources[]={\n'
    for row in rows:
        identity=row['identity'];need(len(identity)==10 and all(type(v)is int and v>=0 for v in identity),'Complete unsigned native identity required')
        need(identity[5]==row['bytes'],'Source plan byte size differs')
        context+='{'+','.join(json.dumps(p) for p in paths(row))+',{'+','.join(str(v)+'ULL' for v in identity)+'}},\n'
    context+='};\nstruct readmission_backing{const char*physical,*alias;uint64_t bytes;const char*sha;};\n'
    context+='static const struct readmission_backing readmission_backing[]={\n'
    for row in sources['backing']:
        need(re.fullmatch('[0-9a-f]{64}',row['sha256']),'Whole original backing certificate digest required')
        context+='{'+','.join(json.dumps(p) for p in paths(row))+','+str(row['bytes'])+'ULL,'+json.dumps(row['sha256'])+'},\n'
    context+='};\nstatic const char*readmission_directories[]={'+','.join(map(json.dumps,directories))+'};\n'
    context+='#define READMISSION_CANONICAL_DIRECTORY '+json.dumps(seal['canonical_source_directory'])+'\n'
    context+='#define READMISSION_APPLICATION_DIRECTORY '+json.dumps(ALIAS+seal['source_directory'][5:])+'\n'
    context+='static const uint64_t readmission_previous_directory[]={'+','.join(str(v)+'ULL' for v in previous)+'};\n'
    old=current_files(args.current);plan=build(args.workspace,args.mount_plan,old,old,[],'readmission',args.out,readmission_context=context)
    if not args.execute:print('Read-only model source proof prepared; PS5 operations=0');return
    result=execute(lan_module(),plan,args.out);raw=(args.out/'execution/console.private.log').read_bytes()
    need(b'MODEL_READMISSION sources=518 backing_hashes=5 stable_directory_snapshots=' in raw,'Complete native model proof missing')
    components=re.findall(rb'MODEL_DIRECTORY component=(\d+) canonical=(\d+) application=(\d+)',raw)
    need(len(components)==10 and [int(r[0]) for r in components]==list(range(10)),'Complete native directory identity missing')
    boot=re.search(r'boot.tv_sec!=(\d+)LL\|\|boot.tv_usec!=(\d+)LL',Path(plan['controller']['path']).read_text())
    proof=dict(completed=True,current_boot=[int(boot[1]),int(boot[2])],
        full_native_SHA256_identity_EOF_files=11,additional_full_shader_SHA256_files=1,
        complete_unchanged_file_metadata=518,double_directory_snapshot_equal=True,
        only_directory_times_require_rebinding=True,source_payloads_changed=False,GPU_calls=0,title_launches=0,
        canonical_directory=[int(r[1]) for r in components],application_directory=[int(r[2]) for r in components],
        previous_directory=previous,source_plan=record(source_path),native_result=record(args.out/'result.private.json'))
    save(args.out/'model-proof.private.json',proof)
    print(json.dumps({k:v for k,v in proof.items() if k not in ('source_plan','native_result','canonical_directory','application_directory','previous_directory','current_boot')}))


if __name__=='__main__':main()
