#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exclude an exclusive zero-backed tail from an RW LOAD without changing code."""
import struct
from external_rodata_layout import headers


def exclude(raw,begin,end):
    offset,rows=headers(raw)
    if not begin or begin%65536 or end<=begin or end%65536 or end-begin>16<<20:
        raise ValueError('One exact64KiB-aligned owned zero range is required')
    candidates=[(i,h) for i,h in enumerate(rows) if h[0]==1 and h[1]==6 and
        h[3]+h[5]<=begin and h[3]<begin and h[3]+h[6]==end]
    if len(candidates)!=1:raise ValueError('One non-executable original zero tail must contain the whole range')
    index,selected=candidates[0]
    shoff=struct.unpack_from('<Q',raw,40)[0];stride,count,strings_index=struct.unpack_from('<HHH',raw,58)
    if stride!=64:raise ValueError('Original section metadata required')
    sections=[struct.unpack_from('<IIQQQQIIQQ',raw,shoff+i*stride) for i in range(count)]
    tab=sections[strings_index];names=raw[tab[4]:tab[4]+tab[5]];owned=[]
    for section in sections:
        if section[1]==4:
            if section[9]!=24 or section[5]%24:raise ValueError('Original RELA geometry required')
            for at in range(section[4],section[4]+section[5],24):
                location=struct.unpack_from('<Q',raw,at)[0]
                if location<end and begin<location+8:raise ValueError('A relocation writes inside the zero hole')
        if section[2]&2 and section[5] and section[3]<end and begin<section[3]+section[5]:
            name=names[section[0]:names.index(0,section[0])].decode()
            if section[1]!=8 or section[2]!=3 or name not in ('.qwen_driver_tables','.qwen_early_padding') or not (
                begin<=section[3] and section[3]+section[5]<=end):raise ValueError('Another allocated section intersects the exclusive zero range')
            owned.append((section[3],section[3]+section[5],name))
    owned.sort()
    if not owned or owned[0][0]!=begin or owned[-1][1]!=end or any(a[1]!=b[0] for a,b in zip(owned,owned[1:])):
        raise ValueError('The exact two zero sections must cover the complete removed tail')
    changed=bytearray(raw);struct.pack_into('<Q',changed,offset+index*56+40,begin-selected[3])
    allowed=set(range(offset+index*56+40,offset+index*56+48))
    if any(a!=b and i not in allowed for i,(a,b) in enumerate(zip(raw,changed))):raise ValueError('Non-header bytes changed')
    return bytes(changed),dict(begin=begin,end=end,bytes=end-begin,original_zero_sections=owned,
        original_program=selected,only_original_RW_memsz_changed=True,removed_relocation_locations=0,
        original_file_backed_bytes_code_and_relocations_exact=True,source_payload_bytes=0)


def exclude_converted(raw,begin,end):
    if raw[:7]!=b'\x7fELF\x02\x01\x01' or not begin or begin%65536 or end<=begin or end%65536:
        raise ValueError('Exact converted ELF and exclusive CPU zero geometry required')
    at=struct.unpack_from('<Q',raw,32)[0];stride,count=struct.unpack_from('<HH',raw,54)
    if stride!=56 or not 0<count<64:raise ValueError('Complete converted ELF64 program headers required')
    rows=[struct.unpack_from('<IIQQQQQQ',raw,at+i*stride) for i in range(count)]
    found=[(i,h) for i,h in enumerate(rows) if h[0]==1 and h[1]==6 and h[3]+h[5]<=begin and h[3]<begin and h[3]+h[6]==end]
    if len(found)!=1:raise ValueError('One original converted writable zero tail must cover the complete owned range')
    index,selected=found[0]
    if any(i!=index and h[0]==1 and h[3]<end and begin<h[3]+h[6] for i,h in enumerate(rows)):
        raise ValueError('Other converted LOAD data intersects the exclusive zero tail')
    output=bytearray(raw);struct.pack_into('<Q',output,at+index*stride+40,begin-selected[3])
    allowed=set(range(at+index*stride+40,at+index*stride+48))
    if any(a!=b and i not in allowed for i,(a,b) in enumerate(zip(raw,output))):raise ValueError('Converted data outside memsz changed')
    return bytes(output),dict(begin=begin,end=end,bytes=end-begin,original_program=selected,
        only_converted_RW_memsz_changed=True,all_code_data_dynamic_metadata_and_relative_relocations_byte_exact=True,
        generated_metadata_beyond_owned_zero_range=True)
