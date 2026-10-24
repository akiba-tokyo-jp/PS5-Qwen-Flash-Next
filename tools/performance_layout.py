#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Bounded GGUF metadata and completed-trace screening; no model inference."""
import argparse
from collections import OrderedDict
import hashlib
import json
from pathlib import Path
import struct


def identity(path):
    s=path.stat()
    return (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)


def read_header(path):
    before=identity(path)
    with path.open('rb') as f:
        def get(fmt):
            n=struct.calcsize(fmt);b=f.read(n)
            if len(b)!=n or f.tell()>32<<20:raise ValueError('GGUF header bound exceeded')
            return struct.unpack(fmt,b)[0]
        def string():
            n=get('<Q')
            if n>1<<20:raise ValueError('GGUF string bound exceeded')
            b=f.read(n)
            if len(b)!=n or f.tell()>32<<20:raise ValueError('GGUF string truncated')
            return b.decode('utf-8')
        formats={0:'<B',1:'<b',2:'<H',3:'<h',4:'<I',5:'<i',6:'<f',7:'<?',10:'<Q',11:'<q',12:'<d'}
        def value(kind,retain=False):
            if kind in formats:return get(formats[kind])
            if kind==8:return string()
            if kind==9:
                t=get('<I');n=get('<Q')
                if n>1<<24 or t==9:raise ValueError('GGUF array bound exceeded')
                result=[] if retain and n<=1024 else None
                for _ in range(n):
                    item=value(t)
                    if result is not None:result.append(item)
                return result
            raise ValueError('Unsupported GGUF metadata kind')
        if f.read(4)!=b'GGUF' or get('<I')!=3:raise ValueError('Expected original GGUF v3')
        nt,nm=get('<Q'),get('<Q')
        if nt>4096 or nm>4096:raise ValueError('GGUF table bound exceeded')
        metadata={}
        for _ in range(nm):
            key=string();t=get('<I');keep=not key.startswith('tokenizer.')
            item=value(t,keep)
            if keep:metadata[key]=item
        tensors=[]
        for _ in range(nt):
            name=string();nd=get('<I')
            if not 1<=nd<=4:raise ValueError('GGUF tensor rank differs')
            shape=[get('<Q') for _ in range(nd)];kind=get('<I');offset=get('<Q')
            if kind not in (0,30) or any(not n for n in shape):raise ValueError('Expected original F32/BF16')
            count=1
            for n in shape:count*=n
            tensors.append(dict(name=name,shape=shape,type=kind,offset=offset,bytes=count*(4 if kind==0 else 2)))
        alignment=metadata.get('general.alignment',32)
        if type(alignment)is not int or not 1<=alignment<=16384:raise ValueError('Invalid GGUF alignment')
        start=(f.tell()+alignment-1)//alignment*alignment
        for t in tensors:
            t['file_offset']=start+t['offset']
            if t['file_offset']+t['bytes']>before[2]:raise ValueError('Tensor exceeds original file')
    if identity(path)!=before:raise ValueError('Original file identity changed')
    return dict(file=path.name,file_bytes=before[2],header_bytes=start,metadata=metadata,tensors=tensors)


def split_extent(file,offset,bytes_,size):
    if min(file,offset)<0 or bytes_<=0 or size<=0:raise ValueError('Invalid extent')
    out=[]
    while bytes_:
        chunk,within=divmod(offset,size);take=min(bytes_,size-within)
        out.append(((file,chunk),within,take));offset+=take;bytes_-=take
    return out


def screen_trace(rows,file_sizes,size,handles=8):
    lru=OrderedDict();opens=0;cross=0;selected=0;calls=0;total=0
    for r in rows:
        pair=[]
        for file,offset,n in zip(r['files'],r['aligned_offsets'],r['requested_bytes']):
            if not 0<=file<len(file_sizes) or offset+n>file_sizes[file]:raise ValueError('Trace extent exceeds file')
            parts=split_extent(file,offset,n,size);cross+=len(parts)>1;calls+=len(parts);total+=n
            for key,_,_ in parts:
                if key not in lru:
                    opens+=1
                    if len(lru)==handles:lru.popitem(last=False)
                else:del lru[key]
                lru[key]=True
            pair.append(parts)
        # The current selector's 4 MiB inset remains in force. This is geometry
        # eligibility only, never a claim that a new physical inode is qualified.
        if all(len(parts)==1 and parts[0][1]>=4<<20 and
               parts[0][1]+parts[0][2]<=(1<<30)-(4<<20) for parts in pair):selected+=1
    return dict(chunk_bytes=size,physical_files=sum((n+size-1)//size for n in file_sizes),
        sampled_pairs=len(rows),sampled_crossing_extents=cross,sampled_physical_calls=calls,
        sampled_returned_bytes=total,sampled_parallel_geometry_eligible_pairs=selected,
        sampled_eight_descriptor_opens=opens,sample_is_full_route_or_contiguous_IO_trace=False,
        native_speedup_qualified=False)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--model-directory',type=Path,required=True)
    p.add_argument('--receipt',type=Path,required=True)
    p.add_argument('--trace',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();a.out.mkdir(exist_ok=False)
    raw=a.receipt.read_bytes();receipt=json.loads(raw);headers=[]
    for row in receipt['files']:
        path=a.model_directory/row['path']
        if path.parent.resolve()!=a.model_directory.resolve():raise ValueError('Original path escaped')
        headers.append(read_header(path))
    trace_raw=a.trace.read_bytes();trace=json.loads(trace_raw)
    if not trace['completed'] or not trace['all_read_counts_exact']:raise ValueError('Incomplete source trace')
    rows=[r for r in trace['rows'] if r['round']==0 and r['mode']==0]
    if len(rows)!=32 or len({r['index']for r in rows})!=32:raise ValueError('Expected 32 completed sparse pairs')
    sizes=[h['file_bytes']for h in headers]
    result=dict(schema='ps5-qwen-layout-screen-v1',model_receipt_sha256=hashlib.sha256(raw).hexdigest(),
        completed_trace_sha256=hashlib.sha256(trace_raw).hexdigest(),file_count=len(headers),
        model_bytes=sum(sizes),metadata_only=True,model_payload_read_bytes=0,console_requests=0,
        screens=[screen_trace(rows,sizes,n<<20)for n in (512,256,128,64)])
    (a.out/'headers.private.json').write_text(json.dumps(headers,indent=2)+'\n',encoding='utf-8')
    (a.out/'receipt.private.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result))
if __name__=='__main__':main()
