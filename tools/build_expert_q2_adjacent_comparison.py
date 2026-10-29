#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build one finite adjacency ABBA with observed two-lane I/O occupancy."""
import argparse,copy,json,os,subprocess
from pathlib import Path
from expert_q4 import require,record,write_json
from active_native_inputs import active_link_inputs
from build_speculative_batch_probe import once
from build_expert_q2_bundle_comparison import SCOPE as OLD_SCOPE,MODEL_SCOPE,IO_SCOPE,literal
from build_expert_q2_reader_comparison import owner_source as hint_owner
from expert_q2_reader_candidates import candidate_header
from expert_q2_adjacent_bundle import header_source,owner_source,cache_source
from driver_table_storage import audit_linked_storage
from audit_native_imports import audit
from native_dispatch import audit as dispatch
ROOT=Path(__file__).resolve().parents[1]
SCOPE=dict(OLD_SCOPE,schema='ps5-qwen-Q2-adjacent-bundle-ABBA-v1',
    order=[False,False,True,True,False],partial_bundles_always_enabled=True,
    immutable_range_hint_always_enabled=True,maximum_group_Experts=5,maximum_group_read_bytes=7700480,
    I_O_occupancy_observed=True,additional_scratch_bytes=0,additional_worker_threads=0)

def entry_source(text):
    text='''#include <source_io_occupancy.h>
extern "C" void qwen_app_select_Q2_adjacent(bool);
extern "C" std::uint64_t qwen_app_Q2_merged_calls_saved();
extern "C" void qwen_app_select_Q2_reader(unsigned);
'''+text
    text=once(text,literal(OLD_SCOPE),literal(SCOPE))
    text=once(text,'                qwen_app_select_Q2_bundle(probation);',
        '                qwen_app_select_Q2_bundle(true);qwen_app_select_Q2_reader(1);qwen_app_select_Q2_adjacent(probation);')
    text=once(text,'(probation?"partial-Expert-bundles":"original-Expert-reads")',
        '(probation?"adjacent-bundle-groups":"single-Expert-bundles")')
    text=once(text,'    result["bundle_Experts"]=qwen_app_Q2_bundle_hits();','''    result["bundle_Experts"]=qwen_app_Q2_bundle_hits();
    result["adjacent_bundle_calls_saved"]=qwen_app_Q2_merged_calls_saved();
    std::uint64_t occupancy[7]{};qwen_app_source_io_occupancy(occupancy,7);
    for(unsigned i=0;i<7;++i)result["source_IO_occupancy_"+std::to_string(i)]=occupancy[i];''')
    return text

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('parent','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--resume-cache-only',action='store_true',help='Retain successful unchanged entry/owner objects after a cache compile failure')
    a=p.parse_args();prior=json.loads(a.parent.read_text());require(prior['all_Q2_bundle_comparison']['scope']==OLD_SCOPE,'Exact completed bundle parent required')
    frozen=active_link_inputs(prior)+[r for r in prior['inputs_before']if Path(r['path']).suffix=='.so']
    frozen += [record(x)for x in (a.parent,Path(__file__),ROOT/'tools/expert_q2_adjacent_bundle.py',ROOT/'native/app/source_io_occupancy.h')]
    for r in frozen:require(record(r['path'])==r,'Qualified immutable input changed')
    if a.resume_cache_only:
        require(a.out.is_dir() and not (a.out/'receipt.private.json').exists() and (a.out/'2.private.log').exists(),'Only a returned host cache compile failure may resume')
    else:
        a.out.mkdir(parents=True,exist_ok=False);(a.out/'tmp').mkdir()
    original_header=prior['all_Q2_bundle_comparison']['actual_header'];header=a.out/'resident-mapped-source.private.h'
    header.write_text(header_source(candidate_header(Path(original_header['path']).read_text())),newline='\n')
    bundle_plan=Path(original_header['path']).parent/'Q2-bundle-plan.private.h';(a.out/bundle_plan.name).write_bytes(bundle_plan.read_bytes())
    owner=prior['all_Q2_IO_measurement']['owner'];cache=prior['expert_q2_model']['actual_cache'];entry=prior['expert_q2_model']['actual_entry']
    variants=[('entry',prior['compile_commands'][0],entry,entry_source),
              ('owner',prior['all_Q2_IO_measurement']['commands'][1],owner,lambda s:owner_source(hint_owner(s))),
              ('cache',prior['expert_q2_model']['commands'][1],cache,cache_source)]
    replacements={};commands=[];added=[record(header),record(a.out/bundle_plan.name),original_header]
    for label,oldcommand,oldrecord,derive in variants:
        require(record(oldrecord['path'])==oldrecord,'Actual source changed')
        source=a.out/(label+'.private.cpp');derived=derive(Path(oldrecord['path']).read_text())
        if a.resume_cache_only and label in ('entry','owner'):
            require(source.read_text()==derived and (a.out/(label+'.o')).is_file(),'Successful host objects require identical complete source')
        else:source.write_text(derived,newline='\n')
        command=oldcommand.copy();oldobj=command[command.index('-o')+1];obj=a.out/(label+'.o')
        command[command.index('-c')+1]=str(source);command[command.index('-o')+1]=str(obj)
        command[1:1]=['-I',str(Path(oldrecord['path']).parent)]
        if '-MF'in command:command[command.index('-MF')+1]=str(a.out/(label+'.private.d'))
        require(prior['link_command'].count(oldobj)==1,'One actual override required');replacements[oldobj]=str(obj)
        commands.append(command);added.extend((record(source),oldrecord))
    image=a.out/'qwen-native.pie.elf';link=[replacements.get(x,x)for x in prior['link_command']];link[link.index('-o')+1]=str(image)
    link=[('-Map='+str(a.out/'native-link.private.map'))if x.startswith('-Map=')else x for x in link]
    for i,command in enumerate(commands+[link]):
        if a.resume_cache_only and i<2:
            require('error:'not in (a.out/f'{i}.private.log').read_text(),'A failed earlier compile cannot be reused')
            continue
        run=subprocess.run(command,capture_output=True,timeout=600,env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp')))
        (a.out/f'{i}.private.log').write_bytes(run.stdout+run.stderr);require(run.returncode==0,run.stderr.decode(errors='replace')[-4000:])
        print(json.dumps(dict(build_step=i+1,total=4)),flush=True)
    for r in frozen:require(record(r['path'])==r,'Frozen source changed')
    receipt=copy.deepcopy(prior);receipt.update(artifact=record(image),link_command=link,compile_commands=[commands[0]],source_parent=record(a.parent),
        inputs_before=frozen+added+[record(a.out/(x+'.o'))for x in ('entry','owner','cache')],lossless_driver_table_geometry=audit_linked_storage(image,prior['lossless_driver_tables']))
    receipt['expert_q2_model'].update(actual_entry=record(a.out/'entry.private.cpp'),actual_cache=record(a.out/'cache.private.cpp'),commands=[commands[0],commands[2]])
    receipt['all_Q2_IO_measurement'].update(entry=record(a.out/'entry.private.cpp'),owner=record(a.out/'owner.private.cpp'),commands=commands)
    receipt['all_Q2_bundle_comparison'].update(scope=SCOPE,commands=commands,actual_header=record(header),original_header=original_header,production_adopted=False)
    receipt['all_Q2_adjacent_comparison']=dict(scope=SCOPE,host_analysis=record(ROOT/'.local/Q2-IO-distribution-9332/receipt.private.json'),maximum_new_counter_bytes=128)
    target=a.out/'receipt.private.json';write_json(target,receipt)
    receipt['real_module_import_audit']=audit(a.workspace,a.cache,a.out);receipt['native_dispatch_audit']=dispatch(a.workspace,a.workspace/'driver-work/PS5-Vulkan-Inference-qwen-872cc126',image,a.out/'dispatch')
    require(not receipt['real_module_import_audit']['missing']and receipt['native_dispatch_audit']['passed'],'Import/dispatch audit failed');write_json(target,receipt)
    print('Native adjacency comparison linked; no console operation or CI executed.',flush=True)
if __name__=='__main__':main()
