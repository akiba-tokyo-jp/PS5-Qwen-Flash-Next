#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Opt-in SELF delivery using the positively qualified bounded Direct receiver."""
import concurrent.futures
import hashlib
import json
from pathlib import Path
import re
import secrets
import socket
import struct
import time
import urllib.error
import urllib.parse

from build_performance_quantizer import record
from start_success_route import load,need,save
from success_case_control import build,complete,execute


def qualification(path):
    proof=load(path);intent=load(Path(path).parent/'intent.private.json')
    need(proof['completed'] and proof['stream_and_independent_Direct_readback_SHA256_exact'] and proof['temporary_file_retired'] and
         proof['PC_and_console_current_seven_unchanged'] and proof['existing_file_writes']==proof['publication_calls']==proof['GPU_calls']==0 and
         proof['connections']==1 and proof['bytes']>=20<<20,'Completed large SELF Direct transport with no existing-file writes required')
    native=load(proof['native']['path']);need(record(proof['native']['path'])==proof['native'] and native['completed'] and
        native['helper_exited'] and native['operation_calls']==1 and record(native['raw']['path'])==native['raw'],
        'Positive returned native transport, exact full journal and helper retirement required')
    host=intent['host_fault_check'];need(record(host['path'])==host,'Host fault qualification changed');tested=load(host['path'])
    need(tested['completed'] and tested['returned_transport_and_file_cases']==14 and tested['actual_receiver_control_flow_unchanged'] and
        tested['host_window_still_16384_aligned'] and all(record(row['path'])==row for row in tested['inputs']),
        'Actual receiver and all returned-failure controls must remain exact')
    if proof.get('OS_assigned_port'):
        endpoint=intent['assigned_port_host_check'];need(record(endpoint['path'])==endpoint,'Assigned-port host receipt changed');checked=load(endpoint['path'])
        need(checked['completed'] and checked['cases']==10 and checked['actual_adapter_tested'] and checked['OS_objects']==0 and
             all(record(r['path'])==r for r in checked['inputs']),'Actual OS-assigned endpoint adapter must remain exact')
        plan=load(Path(proof['native']['path']).parent/'plan.private.json')
        need(record(intent['native']['path'])==intent['native'] and
             Path(plan['context']['path']).read_text().count('#include "direct_stage_assigned_port.h"')==1 and
             len(re.findall(rb'DIRECT_STAGE_READY [^\n]* port=\d+\n',Path(native['raw']['path']).read_bytes()))==1,
             'The positively completed native control must actually bind the assigned-port adapter')
    return record(path)


def upload(capture,remote,out,lan,native_verify,*,workspace,mount_plan,current_rows,qualified,kind='SELF'):
    proof=qualification(qualified);out=Path(out);source=Path(capture['path'])
    need(kind in ('SELF','selected_shader_storage'),'Only qualified SELF or exact selected shader storage delivery is supported')
    if kind=='SELF':
        target_ok=re.fullmatch(r'(?:/data/ai/native-moss-image-sft/PPSA99190/eboot.pending-qwen-plan-[0-9]+|/data/ai/moss-qwen-case-[0-9a-f]{32}-(?:candidate|restore)-SELF)\.bin',remote) and callable(native_verify)
    else:
        selected=current_rows[-1]
        target_ok=(capture=={key:selected[key] for key in ('path','bytes','sha256')} and
            selected['remote']=='/data/ai/native-moss-image-sft/PPSA99190/qwen-runtime/shader-storage-'+capture['sha256']+'.bin' and
            re.fullmatch(r'/data/ai/moss-qwen-case-[0-9a-f]{32}-shader-storage\.bin',remote) and native_verify is None)
    need(target_ok and type(capture['bytes']) is int and 0<capture['bytes']<=32<<20 and record(source)==capture,
        'Exact new owned SELF, local whole SHA and mandatory native publisher required')
    lan.allowed(remote);lan.absent(remote);out.mkdir(parents=True,exist_ok=False)
    before=source.stat();assigned=load(qualified).get('OS_assigned_port') is True
    port=0 if assigned else 40000+secrets.randbelow(20000);nonce=secrets.token_hex(16)
    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as route:
        route.connect((lan.HOST,8080));peer=route.getsockname()[0]
    ip=lambda value:int.from_bytes(socket.inet_aton(value),'little')
    context=''.join('#define '+key+' '+value+'\n' for key,value in dict(DIRECT_STAGE_PATH=json.dumps(remote),
        DIRECT_STAGE_PORT=str(port)+'u',DIRECT_STAGE_CONSOLE_IP=str(ip(lan.HOST))+'u',DIRECT_STAGE_PEER_IP=str(ip(peer))+'u',
        DIRECT_STAGE_BYTES=str(capture['bytes'])+'ULL',DIRECT_STAGE_SHA256=json.dumps(capture['sha256']),DIRECT_STAGE_NONCE=json.dumps(nonce)).items())
    if assigned:context+='#include "direct_stage_assigned_port.h"\n'
    native_out=out/'receiver';plan=build(workspace,mount_plan,current_rows,current_rows,[],'receive-direct-stage',native_out,direct_stage_context=context)
    save(out/'intent.json',dict(SELF=capture,kind=kind,remote=remote,qualification=proof,receiver=record(native_out/'plan.private.json'),
        nonce=nonce,port=port,peer=peer,payload_window_bytes=16384,receive_buffer_bytes=32768,
        current_files=current_rows,existing_file_writes=0,automatic_retries=0,raw_HTTP_payload_readbacks=0))
    original=lan.web;expected='/fs'+urllib.parse.quote(plan['log'],safe='/')
    def bounded(path,limit=1<<20,timeout=15):return original(path,64<<20 if path==expected else limit,timeout)
    lan.web=bounded;pool=concurrent.futures.ThreadPoolExecutor(max_workers=1);future=pool.submit(execute,lan,plan,native_out,60)
    try:
        deadline=time.monotonic()+100;ready=False
        while time.monotonic()<deadline:
            try:
                raw=lan.web(expected,64<<20,8)
                if b'\nDIRECT_STAGE_READY ' in raw:ready=True;break
                need(b'\nEND ' not in raw,'Returned receiver refusal; no connection or publication')
            except urllib.error.HTTPError as error:
                if error.code!=404:raise
            if future.done():future.result();raise RuntimeError('Receiver ended without transport admission')
            time.sleep(1)
        need(ready,'Receiver admission unknown; never connect or launch again')
        if assigned:
            matched=re.findall(rb'DIRECT_STAGE_READY [^\n]* port=(\d+)\n',raw)
            need(len(matched)==1 and 1024<=int(matched[0])<=65535,'One exact OS-assigned endpoint required');port=int(matched[0])
        sent=0;digest=hashlib.sha256();header=struct.pack('<8s32sQ64s16s',b'QWENDIR1',nonce.encode('ascii'),capture['bytes'],capture['sha256'].encode('ascii'),bytes(16))
        with socket.create_connection((lan.HOST,port),timeout=20) as channel:
            channel.settimeout(20);channel.setsockopt(socket.SOL_SOCKET,socket.SO_SNDBUF,32768);channel.sendall(header)
            with source.open('rb') as stream:
                while True:
                    block=stream.read(16384)
                    if not block:break
                    channel.sendall(block);sent+=len(block);digest.update(block);need(sent<=capture['bytes'],'SELF exceeded declared size')
            response=b''
            while len(response)<8:
                chunk=channel.recv(8-len(response));need(chunk,'Native SHA acknowledgement was short');response+=chunk
            need(response==b'QWENDONE','Native complete Direct SHA acknowledgement required')
        stamp=lambda value:(value.st_dev,value.st_ino,value.st_size,value.st_mtime_ns,value.st_ctime_ns)
        need(sent==capture['bytes'] and digest.hexdigest()==capture['sha256'] and stamp(before)==stamp(source.stat()),
            'Entire streamed SELF and unchanged local identity required')
        save(out/'transfer-returned.json',dict(bytes=sent,sha256=digest.hexdigest(),one_connection=True,raw_HTTP_payload_readbacks=0,native_Direct_readback_SHA_acknowledged=True))
        try:returned=future.result(timeout=90)
        except Exception:
            # Only collect this consumed receiver after its positive terminal.
            # There is no second native request or second data connection.
            deadline=time.monotonic()+90
            while True:
                raw=lan.web(expected,64<<20,8)
                if b'\nEND ' in raw:break
                need(time.monotonic()<deadline,'Receiver completion unknown; retain pending file and owners');time.sleep(1)
            path=native_out/'collected-native.private.log';path.write_bytes(raw);returned=complete(lan,plan,native_out,raw,path)
        need(returned['completed'] and returned['operation_calls']==1,'One positively closed receiver and unchanged canonical files required')
    finally:
        # execute_once has a finite first collector; shutdown never terminates
        # the native owner. Unknown native ownership always blocks publication.
        pool.shutdown(wait=True);lan.web=original
    evidence=None
    if kind=='SELF':
        evidence=native_verify(capture,remote)
        need(evidence.get('whole_native_SHA256_identity_EOF_verified') and evidence.get('all_reads_returned') and
             evidence.get('sha256')==capture['sha256'] and evidence.get('bytes')==capture['bytes'],
             'Existing native whole-SHA publisher must still qualify the exact pending SELF')
    result=dict(completed=True,bytes=sent,sha256=digest.hexdigest(),raw_HTTP_payload_readbacks=0,buffered_FTP_SELF_writes=0,
        transport='nonce_bound_CPU_Direct',kind=kind,native_receiver=record(native_out/'result.private.json'),native_verification=evidence,
        shader_copy_is_new_only_and_not_canonical_publication=kind=='selected_shader_storage',
        original_canonical_until_native_verification=True,automatic_retries=0,memory_or_inference_gain_qualified=False)
    save(out/'complete.json',result);return result
