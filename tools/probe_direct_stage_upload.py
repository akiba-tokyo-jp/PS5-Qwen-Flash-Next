#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Copy only the selected SELF into one new CPU-only Direct staging test file."""
import argparse
import concurrent.futures
import json
from pathlib import Path
import secrets
import socket
import struct
import time
import urllib.error
import urllib.parse

from build_performance_quantizer import record
from kernel_vm_preflight import query
from start_success_route import load,need,save
from success_case_control import build,complete,current_files,execute,lan_module


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','mount-plan','out'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--host-check',type=Path,required=True)
    p.add_argument('--execute',action='store_true');p.add_argument('--collect',action='store_true');a=p.parse_args()
    need(not(a.execute and a.collect),'Submit once or collect the same operation')
    state=load(a.current/'active-console.private.json');need(state['original_restored'] and not state['native_running'] and
        not state['model_loaded'] and not state['unknown_completion'],'Positive idle current deployment required')
    selected=current_files(a.current);source=selected[0];need(record(source['path'])=={key:source[key] for key in ('path','bytes','sha256')} and source['bytes']<=32<<20,
        'Only the exact selected production SELF may be used as an opaque CPU test payload')
    check=load(a.host_check)
    need(check['completed'] and check['returned_transport_and_file_cases']==14 and check['actual_receiver_control_flow_unchanged'] and
         check['host_window_still_16384_aligned'] and check['OS_objects']==check['PS5_operations']==0 and
         all(record(row['path'])==row for row in check['inputs']),
         'Exact current receiver, real SHA and returned-failure host controls required before staging')
    lan=lan_module()
    if a.collect:
        intent=load(a.out/'intent.private.json');plan=load(a.out/'native/plan.private.json')
        need((a.out/'native/execution/execution.once.private.json').exists(),'Only collect the consumed native helper')
        raw=lan.web('/fs'+urllib.parse.quote(plan['log'],safe='/'),64<<20);path=a.out/'native/collected-native.private.log';path.write_bytes(raw)
        native=complete(lan,plan,a.out/'native',raw,path)
    else:
        a.out.mkdir(parents=True,exist_ok=False);port=40000+secrets.randbelow(20000);nonce=secrets.token_hex(16)
        with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as route:
            route.connect((lan.HOST,8080));peer=route.getsockname()[0]
        remote='/data/ai/moss-direct-stage-'+secrets.token_hex(16)+'.bin'
        ip=lambda value:int.from_bytes(socket.inet_aton(value),'little')
        context='#define DIRECT_STAGE_PATH '+json.dumps(remote)+'\n#define DIRECT_STAGE_PORT '+str(port)+'u\n'
        context+='#define DIRECT_STAGE_CONSOLE_IP '+str(ip(lan.HOST))+'u\n#define DIRECT_STAGE_PEER_IP '+str(ip(peer))+'u\n'
        context+='#define DIRECT_STAGE_BYTES '+str(source['bytes'])+'ULL\n#define DIRECT_STAGE_SHA256 '+json.dumps(source['sha256'])+'\n'
        context+='#define DIRECT_STAGE_NONCE '+json.dumps(nonce)+'\n'
        plan=build(a.workspace,a.mount_plan,selected,selected,[],'receive-direct-stage',a.out/'native',direct_stage_context=context)
        intent=dict(source=source,remote=remote,port=port,nonce=nonce,peer=peer,native=record(a.out/'native/plan.private.json'),
            host_fault_check=record(a.host_check),
            current_files=selected,maximum_connections=1,payload_window_bytes=16384,receive_buffer_bytes=32768,
            publication_calls=0,existing_file_writes=0,GPU_calls=0,title_launches=0,initializer_requests=0,automatic_retries=0)
        save(a.out/'intent.private.json',intent)
        if not a.execute:return
        before=a.out/'VM-before';before.mkdir();observation=query(lan.HOST,before)
        need(observation['boot_before']==observation['boot_after']==state['current_boot'],'Same boot required')
        save(before/'result.private.json',dict(completed=True,observations=observation,GPU_calls=0))
        original=lan.web;expected='/fs'+urllib.parse.quote(plan['log'],safe='/')
        def bounded_web(path,limit=1<<20,timeout=15):return original(path,64<<20 if path==expected else limit,timeout)
        lan.web=bounded_web
        # A separate host collector permits exactly one send after the native
        # READY record. It never launches/replays a helper after a timeout.
        pool=concurrent.futures.ThreadPoolExecutor(max_workers=1)
        future=pool.submit(execute,lan,plan,a.out/'native',60)
        ready=False;until=time.monotonic()+100
        while time.monotonic()<until:
            try:
                raw=lan.web(expected,64<<20,8)
                if b'\nDIRECT_STAGE_READY ' in raw:ready=True;break
                need(b'\nEND ' not in raw,'Native helper returned before transport admission')
            except urllib.error.HTTPError as error:
                if error.code!=404:raise
            if future.done():future.result();raise RuntimeError('Native helper ended without one transport admission')
            time.sleep(1)
        need(ready,'Native receive admission unknown; no connection or launch retry')
        sent=0;header=struct.pack('<8s32sQ64s16s',b'QWENDIR1',nonce.encode('ascii'),source['bytes'],source['sha256'].encode('ascii'),bytes(16))
        with socket.create_connection((lan.HOST,port),timeout=20) as channel:
            channel.settimeout(20);channel.setsockopt(socket.SOL_SOCKET,socket.SO_SNDBUF,32768);channel.sendall(header)
            with Path(source['path']).open('rb') as stream:
                while True:
                    block=stream.read(16384)
                    if not block:break
                    channel.sendall(block);sent+=len(block)
            response=b''
            while len(response)<8:
                chunk=channel.recv(8-len(response));need(chunk,'Native acknowledgement was short');response+=chunk
            need(response==b'QWENDONE' and sent==source['bytes'],'One exact positive native readback acknowledgement required')
        save(a.out/'sent.private.json',dict(completed=True,source=source,bytes=sent,connections=1,native_stream_and_Direct_readback_SHA256_acknowledged=True,automatic_retries=0))
        failure=None
        try:native=future.result(timeout=90)
        except Exception as error:failure=type(error).__name__;native=None
        if native is None:
            # The native operation may outlast its first collector. Observe only
            # that same journal and retire the helper only after positive END.
            deadline=time.monotonic()+90
            while True:
                raw=lan.web(expected,64<<20,8)
                if b'\nEND ' in raw:break
                need(time.monotonic()<deadline,'Completion unknown; helper/file retained and never resubmitted');time.sleep(1)
            path=a.out/'native/collected-native.private.log';path.write_bytes(raw);native=complete(lan,plan,a.out/'native',raw,path)
        pool.shutdown(wait=True);lan.web=original
    need(native['completed'] and native['operation_calls']==1,'Exactly one new file and complete CPU helper retirement required')
    after=a.out/'VM-after';after.mkdir();observation=query(lan.HOST,after)
    need(observation['boot_before']==observation['boot_after']==state['current_boot'],'Same boot after completed CPU transfer required')
    save(after/'result.private.json',dict(completed=True,observations=observation,GPU_calls=0))
    # Its exact full native SHA is sealed above. The temporary opaque copy is
    # removed only after the helper has exited, never while completion is unknown.
    with lan.ftplib.FTP() as ftp:
        ftp.connect(lan.HOST,2121,timeout=20);ftp.login();need(ftp.sendcmd('SELF')=='226 SELF transfer mode disabled','Raw FTP cleanup mode required')
        need(ftp.sendcmd('DELE '+intent['remote']).startswith(('226 ','250 ')),'Exact completed opaque staging copy removal failed')
    lan.absent(intent['remote'])
    need(current_files(a.current)==selected and all(record(row['path'])=={key:row[key] for key in ('path','bytes','sha256')} for row in selected),'Current PC files changed')
    save(a.out/'result.private.json',dict(completed=True,source=source,bytes=source['bytes'],native=record(a.out/'native/result.private.json'),
        stream_and_independent_Direct_readback_SHA256_exact=True,temporary_file_retired=True,PC_and_console_current_seven_unchanged=True,
        VM_before=record(a.out/'VM-before/result.private.json'),VM_after=record(after/'result.private.json'),
        existing_file_writes=0,publication_calls=0,connections=1,GPU_calls=0,title_launches=0,initializer_requests=0,automatic_retries=0,
        application_launch_memory_saving_qualified=False))
    print(json.dumps(dict(completed=True,bytes=source['bytes'],temporary_copy_retired=True,original_current_seven_unchanged=True,GPU_calls=0)))


if __name__=='__main__':main()
