#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Extend an exact NIR storage overlay with immutable packet-description data."""
import argparse,hashlib,json,subprocess,zlib
from pathlib import Path
from driver_table_storage import selected,verify_object,write_archive,validate as validate_parent
from shader_storage import archive_members,record
MEMBER='ac_parse_ib.c.o'
SCHEMA='ps5-qwen-cold-driver-tables-v2'
def validate(path,donor):
    m=json.loads(Path(path).read_text());parent=m.get('parent',{})
    if m.get('schema')!=SCHEMA or record(parent['path'])!=parent:raise ValueError('Exact parent storage required')
    p=validate_parent(parent['path'],donor)
    if m['source_archive']!=p['source_archive']or m['tables'][:len(p['tables'])]!=p['tables']:
        raise ValueError('Original NIR storage identity changed')
    for k in('archive','pool','assembly','registry','linker_script','additional_cold_member'):
        if record(m[k]['path'])!=m[k]:raise ValueError('Extended driver input changed: '+k)
    a,b=list(archive_members(p['archive']['path'])),list(archive_members(m['archive']['path']))
    if len(a)!=len(b):raise ValueError('Archive occurrences changed')
    names=m.get('additional_source_members',[m['additional_source_member']]);counts={n:0 for n in names}
    for old,new in zip(a,b):
        if old[0]in counts and new[0]==old[0]:
            rows=[r for r in m['tables'][len(p['tables']):]if r.get('member',names[0])==old[0]]
            verify_object(old[1],new[1],rows);counts[old[0]]+=1
        elif old!=new:raise ValueError('An untouched native member changed')
    if any(n!=1 for n in counts.values()):raise ValueError('Additional constant members must be unique')
    return m
def build(parent,llvm,out,names):
    parent,llvm,out=Path(parent),Path(llvm),Path(out);p=json.loads(parent.read_text())
    p=validate_parent(parent,p['source_archive']['path']);out.mkdir(parents=True,exist_ok=False)
    if not names or len(set(names))!=len(names)or len(names)>4:raise ValueError('One explicit finite additional member set is required')
    members=list(archive_members(p['archive']['path']));rows=list(p['tables']);added=[];cold_members=[]
    pool=bytearray(Path(p['pool']['path']).read_bytes())
    for j,member in enumerate(names):
        positions=[i for i,(n,_)in enumerate(members)if n==member]
        if len(positions)!=1:raise ValueError('Additional constant member must be unique')
        index=positions[0];raw=members[index][1];original=out/f'original-{j}.o';original.write_bytes(raw)
        items=[s for s in selected(raw)if s['bytes']>=16384];local=[];rename=[];change=[]
        for s in items:
            i=len(rows);name=f'.qwen_cold_table_{i:04}';symbol=f'qwen_driver_table_{i:04}';packed=zlib.compress(s['data'],9)
            if zlib.decompress(packed)!=s['data']:raise ValueError('Exact constant roundtrip failed')
            row=dict(index=s['index'],member=member,original_section=s['name'],new_section=name,symbol=symbol,bytes=s['bytes'],
                alignment=s['alignment'],sha256=hashlib.sha256(s['data']).hexdigest(),offset=len(pool),packed_bytes=len(packed))
            rows.append(row);added.append(row);local.append(row);pool.extend(packed)
            rename+=['--rename-section='+s['name']+'='+name+',alloc']
            change+=['--set-section-type='+name+'=8','--add-symbol='+symbol+'='+name+':0,global,object']
        if not local or len(rows)>1024:raise ValueError('Every explicit member requires a bounded exact constant set')
        renamed=out/f'renamed-{j}.o';target=out/f'cold-{j}.o'
        for i,args in enumerate((rename+[str(original),str(renamed)],change+[str(renamed),str(target)])):
            rsp=out/f'objcopy-{j}-{i}.rsp';rsp.write_text('\n'.join(json.dumps(v)for v in args)+'\n',newline='\n')
            r=subprocess.run([str(llvm/'llvm-objcopy.exe'),'@'+str(rsp)],capture_output=True,timeout=120)
            (out/f'objcopy-{j}-{i}.private.log').write_bytes(r.stdout+r.stderr)
            if r.returncode:raise ValueError(r.stderr.decode(errors='replace'))
        cold=target.read_bytes();verify_object(raw,cold,local);members[index]=(member,cold);cold_members.append(record(target))
    archive=out/'libvulkan-cold-tables.a';write_archive(archive,members)
    r=subprocess.run([str(llvm/'llvm-ranlib.exe'),str(archive)],capture_output=True,timeout=120)
    (out/'ranlib.private.log').write_bytes(r.stdout+r.stderr)
    if r.returncode or list(archive_members(archive))!=members:raise ValueError('Every untouched native member must remain exact')
    (out/'tables.deflate.bin').write_bytes(pool)
    assembly=Path(p['assembly']['path']).read_text().replace(Path(p['pool']['path']).as_posix(),(out/'tables.deflate.bin').as_posix())
    registry=Path(p['registry']['path']).read_text()
    declarations=''.join('extern "C" unsigned char '+r['symbol']+'[];\n'for r in added)
    registry=registry.replace('static const qwen_driver_table tables[]={',declarations+'static const qwen_driver_table tables[]={')
    extra=''
    for r in added:extra+='{'+r['symbol']+','+','.join(str(r[k])for k in('bytes','offset','packed_bytes'))+',{'+','.join(str(v)for v in bytes.fromhex(r['sha256']))+'}},\n'
    registry=registry.replace('};\nextern "C" unsigned char',extra+'};\nextern "C" unsigned char')
    registry=registry.replace('{tables,'+str(len(p['tables']))+',qwen_driver_table_packed,'+str(p['packed_bytes']),
        '{tables,'+str(len(rows))+',qwen_driver_table_packed,'+str(len(pool)))
    (out/'tables.S').write_text(assembly,newline='\n');(out/'registry.cpp').write_text(registry,newline='\n')
    (out/'tables.ld').write_bytes(Path(p['linker_script']['path']).read_bytes())
    m=dict(p,schema=SCHEMA,parent=record(parent),tables=rows,archive=record(archive),additional_cold_member=cold_members[0],additional_cold_members=cold_members,
        pool=record(out/'tables.deflate.bin'),assembly=record(out/'tables.S'),registry=record(out/'registry.cpp'),
        linker_script=record(out/'tables.ld'),original_table_bytes=sum(r['bytes']for r in rows),packed_bytes=len(pool),
        additional_source_member=names[0],additional_source_members=names,untouched_member_occurrences_verified=p['untouched_member_occurrences_verified']-len(names))
    target=out/'receipt.private.json';target.write_text(json.dumps(m,indent=2)+'\n');validate(target,p['source_archive']['path'])
    print(json.dumps(dict(original_table_bytes=m['original_table_bytes'],packed_bytes=m['packed_bytes'],tables=len(rows),PS5_operations=0)))
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in('parent','llvm','out'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--members',nargs='+',default=[MEMBER])
    a=p.parse_args();build(a.parent,a.llvm,a.out,a.members)
