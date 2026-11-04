#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise actual ELF page exclusion and its scope/relocation refusals."""
import argparse
import json
from pathlib import Path
import struct
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from external_rodata_layout import externalize,headers
from native_dispatch import ELF


def main():
    p=argparse.ArgumentParser();p.add_argument('--image',type=Path,required=True)
    p.add_argument('--payload',type=Path,required=True);a=p.parse_args()
    elf=ELF(a.image);raw=elf.data;payload=a.payload.read_bytes()
    begin=elf.symbols['qwen_cold_payload']['value'];size=len(payload)
    at,rows=headers(raw);index=next(i for i,h in enumerate(rows) if h[0]==1 and h[3]<=begin<h[3]+h[5])
    _,tail=externalize(raw,begin,size,payload)
    _,interior=externalize(raw,begin+16384,32768,payload[16384:49152])
    assert tail['original_loaded_bytes_reconstructed_exactly'] and interior['original_loaded_bytes_reconstructed_exactly']
    def mutate(offset,fmt,value):
        changed=bytearray(raw);struct.pack_into(fmt,changed,offset,value);return bytes(changed)
    shoff=struct.unpack_from('<Q',raw,40)[0]
    section=elf.symbols['qwen_cold_payload']['section']
    relocation=next(s for s in elf.sections if s[1]==4 and s[5])
    cases=[(raw,begin+1,size,payload),(raw,begin,size-1,payload[:-1]),
        (raw,begin,size,payload[:-1]),(raw,begin,size,b'x'+payload[1:]),
        (mutate(at+index*56+4,'<I',6),begin,size,payload),
        (mutate(at+index*56+4,'<I',5),begin,size,payload),
        (mutate(at+index*56+40,'<Q',size-16384),begin,size,payload),
        (mutate(at+index*56+48,'<Q',rows[index][6]+16384),begin,size,payload),
        (mutate(at+index*56+56-8,'<Q',4096),begin,size,payload),
        (mutate(relocation[4],'<Q',begin+8),begin,size,payload),
        (mutate(shoff+section*64+8,'<Q',3),begin,size,payload),
        (raw,begin+size,size,payload)]
    for i,case in enumerate(cases):
        try:externalize(*case)
        except ValueError:pass
        else:raise AssertionError('Unsafe ELF scope accepted: '+str(i))
    print(json.dumps(dict(positive_real_ELF_layouts=2,negative_scope_controls=len(cases),PS5_operations=0)))


if __name__=='__main__':main()
