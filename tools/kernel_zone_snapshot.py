#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Snapshot fixed kernel allocator metadata through the existing read-only shell.

Unavailable zone nodes are explicit results. No title, new ELF, sysctl setter,
allocator pressure, recovery operation or native admission is performed.
"""
import argparse,hashlib,json,re,secrets,socket,time
from pathlib import Path
from kernel_vm_preflight import decode_dump,load_qualified_session,session_boot
FIELDS=(('boot_before','kern.boottime',16),('free_before','vm.stats.vm0.v_free_count',4),
    ('wired_before','vm.stats.vm0.v_wire_count',4),('zones','vm.zone',None),
    ('UMA_zones','vm.uma_zones',None),('mbuf_cluster_limit','kern.ipc.nmbclusters',4),
    ('free_after','vm.stats.vm0.v_free_count',4),('wired_after','vm.stats.vm0.v_wire_count',4),('boot_after','kern.boottime',16))
MAX_NODE=131072

def decode_variable_dump(raw):
    if not isinstance(raw,bytes)or not 0<len(raw)<=MAX_NODE*5:raise ValueError('Bounded zone shell response required')
    text=raw.decode('ascii','strict')
    if 'sysctl:'in text:return None
    payload=bytearray()
    for line in text.splitlines():
        m=re.fullmatch(r'([0-9a-f]{8})  ((?:[0-9a-f]{2} )+[ ]*)\|.*',line)
        if not m:
            if re.search(r'[0-9a-f]{8} {2}',line):raise ValueError('Malformed zone dump')
            continue
        if int(m[1],16)!=len(payload):raise ValueError('Discontinuous zone dump')
        payload.extend(bytes.fromhex(m[2]))
        if len(payload)>MAX_NODE:raise ValueError('Zone node exceeds its fixed cap')
    if not payload:raise ValueError('No returned zone payload')
    return bytes(payload)

def query(host,out,expected_boot):
    values={};available={};total=0;deadline=time.monotonic()+45
    with socket.create_connection((host,2323),timeout=3)as connection:
        connection.settimeout(.25)
        def receive(marker=None):
            nonlocal total
            raw=bytearray();until=min(deadline,time.monotonic()+6)
            while time.monotonic()<until:
                try:block=connection.recv(8192)
                except socket.timeout:continue
                if not block:raise EOFError('Existing shell closed; no retry')
                raw.extend(block);total+=len(block)
                if total>2<<20 or len(raw)>MAX_NODE*5:raise ValueError('Zone response exceeds its bounded transport')
                if raw.endswith(b'$ ')and(marker is None or marker in raw):return bytes(raw)
            raise TimeoutError('Read-only allocator query did not return; no retry')
        (out/'greeting.private.log').write_bytes(receive())
        for index,(key,name,size)in enumerate(FIELDS):
            marker=('QWEN_ZONE_DONE_'+secrets.token_hex(16)).encode('ascii')
            connection.sendall(('sysctl '+name+'\necho ').encode('ascii')+marker+b'\n')
            raw=receive(marker);(out/f'{index:02d}-{key}.private.log').write_bytes(raw)
            if 'sysctl:'in raw.decode('ascii','strict'):
                if key not in('zones','UMA_zones','mbuf_cluster_limit'):raise ValueError('A required boot/VM node was unavailable')
                available[key]=False;values[key]=None;continue
            if size:
                values[key]=decode_dump(raw,size);available[key]=True
            else:
                payload=decode_variable_dump(raw);assert payload is not None
                (out/(key+'.private.bin')).write_bytes(payload);available[key]=True
                try:readable=payload.rstrip(b'\0').decode('ascii','strict')
                except UnicodeError:readable=None
                is_text=readable is not None and all(ord(c)>=32 or c in'\n\r\t'for c in readable)
                if is_text:
                    (out/(key+'.private.txt')).write_text(readable,encoding='utf-8',newline='\n')
                values[key]=dict(bytes=len(payload),sha256=hashlib.sha256(payload).hexdigest(),ASCII_text=is_text)
    if values['boot_before']!=expected_boot or values['boot_after']!=expected_boot:raise ValueError('Allocator snapshot boot differs')
    return dict(observations=values,node_available=available,response_bytes=total)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--host',required=True)
    p.add_argument('--session',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    session,raw=load_qualified_session(a.session);boot=session_boot(session);a.out.mkdir(parents=True,exist_ok=False)
    intent=dict(schema='ps5-qwen-kernel-zone-intent-v1',session=dict(path=str(a.session.resolve()),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()),
        fixed_read_only_queries=FIELDS,expected_boot=boot,connections=1,maximum_seconds=45,maximum_node_bytes=MAX_NODE,
        ELF_requests=0,title_launches=0,GPU_calls=0,sysctl_writes=0,allocator_pressure_calls=0,automatic_retries=0)
    (a.out/'intent.private.json').write_text(json.dumps(intent,indent=2)+'\n')
    result=query(a.host,a.out,boot)
    if a.session.read_bytes()!=raw:raise ValueError('Qualified session changed during allocator snapshot')
    result.update(schema='ps5-qwen-kernel-zone-result-v1',completed=True,boot=boot,
        ELF_requests=0,title_launches=0,GPU_calls=0,sysctl_writes=0,allocator_pressure_calls=0,
        native_admission_granted=False,memory_recovery_claimed=False,automatic_retries=0)
    (a.out/'complete.private.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(completed=True,node_available=result['node_available'],free_before=result['observations']['free_before'],
        free_after=result['observations']['free_after'],ELF_requests=0,title_launches=0,GPU_calls=0)),flush=True)
if __name__=='__main__':main()
