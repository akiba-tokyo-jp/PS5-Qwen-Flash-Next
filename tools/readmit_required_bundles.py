#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Observe all 69 actual owner dependencies without model or GPU execution."""
import argparse
import json
from pathlib import Path
import re
import struct

from build_performance_quantizer import record
from native_dispatch import ELF
from start_success_route import load,need,save
from success_case_control import build,current_files,execute,lan_module,PHYSICAL,ALIAS


def cstring(elf,address):
    for section in elf.sections:
        if section[1]!=8 and section[3]<=address<section[3]+section[5]:
            raw=elf.read(section[4]+address-section[3],min(512,section[3]+section[5]-address))
            need(b'\0' in raw,'Unterminated original bundle path')
            return raw.split(b'\0',1)[0].decode()
    raise ValueError('Actual owner path is not file-backed')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','mount-plan','identity-provider','baseline-relink','out'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--execute',action='store_true')
    parser.add_argument('--collect-existing',action='store_true',help='Validate an already completed observation without resubmitting it')
    args=parser.parse_args()
    need(not(args.execute and args.collect_existing),'Choose one fresh execution or read-only collection')
    baseline=load(args.baseline_relink);provider=load(args.identity_provider)
    need(baseline['completed'] and baseline['exact_current_native_ELF_reproduced'] and
         record(baseline['artifact']['path'])==baseline['artifact'],'Exact unchanged current ELF required')
    need(provider['completed'] and provider['strong_readonly_identity_definitions']==3 and
         provider['executable_bytes']==0 and record(provider['artifact']['path'])==provider['artifact'],
         'Authenticated read-only restored-input provider required')
    elf=ELF(Path(baseline['artifact']['path']));name='_ZN12_GLOBAL__N_116throughput_partsE'
    symbol=elf.symbols[name];raw=elf.symbol_data(name)
    need(len(raw)==66*88,'Exact current 66-part native owner ABI required')
    rows=[]
    for i in range(66):
        path=cstring(elf,elf.pointer(symbol['value']+88*i))
        need(re.fullmatch(r'/app0/qwen-full-bundles-[0-9a-f]{32}/part-[0-9]{3}\.bin',path),
             'Exact current full-bundle path required')
        identity=list(struct.unpack_from('<10Q',raw,88*i+8))
        need(identity[2:5]==[0o100444,0,0] and identity[5]>0,'Original immutable full-bundle identity required')
        rows.append(dict(path=path,identity=identity,bytes=identity[5],preservation='unchanged_actual_owner_identity'))
    for entry in provider['inputs']:
        reference=entry['restored_input'];need(record(reference['path'])==reference,'Restored evidence changed')
        restored=load(reference['path'])
        rows.append(dict(path='/app0'+restored['path'][len(PHYSICAL):],identity=restored['identity'],
            bytes=restored['bytes'],sha256=restored['sha256'],preservation='native_whole_original_SHA256_and_EOF',
            restored_input=reference))
    need(len(rows)==len({r['path'] for r in rows})==69,'All 69 distinct current dependencies required')
    paths=[root+r['path'][5:] for root in (PHYSICAL,ALIAS) for r in rows]
    files=current_files(args.current)
    if args.collect_existing:
        plan=load(args.out/'plan.private.json');result=load(args.out/'result.private.json')
        need(result['completed'] and result['helper_exited'] and result['helper_files_removed'] and
             plan['operation']=='dependencies' and plan['old_files']==files and plan['new_files']==files,
             'Only an already completed same-current observation may be collected')
        context=Path(plan['context']['path']).read_text()
        need(record(plan['context']['path'])==plan['context'] and
             'static const char*case_dependencies[]={'+','.join(map(json.dumps,paths))+'};' in context,
             'Exact completed 138-path observation context required')
    else:
        plan=build(args.workspace,args.mount_plan,files,files,[],'dependencies',args.out,dependencies=paths)
        save(args.out/'required-inputs.plan.private.json',dict(completed=True,rows=rows,owner=provider['owner'],
            identity_provider=record(args.identity_provider),baseline_relink=record(args.baseline_relink),
            live_native_metadata_verified=False,current_only_retention_required=True))
        if not args.execute:print('All 69 current owner dependencies prepared; PS5 operations=0');return
        result=execute(lan_module(),plan,args.out)
    need(record(result['raw']['path'])==result['raw'],'Completed native dependency journal changed')
    raw=(args.out/'execution/console.private.log').read_bytes()
    pattern=rb'DEPENDENCY index=(\d+) lstat_rc=(-?\d+) errno=(\d+) device=(\d+) inode=(\d+) mode=(\d+) uid=(\d+) gid=(\d+) bytes=(\d+) mtime_sec=(\d+) mtime_nsec=(\d+) ctime_sec=(\d+) ctime_nsec=(\d+)'
    seen=re.findall(pattern,raw)
    need(len(seen)==138 and [int(r[0]) for r in seen]==list(range(138)), 'Complete physical and mounted dependency observations required')
    for i,observation in enumerate(seen):
        values=list(map(int,observation));expected=rows[i%69]['identity']
        need(values[1:3]==[0,0], 'A live current owner input is missing')
        observed=values[3:]
        need(observed[1:]==expected[1:] and (i>=69 or observed[0]==expected[0]),
             'An original live current owner input changed')
        if i>=69:need(observed[0]>0,'Positive mounted namespace device required')
    report=dict(completed=True,rows=rows,owner=provider['owner'],identity_provider=record(args.identity_provider),
        baseline_relink=record(args.baseline_relink),native_result=record(args.out/'result.private.json'),
        live_native_metadata_verified=True,physical_and_mounted_observations=138,
        whole_SHA256_restored_inputs=3,unchanged_actual_owner_identity_inputs=66,
        current_only_retention_required=True,GPU_calls=0,model_loads=0,title_launches=0,initializer_requests=0)
    save(args.out/'required-inputs.private.json',report)
    save(args.current/'provenance/required-bundle-inputs.private.json',report)
    state_path=args.current/'active-console.private.json';state=load(state_path)
    state['required_bundle_inputs']=record(args.current/'provenance/required-bundle-inputs.private.json')
    for row in state.get('native_required_bundle_restorations',[]):
        for restored in state['restored_required_bundle_inputs']:
            if row['report']==restored['native_report']:
                row['root_ownership_finalization_pending']=False;row['canonical_finalization']=restored['finalization']
    state_path.write_text(json.dumps(state,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('rows','owner','identity_provider','baseline_relink','native_result')}))


if __name__=='__main__':main()
