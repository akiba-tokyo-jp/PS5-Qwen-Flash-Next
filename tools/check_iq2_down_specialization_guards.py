#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise new refusal boundaries without replaying the completed array patch."""
import argparse
import copy
from pathlib import Path
import struct
from build_performance_quantizer import record
from iq2_down_specialization_arrays import patch_registry
from native_dispatch import ELF
from start_success_route import load,need,save


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('current','provider','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();provider=load(a.provider);audit=load(provider['specialization_array_audit']['path'])
    need(provider['completed'] and audit['completed'] and audit['all_other_original_bytes_exact'] and
         record(provider['specialization_array_audit']['path'])==provider['specialization_array_audit'],
         'Reuse the already completed actual nine-pair positive patch')
    original=provider['selected_shader_registry'];need(record(original['path'])=={k:original[k] for k in ('path','bytes','sha256')},
        'The original selected registry must remain immutable')
    raw=Path(original['path']).read_bytes();native=ELF(a.current/'provenance/qwen-native.pie.elf')
    shaders=load(provider['shaders']['path'])['shaders'];targets={}
    for row in shaders:
        stored=struct.unpack('<8sQII',native.symbol_data(row['name']+'_data'))[2]
        targets[row['name']]=dict(replacement='qwen_iq2_down_'+row['name'],original_stored_bytes=stored,
            replacement_bytes=row['artifact']['bytes'])
    metadata=load(a.current/'provenance/native-link.receipt.private.json')['lossless_shader_storage']['lookup_tables']
    selected=next(x for x in metadata if x['name']==audit['array_pointer_length_pairs'][0]['array'])
    first=audit['array_pointer_length_pairs'][0];a.out.mkdir(parents=True,exist_ok=False);results=[]
    for fault in range(9):
        malformed=bytearray(raw);tables=copy.deepcopy(metadata);mapping=copy.deepcopy(targets)
        if fault==0:malformed[0]=0
        elif fault==1:next(x for x in tables if x['name']==selected['name'])['dimensions']=[4]
        elif fault==2:del mapping[first['shader']]
        elif fault==3:mapping[first['shader']]['original_stored_bytes']+=1
        elif fault==4:struct.pack_into('<Q',malformed,first['length_field'],1)
        elif fault==5:
            at=first['relocation_field'];value=struct.unpack_from('<Q',malformed,at)[0]
            struct.pack_into('<Q',malformed,at,(value&~0xffffffff)|2)
        elif fault==6:struct.pack_into('<q',malformed,first['relocation_field']+8,8)
        elif fault==7:
            table=next(x for x in tables if x['name']==selected['name']);table['targets'][0],table['targets'][1]=table['targets'][1],table['targets'][0]
        else:tables=[x for x in tables if x['name']!=selected['name']]
        source=a.out/(str(fault)+'.malformed.o');source.write_bytes(malformed);destination=a.out/(str(fault)+'.must-not-exist.o')
        try:patch_registry(source,destination,mapping,tables)
        except (RuntimeError,ValueError,KeyError,struct.error) as error:
            need(not destination.exists(),'A refused transformation must not publish a partial object')
            results.append(dict(fault=fault,input=record(source),refused=True,partial_output=False,reason=str(error)))
        else:raise RuntimeError('Malformed specialization input was admitted')
    save(a.out/'result.private.json',dict(completed=True,new_negative_boundaries=9,results=results,
        completed_actual_positive_patch_reused=record(a.provider),positive_patch_replayed=False,PS5_operations=0))
    print(dict(completed=True,new_negative_boundaries=9,positive_patch_replayed=False,PS5_operations=0))


if __name__=='__main__':main()
