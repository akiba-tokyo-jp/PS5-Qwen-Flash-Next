#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Patch only matvec array relocations/lengths; preserve the codec registry."""
import struct
from pathlib import Path
from start_success_route import need


def patch_registry(source, destination, targets, lookup_tables):
    original=Path(source).read_bytes();data=bytearray(original)
    need(data[:6]==b'\x7fELF\x02\x01' and struct.unpack_from('<H',data,16)[0]==1,'ELF64 little-endian relocatable registry required')
    offset=struct.unpack_from('<Q',data,40)[0];stride,count=struct.unpack_from('<HH',data,58)
    need(stride==64 and offset+count*64<=len(data),'Complete original section headers required')
    sections=[list(struct.unpack_from('<IIQQQQIIQQ',data,offset+i*64)) for i in range(count)]
    tables=[i for i,s in enumerate(sections) if s[1]==2];need(len(tables)==1,'One exact registry symbol table required')
    si=tables[0];symtab=sections[si];sti=symtab[6];strings=bytearray(data[sections[sti][4]:sections[sti][4]+sections[sti][5]])
    symbols=bytearray(data[symtab[4]:symtab[4]+symtab[5]]);need(symtab[9]==24 and len(symbols)%24==0,'Complete ELF64 symbols required')
    def name(at):
        end=strings.find(b'\0',at);need(end>=at,'Terminated symbol name required');return bytes(strings[at:end]).decode()
    rows=[]
    for at in range(0,len(symbols),24):
        n,info,other,section,value,size=struct.unpack_from('<IBBHQQ',symbols,at)
        rows.append(dict(name=name(n),section=section,value=value,size=size))
    defined={r['name']:r for r in rows if r['section']};new_indices={};changes=[];allowed=[]
    def change(at,raw):
        need(0<=at<=len(original)-len(raw),'Only bounded existing fields may change')
        allowed.append((at,at+len(raw)));data[at:at+len(raw)]=raw
    def external(shader):
        symbol=targets[shader]['replacement']+'_data'
        if symbol not in new_indices:
            need(symbol not in defined,'A replacement definition must come from its separate qualified data object')
            at=len(strings);strings.extend(symbol.encode()+b'\0');new_indices[symbol]=len(symbols)//24
            symbols.extend(struct.pack('<IBBHQQ',at,0x11,0,0,0,0))
        return new_indices[symbol]
    selected=[x for x in lookup_tables if x['name'] in
        ('arr_dmmv_q2_0_f32_f32','arr_dmmv_q2_0_f16_f32','arr_dmmv_id_q2_0_f32_f32')]
    need(len(selected)==3,'Three original selected matvec arrays required')
    for table in selected:
        array,length=defined[table['name']+'_data'],defined[table['name']+'_len']
        need(table['dimensions']==[3] and array['size']==length['size']==24 and
             sections[array['section']][1]==sections[length['section']][1]==1,
             'Three literal lengths and three existing pointer relocations required')
        seen=set()
        for section in sections:
            if section[1]!=4 or section[6]!=si or section[7]!=array['section']:continue
            need(section[9]==24,'ELF64 RELA records required')
            for at in range(section[4],section[4]+section[5],24):
                target,info,addend=struct.unpack_from('<QQq',data,at)
                if not array['value']<=target<array['value']+array['size']:continue
                index=(target-array['value'])//8;shader=rows[info>>32]['name']
                need((target-array['value'])%8==0 and index<3 and index not in seen and
                     info&0xffffffff==1 and addend==0 and shader==table['targets'][index]+'_data',
                     'Each original exact64-bit shader pointer must bind its declared array position')
                key=table['targets'][index];need(key in targets,'Every selected variant needs a qualified replacement')
                length_at=sections[length['section']][4]+length['value']+index*8
                previous=struct.unpack_from('<Q',data,length_at)[0]
                need(previous==targets[key]['original_stored_bytes'],'The existing literal compressed length differs')
                change(at+8,struct.pack('<Q',(external(key)<<32)|1))
                change(length_at,struct.pack('<Q',targets[key]['replacement_bytes']));seen.add(index)
                changes.append(dict(array=table['name'],index=index,shader=key,old_stored_bytes=previous,
                    new_bytes=targets[key]['replacement_bytes'],relocation_field=at+8,length_field=length_at))
        need(seen=={0,1,2},'All three variants must be replaced exactly once')
    need(len(changes)==len(new_indices)==9,'Nine selected pointer/length pairs required')
    for index,blob in ((sti,strings),(si,symbols)):
        data.extend(bytes((-len(data))%8));begin=len(data);data.extend(blob)
        change(offset+index*64+24,struct.pack('<Q',begin));change(offset+index*64+32,struct.pack('<Q',len(blob)))
    need(all(a==b or any(start<=i<end for start,end in allowed) for i,(a,b) in enumerate(zip(original,data))),
         'A byte outside the declared array fields and symbol/string-table headers changed')
    Path(destination).write_bytes(data)
    return dict(completed=True,array_pointer_length_pairs=changes,added_undefined_symbols=9,
        all_other_original_bytes_exact=True,original_codec_registry_entries_and_relocations_unchanged=True,
        appended_symbol_and_string_tables=True,new_executable_bytes=0)
