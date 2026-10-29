#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Relink only the entry and qualified source owner for packed Q2/Q4 sources."""
import argparse,copy,json,os,subprocess
from pathlib import Path
from expert_q4 import record,require,write_json
from expert_q2_sparse_reader import reader_header,reader_source
from active_native_inputs import active_link_inputs
from driver_table_storage import audit_linked_storage
from native_dispatch import audit as dispatch
from audit_native_imports import audit
ROOT=Path(__file__).resolve().parents[1]
PACKED_SCOPE=dict(schema='ps5-qwen-expert-q2-composite-source-v1',enabled=True,
    new_payloads='Gate_Up_Q2_K',retained_payloads='sealed_Q4_Down_and_non_Expert',
    complete_logical_GGUF=True,physical_part_bytes=512<<20,maximum_source_handles=8,
    maximum_source_ranges=8192,maximum_backing_metadata_bytes=1<<20,
    original_BF16_and_Q4_sources_modified=False,CPU_matrix_fallback=False,
    GPU_or_memory_floor_changes=0,automatic_retries=0)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--finalize-existing',action='store_true');p.add_argument('--reuse-owner',type=Path)
    p.add_argument('--complete-prefix-metadata',action='store_true')
    for key in ('parent','workspace','cache','out'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();prior=json.loads(a.parent.read_text())
    frozen=active_link_inputs(prior)+[record(a.parent),record(__file__)]
    for row in frozen:require(record(row['path'])==row,'The qualified mixed-precision parent changed')
    existing={}
    if a.finalize_existing:
        require(not(a.out/'receipt.private.json').exists(),'Only a completed pre-audit link may be finalized once')
        for name in ('entry.o','owner.o','qwen-native.pie.elf','Q2-composite-entry.private.cpp','Q2-composite-owner.private.cpp','resident-mapped-source.private.h','reader-overlay.private.json','native-link.private.map'):
            existing[name]=record(a.out/name)
        require(all((a.out/f'{i}.private.log').is_file()for i in range(3)),'All completed compile/link logs required')
    a.out.mkdir(parents=True,exist_ok=a.finalize_existing);(a.out/'tmp').mkdir(exist_ok=a.finalize_existing)
    geometry=json.loads((a.cache/'build/additional-cache-6290/receipt.private.json').read_text())
    owner=next(row for row in geometry['additional_cache_geometry']['compiled']
        if Path(row['object']['path']).name.startswith('8-mapped-source'))
    actual=Path(owner['compiled_source']['path']);require(record(actual)==owner['compiled_source'],'Actual selected source owner changed')
    header=a.cache/'additional-cache-build-plan-6204/vfs/b697011b0638954f-resident-mapped-source.private.h';derived=a.out/'resident-mapped-source.private.h'
    derived.write_text(reader_header(header.read_text()),newline='\n')
    source=a.out/'Q2-composite-owner.private.cpp';source.write_text(reader_source(actual.read_text()),newline='\n')
    entry_before=Path(prior['expert_q2_model']['actual_entry']['path']);text=entry_before.read_text()
    require(text.count('#include "expert_q2_source_integrity.h"')==1,'One exact mixed source-validator replacement required')
    text=text.replace('#include "expert_q2_source_integrity.h"','#include "expert_q2_composite_source.h"',1)
    text=text.replace('qwen_app::expert_q2_source_integrity(','qwen_app::expert_q2_composite_source_integrity(',1)
    marker='        const auto receipt = qwen_app::read_model_receipt(startup.model_receipt);'
    require(text.count(marker)==1,'One exact original receipt admission required')
    text=text.replace(marker,'        if(policy.at("native_Expert_Q2_composite_sources")!=Json::parse('+json.dumps(json.dumps(PACKED_SCOPE,separators=(',',':')))+'))\n'
        '            throw std::runtime_error("Exact finite packed-source scope required");\n'+marker,1)
    marker='            qwen_app::start_native_model_sources(std::move(sources),std::move(logical));'
    require(text.count(marker)==1,'One original source startup required')
    text=text.replace(marker,'            qwen_app::configure_expert_q2_source_segments(std::move(qwen_app::expert_q2_pending_segments));\n'+marker,1)
    if a.complete_prefix_metadata:
        from expert_q2_metadata_reader import metadata_entry
        text=metadata_entry(text)
    entry=a.out/'Q2-composite-entry.private.cpp';entry.write_text(text,newline='\n')
    commands=[prior['compile_commands'][0].copy(),owner['command'].copy()]
    # Quoted headers can resolve through several preserved include views.
    # Map every existing candidate to one exact immutable derived header.
    aliases={(a.cache/'build/cache128-postload-5460/resident-mapped-source.private.h').resolve()}
    for command in commands:
        for i,arg in enumerate(command[:-1]):
            if arg=='-I':
                path=Path(command[i+1])/'resident-mapped-source.private.h'
                if path.is_file():aliases.add(path.resolve())
    overlay=a.out/'reader-overlay.private.json'
    write_json(overlay,dict(version=0,**{'case-sensitive':'false','use-external-names':False},
        roots=[dict(type='file',name=str(path).replace('\\','/'),**{'external-contents':str(derived).replace('\\','/')})for path in sorted(aliases)]))
    objects=[]
    for i,(command,src)in enumerate(zip(commands,(entry,source))):
        obj=a.out/('entry.o'if i==0 else'owner.o');objects.append(obj)
        command[command.index('-c')+1]=str(src);command[command.index('-o')+1]=str(obj)
        if '-MF'in command:command[command.index('-MF')+1]=str(a.out/f'{i}.private.d')
        command[1:1]=['-I',str(a.out)];command+=['-I',str(actual.parent),'-I',str(entry_before.parent),'-ivfsoverlay',str(overlay)]
    reuse_owner=None
    if a.reuse_owner:
        reused=json.loads(a.reuse_owner.read_text());details=reused['expert_q2_model']
        require(record(details['source_owner']['path'])==details['source_owner']and Path(details['source_owner']['path']).read_text()==source.read_text(),
            'The reused actual source-owner code must match exactly')
        require(record(details['reader_header']['path'])==details['reader_header']and Path(details['reader_header']['path']).read_text()==derived.read_text(),
            'The reused actual reader header must match exactly')
        captured=details['packed_source_commands'][1];reuse_owner=Path(captured[captured.index('-o')+1]);objects[1]=reuse_owner;commands[1]=captured
        frozen +=[record(a.reuse_owner),details['source_owner'],details['reader_header'],record(reuse_owner)]
    old_entry=prior['compile_commands'][0][prior['compile_commands'][0].index('-o')+1]
    replacements={old_entry:str(objects[0]),owner['object']['path']:str(objects[1])}
    metadata_details=None
    if a.complete_prefix_metadata:
        require(not a.finalize_existing,'Completed legacy links cannot acquire a new metadata owner')
        from expert_q2_metadata_reader import metadata_source
        metadata=next(row for row in geometry['additional_cache_geometry']['compiled']if 'direct_metadata'in Path(row['object']['path']).name)
        actual_metadata=Path(metadata['compiled_source']['path']);require(record(actual_metadata)==metadata['compiled_source'],'Qualified metadata source changed')
        metadata_cpp=a.out/'Q2-composite-metadata.private.cpp';metadata_cpp.write_text(metadata_source(actual_metadata.read_text()),newline='\n')
        cmd=metadata['command'].copy();obj=a.out/'metadata.o'
        cmd[cmd.index('-c')+1]=str(metadata_cpp);cmd[cmd.index('-o')+1]=str(obj)
        if '-MF'in cmd:cmd[cmd.index('-MF')+1]=str(a.out/'metadata.private.d')
        cmd[1:1]=['-I',str(ROOT/'native/app')];cmd+=['-I',str(actual_metadata.parent)]
        commands.append(cmd);objects.append(obj);replacements[metadata['object']['path']]=str(obj)
        frozen +=[record(actual_metadata),record(metadata_cpp),record(ROOT/'tools/expert_q2_metadata_reader.py'),record(ROOT/'native/app/expert_q2_metadata_window.h')]
        metadata_details=dict(original=metadata['compiled_source'],source=record(metadata_cpp),command=cmd,
            header=record(ROOT/'native/app/expert_q2_metadata_window.h'),ordinary_registration_unchanged=True,
            complete_header_prefix_checked_before_registration=True)
    for old in replacements:require(prior['link_command'].count(old)==1,'One exact source/entry object replacement required')
    link=[replacements.get(x,x)for x in prior['link_command']];image=a.out/'qwen-native.pie.elf';link[link.index('-o')+1]=str(image)
    link=[('-Map='+str(a.out/'native-link.private.map'))if x.startswith('-Map=')else x for x in link]
    frozen +=[record(path)for path in (actual,header,derived,source,entry,entry_before,overlay,
        ROOT/'tools/expert_q2_sparse_reader.py',ROOT/'native/app/expert_q2_sparse.h',
        ROOT/'native/app/expert_q2_composite_source.h',ROOT/'native/app/expert_q2_receipt.h',ROOT/'native/app/expert_q2_source_integrity.h')]
    for i,command in enumerate([]if a.finalize_existing else commands+[link]):
        if i==1 and reuse_owner:
            print(json.dumps(dict(qualified_source_owner_reused=True,recompiled=False)),flush=True);continue
        x=subprocess.run(command,cwd=ROOT,capture_output=True,timeout=600,env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp')))
        (a.out/f'{i}.private.log').write_bytes(x.stdout+x.stderr);require(x.returncode==0,x.stderr.decode(errors='replace')[-6000:])
        print(json.dumps(dict(packed_source_build_step=i+1,total=len(commands)+1)),flush=True)
    for name,row in existing.items():require(record(a.out/name)==row,'The already completed link/source differs; do not reuse it')
    for row in frozen:require(record(row['path'])==row,'An active source changed during the packed-source relink')
    historical=[]
    replacements={str(ROOT/'native/app/expert_q2_receipt.h'):ROOT/'.local/expert_q2_receipt_8170.snapshot.h',
        str(ROOT/'native/app/expert_q2_source_integrity.h'):ROOT/'.local/expert_q2_source_integrity_8170.snapshot.h'}
    for row in prior['inputs_before']:
        path=replacements.get(str(Path(row['path'])))
        if path and record(row['path'])!=row:
            saved=record(path);require((saved['bytes'],saved['sha256'])==(row['bytes'],row['sha256']),'An exact historical source snapshot is required');historical.append(saved)
        else:historical.append(row)
    result=copy.deepcopy(prior);result.update(artifact=record(image),compile_commands=[commands[0]],link_command=link,source_parent=record(a.parent),
        inputs_before=historical+frozen+[record(x)for x in objects],
        lossless_driver_table_geometry=audit_linked_storage(image,prior['lossless_driver_tables']))
    result['expert_q2_model'].update(actual_entry=record(entry),packed_source_scope=PACKED_SCOPE,
        source_owner=record(source),reader_header=record(derived),packed_source_commands=commands,
        GPU_math_and_provider_objects_unchanged=True,packed_source_model_validation_pending=True)
    if metadata_details:result['expert_q2_model']['complete_prefix_metadata']=metadata_details
    if a.finalize_existing:result['completed_compile_generator_snapshot']=record(ROOT/'.local/build_expert_q2_composite_8242.snapshot.py')
    write_json(a.out/'receipt.private.json',result)
    result['real_module_import_audit']=audit(a.workspace,a.cache,a.out)
    result['native_dispatch_audit']=dispatch(a.workspace,a.workspace/'driver-work/PS5-Vulkan-Inference-qwen-872cc126',image,a.out/'dispatch')
    require(not result['real_module_import_audit']['missing']and result['native_dispatch_audit']['passed'],'Packed-source native import/dispatch audit failed')
    write_json(a.out/'receipt.private.json',result)
    print(json.dumps(dict(packed_source_native_build_complete=True,PS5_operations=0,CI_runs=0)),flush=True)
if __name__=='__main__':main()
