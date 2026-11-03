#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reuse a native CPU startup only for one exact GPU-only boundary insertion."""
import argparse
from collections import Counter
import json
from pathlib import Path
import struct

from build_performance_quantizer import record
from native_dispatch import ELF
from price_unloaded_iq2_startup import initializer_count
from run_native_paired_down import geometry
from start_success_route import load,need,save


def function_proof(path,name):
    elf=ELF(path);symbol=elf.symbols[name];section=symbol['section'];need(symbol['size']>0,'A complete actual function required')
    names_index=struct.unpack_from('<H',elf.data,62)[0];labels=elf.section_data(elf.sections[names_index])
    label=lambda index:labels[elf.sections[index][0]:labels.index(0,elf.sections[index][0])].decode()
    tables={}
    for index,h in enumerate(elf.sections):
        if h[1]!=2:continue
        strings=elf.section_data(elf.sections[h[6]]);rows=[]
        for at in range(h[4],h[4]+h[5],24):
            offset,info,other,part,value,size=struct.unpack_from('<IBBHQQ',elf.data,at)
            text=strings[offset:strings.index(0,offset)].decode()
            rows.append((text if text else (label(part) if 0<part<len(elf.sections) else ''),value))
        tables[index]=rows
    relocations=[]
    for h in elf.sections:
        if h[1]!=4 or h[7]!=section:continue
        for at in range(h[4],h[4]+h[5],24):
            address,info,addend=struct.unpack_from('<QQq',elf.data,at)
            if symbol['value']<=address<symbol['value']+symbol['size']:
                target,value=tables[h[6]][info>>32]
                relocations.append((address-symbol['value'],info&0xffffffff,target,value+addend))
    return dict(code_hex=elf.symbol_data(name).hex(),relocations=relocations)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('startup','package','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();done=load(a.startup)
    need(done['completed'] and done['mode']=='CPU' and done['native_passed'] and done['ordinary_exit_observed'] and
         done['current_seven_restored_and_native_hashed'],'A positively closed completed CPU startup is required')
    old_package=load(done['package']['path']);new_package=load(a.package)
    need(record(done['package']['path'])==done['package'],'The original CPU package changed')
    old,new=load(old_package['relink']['path']),load(new_package['relink']['path'])
    for package,relink in ((old_package,old),(new_package,new)):
        need(package['completed'] and package['normalized_SELF_roundtrip_equal'] and relink['completed'] and
             record(relink['artifact']['path'])==relink['artifact'],'An actual complete linked native image required')
    old_text=Path(old['source']['path']).read_text();new_text=Path(new['source']['path']).read_text()
    marker='shader.at("workgroup"),result);valid=valid'
    need(old_text.count(marker)==1 and new_text==old_text.replace(marker,
        'shader.at("workgroup"),result);qwen_native_driver_checkpoint();valid=valid'),
        'The sole source change must be the completed GPU case checkpoint')
    def controlled(relink):
        return Counter((Path(r['path']).name,r['bytes'],r['sha256']) for r in relink['inputs_before']
            if Path(r['path']).name not in ('builder.private.py','paired-down-native.private.cpp'))
    need(controlled(old)==controlled(new),'A CPU, runtime, driver, reference, manifest or pack input changed')
    need(old['real_module_import_audit']['resolved']==new['real_module_import_audit']['resolved'] and
         old['component_pack']['local']['sha256']==new['component_pack']['local']['sha256'],
         'Exact native ABI and immutable component bytes required')
    old_command,new_command=old['commands'][0],new['commands'][0]
    old_root=Path(old['source']['path']).parent;new_root=Path(new['source']['path']).parent
    need([x.replace(str(old_root),'BUILD') for x in old_command]==[x.replace(str(new_root),'BUILD') for x in new_command],
         'Actual target CPU compile options must remain unchanged')
    old_object=old_root/'component.o';new_object=new_root/'component.o'
    names=[name for name in ELF(old_object).symbols if name=='main' or 'native_guard' in name or
           'native_save' in name or name.startswith('_GLOBAL__sub_I_')]
    need('main' in names and len(names)>=3,'Main and actual CPU helper/constructor functions required')
    functions=[]
    for name in names:
        need(function_proof(old_object,name)==function_proof(new_object,name),'CPU machine code or normalized relocation changed: '+name)
        functions.append(name)
    need(record(old_root/'integrity.o')['sha256']==record(new_root/'integrity.o')['sha256'] and
         record(old_root/'sha256.o')['sha256']==record(new_root/'sha256.o')['sha256'],
         'The complete actual C integrity and SHA256 objects must remain byte identical')
    need(initializer_count(old_package)==initializer_count(new_package),'Constructor count changed')
    before,after=geometry(old_package),geometry(new_package)
    added=max(0,after['file_pages']-before['file_pages'])+max(0,after['zero_pages']-before['zero_pages'])
    a.out.mkdir(parents=True,exist_ok=False)
    save(a.out/'result.private.json',dict(completed=True,startup=record(a.startup),old_package=done['package'],
        new_package=record(a.package),GPU_only_completed_case_checkpoint_insertion=True,
        actual_CPU_functions_and_normalized_relocations_equal=functions,actual_C_reader_and_hash_objects_byte_exact=True,
        constructors=initializer_count(new_package),additional_ELF_pages_priced=added,
        original_CPU_native_execution_reused_without_replay=True,PS5_operations=0,native_GPU_qualified=False))
    print(json.dumps(dict(completed=True,CPU_functions=len(functions),additional_ELF_pages_priced=added,
                          CPU_native_replays=0,PS5_operations=0)))


if __name__=='__main__':main()
