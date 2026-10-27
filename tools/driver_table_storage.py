#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Lossless storage for relocation-free NIR constants; never edits the donor."""
import hashlib,json,struct,subprocess,zlib
from pathlib import Path
from shader_storage import archive_members,record
MEMBER='meson-generated_.._nir_opt_algebraic.c.o'
SCHEMA='ps5-qwen-cold-driver-tables-v1'

def sections(raw):
    if raw[:6]!=b'\x7fELF\x02\x01' or struct.unpack_from('<HH',raw,16)!=(1,62):
        raise ValueError('An x86-64 ELF64 relocatable object is required')
    at=struct.unpack_from('<Q',raw,40)[0];stride,count,names=struct.unpack_from('<HHH',raw,58)
    if stride!=64 or not count or at+count*stride>len(raw) or names>=count:
        raise ValueError('Invalid section table')
    entries=[struct.unpack_from('<IIQQQQIIQQ',raw,at+i*stride)for i in range(count)]
    tab=entries[names];strings=raw[tab[4]:tab[4]+tab[5]];result=[]
    for i,e in enumerate(entries):
        if e[1]!=8 and e[4]+e[5]>len(raw):raise ValueError('Truncated section')
        name=strings[e[0]:strings.index(0,e[0])].decode()
        result.append(dict(index=i,name=name,type=e[1],flags=e[2],bytes=e[5],info=e[7],alignment=e[8],
            data=b''if e[1]==8 else raw[e[4]:e[4]+e[5]]))
    return result

def selected(raw):
    items=sections(raw);targets={s['info']for s in items if s['type']in(4,9)}
    return [s for s in items if s['type']==1 and s['flags']==2 and s['name'].startswith('.rodata')
            and s['bytes'] and s['index']not in targets]

def verify_object(original,modified,rows):
    old,new=sections(original),sections(modified)
    if len(old)!=len(new):raise ValueError('Section identities changed')
    chosen={r['index']:r for r in rows}
    for a,b in zip(old,new):
        r=chosen.get(a['index'])
        if r:
            if b['name']!=r['new_section'] or b['type']!=8 or b['flags']!=3 or b['bytes']!=a['bytes'] or b['alignment']!=a['alignment']:
                raise ValueError('Cold storage changed its exact object span')
        elif a['name']not in('.strtab','.shstrtab','.symtab'):
            # COMDAT metadata may repeat names. Compare section indices, never a name-keyed dict.
            if any(a[k]!=b[k]for k in('name','type','flags','bytes','info','alignment','data')):
                raise ValueError('Untouched code, relocation or metadata changed: '+str(a['index']))

def write_archive(path,members):
    data=bytearray(b'!<arch>\n')
    # GNU long names retain duplicate member occurrences and their exact order.
    names=bytearray();offsets={}
    for name,_ in members:
        if name not in offsets:offsets[name]=len(names);names.extend(name.encode()+b'/\n')
    for name,payload in [('//',bytes(names)),*[('/'+str(offsets[n]),b)for n,b in members]]:
        fields=[name.ljust(16),'0'.ljust(12),'0'.ljust(6),'0'.ljust(6),'100644'.ljust(8),str(len(payload)).ljust(10),'`\n']
        header=''.join(fields).encode()
        if len(header)!=60:raise ValueError('Archive header overflow')
        data.extend(header);data.extend(payload)
        if len(payload)%2:data.extend(b'\n')
    Path(path).write_bytes(data)

def build(archive,expected_sha,llvm,out):
    archive,llvm,out=Path(archive),Path(llvm),Path(out)
    if record(archive)['sha256']!=expected_sha:raise ValueError('The pinned native driver changed')
    out.mkdir(parents=True,exist_ok=False)
    original=list(archive_members(archive));matches=[i for i,(n,_)in enumerate(original)if n==MEMBER]
    if len(matches)!=1:raise ValueError('The NIR donor member must be unique')
    index=matches[0];raw=original[index][1];items=selected(raw)
    if not items or len(items)>1024:raise ValueError('No bounded relocation-free table set')
    (out/'original-nir.o').write_bytes(raw);pool=bytearray();rows=[];rename=[];change=[]
    for i,s in enumerate(items):
        if s['alignment']>16384 or s['alignment']&(s['alignment']-1):raise ValueError('Invalid original alignment')
        name=f'.qwen_cold_table_{i:04}';symbol=f'qwen_driver_table_{i:04}';packed=zlib.compress(s['data'],9)
        if zlib.decompress(packed)!=s['data']:raise ValueError('Lossless roundtrip failed')
        rows.append(dict(index=s['index'],original_section=s['name'],new_section=name,symbol=symbol,
            bytes=s['bytes'],alignment=s['alignment'],sha256=hashlib.sha256(s['data']).hexdigest(),offset=len(pool),packed_bytes=len(packed)))
        pool.extend(packed)
        rename+=['--rename-section='+s['name']+'='+name+',alloc']
        change+=['--set-section-type='+name+'=8','--add-symbol='+symbol+'='+name+':0,global,object']
    for i,args in enumerate((rename+[str(out/'original-nir.o'),str(out/'renamed-nir.o')],change+[str(out/'renamed-nir.o'),str(out/'cold-nir.o')])):
        response=out/f'objcopy-{i}.rsp';response.write_text('\n'.join(json.dumps(v)for v in args)+'\n',newline='\n')
        command=[str(llvm/'llvm-objcopy.exe'),'@'+str(response)];r=subprocess.run(command,capture_output=True,timeout=120)
        (out/f'objcopy-{i}.private.log').write_bytes(r.stdout+r.stderr)
        if r.returncode:raise ValueError(r.stderr.decode(errors='replace'))
    cold=(out/'cold-nir.o').read_bytes();verify_object(raw,cold,rows)
    replacement=list(original);replacement[index]=(MEMBER,cold);overlay=out/'libvulkan-cold-tables.a'
    write_archive(overlay,replacement)
    r=subprocess.run([str(llvm/'llvm-ranlib.exe'),str(overlay)],capture_output=True,timeout=120)
    (out/'ranlib.private.log').write_bytes(r.stdout+r.stderr)
    if r.returncode or list(archive_members(overlay))!=replacement:raise ValueError('Archive occurrence preservation failed')
    (out/'tables.deflate.bin').write_bytes(pool)
    assembly='.section .rodata.qwen_nir_packed,"a",@progbits\n.global qwen_driver_table_packed\nqwen_driver_table_packed:\n.incbin '+json.dumps((out/'tables.deflate.bin').as_posix())+'\n.section .note.GNU-stack,"",@progbits\n'
    (out/'tables.S').write_text(assembly,newline='\n')
    registry='#include "driver_tables.h"\nextern "C" const unsigned char qwen_driver_table_packed[];\n'
    for r in rows:registry+='extern "C" unsigned char '+r['symbol']+'[];\n'
    registry+='static const qwen_driver_table tables[]={\n'
    for r in rows:
        registry+='{'+r['symbol']+','+','.join(str(r[k])for k in('bytes','offset','packed_bytes'))+',{'+','.join(str(b)for b in bytes.fromhex(r['sha256']))+'}},\n'
    registry+='};\nextern "C" unsigned char __qwen_driver_tables_start[],__qwen_driver_tables_end[];\n'
    registry+='extern "C" const qwen_driver_table_plan qwen_driver_table_storage={tables,'+str(len(rows))+',qwen_driver_table_packed,'+str(len(pool))+',__qwen_driver_tables_start,__qwen_driver_tables_end};\n'
    (out/'registry.cpp').write_text(registry,newline='\n')
    script='SECTIONS { .qwen_driver_tables (NOLOAD) : ALIGN(16384) { __qwen_driver_tables_start = .; KEEP(*(.qwen_cold_table_*)) . = ALIGN(16384); __qwen_driver_tables_end = .; } } INSERT BEFORE .bss;\n'
    (out/'tables.ld').write_text(script,newline='\n')
    result=dict(schema=SCHEMA,state='offline_storage_verified_not_native_qualified',source_archive=record(archive),
        archive=record(overlay),source_member=MEMBER,source_member_sha256=hashlib.sha256(raw).hexdigest(),
        cold_member=record(out/'cold-nir.o'),pool=record(out/'tables.deflate.bin'),assembly=record(out/'tables.S'),
        registry=record(out/'registry.cpp'),linker_script=record(out/'tables.ld'),tables=rows,
        original_table_bytes=sum(r['bytes']for r in rows),packed_bytes=len(pool),
        untouched_member_occurrences_verified=len(original)-1,code_and_relocations_byte_exact=True,
        readonly_table_relocations=0,source_archive_changed=False,PS5_operations=0)
    (out/'receipt.private.json').write_text(json.dumps(result,indent=2)+'\n')
    return result

def validate(path,donor):
    m=json.loads(Path(path).read_text())
    if m.get('schema')=='ps5-qwen-cold-driver-tables-v2':
        from driver_table_storage_extension import validate as validate_extension
        return validate_extension(path,donor)
    if m.get('schema')!=SCHEMA or m.get('source_archive')!=record(donor):raise ValueError('Wrong table donor')
    for k in('source_archive','archive','cold_member','pool','assembly','registry','linker_script'):
        if record(m[k]['path'])!=m[k]:raise ValueError('Cold table input changed: '+k)
    a,b=list(archive_members(donor)),list(archive_members(m['archive']['path']))
    if len(a)!=len(b):raise ValueError('Archive member count changed')
    count=0
    for old,new in zip(a,b):
        if old[0]==MEMBER and new[0]==MEMBER:verify_object(old[1],new[1],m['tables']);count+=1
        elif old!=new:raise ValueError('Untouched archive member changed')
    if count!=1:raise ValueError('NIR member identity changed')
    return m

def audit_linked_storage(image,manifest):
    """Check real relocated plan pointers and exclusive NOBITS geometry."""
    from native_dispatch import ELF
    elf=ELF(Path(image));rows=manifest['tables'];symbols=elf.symbols
    begin=symbols['__qwen_driver_tables_start']['value'];end=symbols['__qwen_driver_tables_end']['value']
    if not begin or end<=begin or begin%16384 or end%16384 or end-begin>16<<20:
        raise ValueError('Empty or malformed linked driver table range')
    plan=symbols['qwen_driver_table_storage']
    if plan['size']!=48:raise ValueError('Unexpected actual native plan ABI')
    values=[elf.pointer(plan['value']+8*i)for i in range(6)]
    tables,count,packed,packed_bytes,actual_begin,actual_end=values
    if count!=len(rows)or packed_bytes!=manifest['packed_bytes']or (actual_begin,actual_end)!=(begin,end):
        raise ValueError('Actual relocated plan bounds or counters differ')
    def read(at,n):
        for s in elf.sections:
            if s[1]!=8 and s[3]<=at and at+n<=s[3]+s[5]:return elf.read(s[4]+at-s[3],n)
        raise ValueError('Required table metadata is not file backed')
    if packed!=symbols['qwen_driver_table_packed']['value']or hashlib.sha256(read(packed,packed_bytes)).hexdigest()!=manifest['pool']['sha256']:
        raise ValueError('Actual linked compressed bytes changed')
    intervals=[];section_index=None
    for i,row in enumerate(rows):
        at=tables+i*64;target=elf.pointer(at);size,offset,stored=struct.unpack('<QQQ',read(at+8,24))
        symbol=symbols[row['symbol']];s=elf.sections[symbol['section']]
        if(target!=symbol['value']or not begin<=target<end or size>end-target or size!=row['bytes']or
           offset!=row['offset']or stored!=row['packed_bytes']or read(at+32,32).hex()!=row['sha256']or
           s[1]!=8 or s[2]&3!=3 or s[3]!=begin or s[5]!=end-begin):
            raise ValueError('A real linked target, hash or exclusive NOBITS section differs: '+str(i))
        if section_index is None:section_index=symbol['section']
        if symbol['section']!=section_index:raise ValueError('Table targets span another output section')
        intervals.append((target,target+size))
    intervals.sort()
    if any(a[1]>b[0]for a,b in zip(intervals,intervals[1:])):raise ValueError('Real table destinations overlap')
    phoff=struct.unpack_from('<Q',elf.data,32)[0];stride,num=struct.unpack_from('<HH',elf.data,54);cover=[]
    for i in range(num):
        kind,flags,offset,vaddr,paddr,filesz,memsz,align=struct.unpack_from('<IIQQQQQQ',elf.data,phoff+i*stride)
        if kind==1 and vaddr<=begin<end<=vaddr+memsz:cover.append((flags,vaddr+filesz))
    if len(cover)!=1 or cover[0][0]&7!=6 or cover[0][1]>begin:
        raise ValueError('The exclusive table range requires a non-executable writable NOBITS load segment')
    return dict(passed=True,table_count=len(rows),exclusive_NOBITS_bytes=end-begin,
        all_actual_relocated_targets_and_hashes_verified=True,actual_linked_pool_SHA256=manifest['pool']['sha256'],
        original_code_and_relocations_unchanged=True,image_SHA256=record(image)['sha256'])

def audit_converted_storage(image,converted,manifest):
    """Check loader-visible data and every critical relative relocation.

    The pinned converter normalizes executable flags and moves generic dynamic
    metadata. Compare the actual cold-data contract rather than requiring those
    unrelated load segments to keep their original geometry.
    """
    from native_dispatch import ELF
    geometry=audit_linked_storage(image,manifest);elf=ELF(Path(image));raw=Path(converted).read_bytes()
    if len(raw)<64 or raw[:6]!=b'\x7fELF\x02\x01':raise ValueError('A complete converted ELF64 module is required')
    off=struct.unpack_from('<Q',raw,32)[0];stride,count=struct.unpack_from('<HH',raw,54)
    if stride!=56 or not 0<count<=4096 or off+stride*count>len(raw):raise ValueError('Invalid converted program table')
    programs=[struct.unpack_from('<IIQQQQQQ',raw,off+i*stride)for i in range(count)]
    loads=[p for p in programs if p[0]==1]
    def read(at,n):
        for t,f,o,v,pa,fs,ms,al in loads:
            if v<=at and at+n<=v+fs and o+at-v+n<=len(raw):return raw[o+at-v:o+at-v+n]
        raise ValueError('Required converted table metadata is not file backed')
    dynamic=[p for p in programs if p[0]==2]
    if len(dynamic)!=1 or dynamic[0][5]%16 or dynamic[0][2]+dynamic[0][5]>len(raw):raise ValueError('One bounded converted dynamic table is required')
    d=dynamic[0];entries=[struct.unpack_from('<qQ',raw,d[2]+i)for i in range(0,d[5],16)]
    if any(sum(k==key for k,v in entries)!=1 for key in(7,8,9)):raise ValueError('The pinned ordinary RELA metadata is required')
    tags=dict(entries)
    if tags[9]!=24 or tags[8]%24 or tags[8]>16<<20:raise ValueError('Converted relative relocations exceed their bounded ABI')
    relas=[struct.unpack('<QQq',read(tags[7]+i,24))for i in range(0,tags[8],24)]
    relative={at:add for at,info,add in relas if info==8}
    begin=elf.symbols['__qwen_driver_tables_start']['value'];end=elf.symbols['__qwen_driver_tables_end']['value']
    cover=[p for p in loads if p[3]<=begin<end<=p[3]+p[6]]
    if len(cover)!=1 or cover[0][1]&7!=6 or cover[0][3]+cover[0][5]>begin:
        raise ValueError('Conversion changed exclusive writable NOBITS table coverage')
    plan=elf.symbols['qwen_driver_table_storage']['value'];tables=elf.pointer(plan);packed=elf.pointer(plan+16)
    if hashlib.sha256(read(packed,manifest['packed_bytes'])).hexdigest()!=manifest['pool']['sha256']:
        raise ValueError('Conversion changed exact embedded compressed bytes')
    critical=[plan+i for i in(0,16,32,40)]+[tables+64*i for i in range(len(manifest['tables']))]
    if any(at not in relative or relative[at]!=elf.pointer(at)for at in critical):raise ValueError('A converted relative table pointer changed')
    if(struct.unpack('<Q',read(plan+8,8))[0]!=len(manifest['tables'])or
       struct.unpack('<Q',read(plan+24,8))[0]!=manifest['packed_bytes']):raise ValueError('Converted plan counters changed')
    for i,row in enumerate(manifest['tables']):
        data=read(tables+64*i+8,56)
        if struct.unpack('<QQQ',data[:24])!=(row['bytes'],row['offset'],row['packed_bytes'])or data[24:].hex()!=row['sha256']:
            raise ValueError('A converted table size, offset or original hash changed')
    return dict(passed=True,critical_relative_pointers=len(critical),table_count=len(manifest['tables']),
        exclusive_NOBITS_bytes=geometry['exclusive_NOBITS_bytes'],all_converted_scalars_hashes_and_pool_exact=True,
        image_SHA256=record(image)['sha256'],converted_SHA256=record(converted)['sha256'])

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    for name in('archive','llvm','out'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--expected-sha256',required=True);a=p.parse_args()
    m=build(a.archive,a.expected_sha256,a.llvm,a.out)
    print(json.dumps({k:m[k]for k in('original_table_bytes','packed_bytes','untouched_member_occurrences_verified','PS5_operations')}))
