#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Stage one new model part through the isolated, bounded CPU Direct receiver."""
import argparse
import concurrent.futures
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
from direct_self_staging import qualification
from start_success_route import load, need, save
from success_case_control import build, complete, current_files, execute, lan_module
from model_part_payload import send_payload


def stage(capture, remote, out, lan, *, workspace, current_rows, mount_plan, original_proof, receiver_proof):
    """Create a new staging file only; a separate source seal admits publication."""
    host = load(receiver_proof)
    batched=host.get('receive_socket_buffer_bytes')==262144 and host.get('socket_configuration_controls',{}).get('socket_configuration_cases')==10
    need(host['completed'] and batched and host['maximum_model_part_bytes'] == 512 << 20 and
         host['reused_ceiling_boundaries']==7 and host['reused_changed_data_transport_cases']==14 and host['reused_changed_integrity_controls']==25 and
         host['original_qualification'] == qualification(original_proof) and
         record(host['receiver']['path']) == host['receiver'] and record(host['original_receiver']['path']) == host['original_receiver'],
         'Exact original proof, batch geometry and observed bounded socket profile required; never repeat the failed large16KiB scope')
    if host.get('wait_all_receive'):
        controls=host['new_wait_all_controls']
        need(controls['completed'] and controls['positive_controls']==4 and controls['negative_controls']==7 and
             controls['OS_objects']==controls['PS5_operations']==0 and
             host['only_receive_flag_and_returned_length_guard_changed'] and
             host['unchanged_socket_transport_integrity_controls_replayed']==0,
             'The changed actual receive body and partial/timeout boundaries must pass')
    need(re.fullmatch(r'/data/ai/moss-qwen-case-[0-9a-f]{32}-candidate-SELF\.bin', remote) and
         type(capture['bytes']) is int and 0 < capture['bytes'] <= 512 << 20 and record(capture['path']) == capture,
         'One exact new owned bounded model-part staging file is required')
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    source = Path(capture['path'])
    before = source.stat()
    lan.allowed(remote)
    lan.absent(remote)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as route:
        route.connect((lan.HOST, 8080))
        peer = route.getsockname()[0]
    ip = lambda value: int.from_bytes(socket.inet_aton(value), 'little')
    nonce = secrets.token_hex(16)
    values = dict(DIRECT_STAGE_PATH=json.dumps(remote), DIRECT_STAGE_PORT='0u',
        DIRECT_STAGE_CONSOLE_IP=str(ip(lan.HOST))+'u', DIRECT_STAGE_PEER_IP=str(ip(peer))+'u',
        DIRECT_STAGE_BYTES=str(capture['bytes'])+'ULL', DIRECT_STAGE_SHA256=json.dumps(capture['sha256']),
        DIRECT_STAGE_NONCE=json.dumps(nonce))
    context = ''.join('#define '+key+' '+value+'\n' for key, value in values.items())
    context += '#include "direct_stage_assigned_port.h"\n'
    receiver = out / 'receiver'
    plan = build(workspace, mount_plan, current_rows, current_rows, [], 'receive-direct-stage', receiver,
                 direct_stage_context=context, direct_stage_header=host['receiver']['path'])
    need(plan['receive_window_bytes']==host['receive_window_bytes']==262144 and
         plan['CPU_metadata_margin_pages']==host['CPU_metadata_margin_pages']==99 and
         plan['additional_fixed_CPU_buffer_pages']==30 and plan['additional_socket_kernel_allowance_pages']==32,
         'The exact added static buffers and socket allowance must enter stronger native admission')
    need(plan['receive_wait_all']==bool(host.get('wait_all_receive')),'The actual compiled receive flag must match its profile')
    save(out/'intent.private.json', dict(model_part=capture, remote=remote, receiver=record(receiver/'plan.private.json'),
        receiver_proof=record(receiver_proof), original_proof=record(original_proof), nonce=nonce, peer=peer,
        payload_window_bytes=262144,host_send_window_bytes=262144,TCP_NODELAY=True,receive_buffer_bytes=262144,maximum_connections=1,automatic_retries=0,
        canonical_file_writes=0, model_or_GPU_operations=0, source_publication_still_required=True))
    expected = '/fs'+urllib.parse.quote(plan['log'], safe='/')
    original_web = lan.web
    def bounded(path, limit=1<<20, timeout=15):
        return original_web(path, 64<<20 if path == expected else limit, timeout)
    lan.web = bounded
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    future = pool.submit(execute, lan, plan, receiver, 60)
    try:
        deadline = time.monotonic()+100
        ready = None
        while time.monotonic() < deadline:
            try:
                raw = lan.web(expected, 64<<20, 8)
                if b'\nDIRECT_STAGE_READY ' in raw:
                    ready = raw
                    break
                need(b'\nEND ' not in raw, 'Returned receiver refusal; never connect or resubmit')
            except urllib.error.HTTPError as error:
                if error.code != 404:
                    raise
            if future.done():
                future.result()
                raise RuntimeError('Receiver ended without admission')
            time.sleep(1)
        need(ready is not None, 'Receiver admission unknown; retain owners and never reconnect')
        ports = re.findall(rb'DIRECT_STAGE_READY [^\n]* port=(\d+)\n', ready)
        need(len(ports) == 1 and 1024 <= int(ports[0]) <= 65535, 'One exact original OS-assigned endpoint required')
        observed=re.findall(rb'DIRECT_STAGE_SOCKET_BUFFER requested=262144 observed=(\d+) extra_kernel_reserve_pages=32',ready)
        need(b'window=262144 receive_buffer=262144' in ready and len(observed)==1 and 262144<=int(observed[0])<=524288,
             'Actual requested/observed native socket bounds and truthful data-window geometry required')
        port = int(ports[0])
        started = time.monotonic()
        header = struct.pack('<8s32sQ64s16s', b'QWENDIR1', nonce.encode(), capture['bytes'], capture['sha256'].encode(), bytes(16))
        with socket.create_connection((lan.HOST, port), timeout=20) as channel:
            channel.settimeout(20)
            channel.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 262144)
            channel.sendall(header)
            notice = time.monotonic()+30
            def progress(sent):
                nonlocal notice
                if time.monotonic() >= notice:
                    print(json.dumps(dict(model_part_sent=sent, total=capture['bytes'], connections=1)), flush=True)
                    notice = time.monotonic()+30
            transfer=send_payload(channel,source,capture['bytes'],progress)
            sent=transfer['bytes']
            channel.settimeout(90)
            response = b''
            while len(response) < 8:
                part = channel.recv(8-len(response))
                need(part, 'Native Direct readback acknowledgement was short')
                response += part
            need(response == b'QWENDONE', 'Native complete Direct SHA/EOF acknowledgement required')
        elapsed = time.monotonic()-started
        stamp = lambda value: (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns)
        need(sent == capture['bytes'] and transfer['sha256'] == capture['sha256'] and stamp(before) == stamp(source.stat()),
             'The complete streamed part and local source identity must remain exact')
        save(out/'transfer-returned.private.json', dict(**transfer, one_connection=True,
            native_Direct_readback_SHA_and_EOF_acknowledged=True, host_transfer_and_readback_ack_seconds=elapsed))
        try:
            returned = future.result(timeout=90)
        except Exception:
            deadline = time.monotonic()+90
            while True:
                raw = lan.web(expected, 64<<20, 8)
                if b'\nEND ' in raw:
                    break
                need(time.monotonic() < deadline, 'Receiver completion unknown; retain staging file and owner')
                time.sleep(1)
            path = receiver/'collected-native.private.log'
            path.write_bytes(raw)
            returned = complete(lan, plan, receiver, raw, path)
        need(returned['completed'] and returned['operation_calls'] == 1 and returned['helper_exited'] and
             returned['helper_files_removed'], 'One positively closed receiver and unchanged current seven files required')
    finally:
        pool.shutdown(wait=True)
        lan.web = original_web
    result = dict(completed=True, model_part=capture, remote=remote, bytes=sent, sha256=transfer['sha256'],
        receiver=record(receiver/'result.private.json'), receiver_proof=record(receiver_proof),
        raw_HTTP_payload_readbacks=0, buffered_FTP_model_part_writes=0, connections=1,
        payload_window_bytes=262144,host_send_window_bytes=262144,TCP_NODELAY=True,receive_buffer_bytes=262144,
        actual_host_stream=transfer,host_transfer_and_readback_ack_seconds=elapsed,
        receive_wait_all=bool(host.get('wait_all_receive')),canonical_file_writes=0,
        source_publication_still_required=True, model_GPU_operations=0, automatic_retries=0)
    save(out/'result.private.json', result)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('workspace', 'current', 'mount-plan', 'original-proof', 'receiver-proof', 'model-part', 'out'):
        p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--PS5-host',help='Restrict this CLI transfer to the identified existing console LAN address')
    a = p.parse_args()
    state = load(a.current/'active-console.private.json')
    need(state['original_restored'] and not state['native_running'] and not state['model_loaded'] and
         not state['unknown_completion'], 'Positive idle current ownership required')
    part = load(a.model_part)
    fragment=part.get('complete_verified_IQ2_fragment') is True
    if fragment:
        master=load(part['master_encoding']['path'])
        need(record(part['master_encoding']['path'])==part['master_encoding'] and master['completed'] and master['complete_layer'] and
             master['encoded_Experts']==512 and part['master_pack']==master['pack'] and
             part['Experts']==64 and part['first_Expert']%64==0 and 0<=part['first_Expert']<=448 and
             part['pack']['bytes']==27033600 and part['lossless_byte_slice_only'],
             'The bounded actual fragment must bind its complete independently decoded master encoding')
    need(part['completed'] and (part.get('complete_layer') or part.get('all_complete_carriers_independently_inverse_verified') or fragment),
         'A completed actual model encoding/carrier part is required')
    lan=lan_module()
    if a.PS5_host:
        import ipaddress
        need(ipaddress.ip_address(a.PS5_host).is_private and lan.HOST==a.PS5_host,'Only the identified existing PS5 LAN destination is authorized')
    remote = '/data/ai/moss-qwen-case-'+secrets.token_hex(16)+'-candidate-SELF.bin'
    result = stage(part['pack'], remote, a.out, lan, workspace=a.workspace, current_rows=current_files(a.current),
                   mount_plan=a.mount_plan, original_proof=a.original_proof, receiver_proof=a.receiver_proof)
    print(json.dumps(dict(completed=True, bytes=result['bytes'], transfer_and_readback_ack_seconds=result['host_transfer_and_readback_ack_seconds'],
                          title_launches=0, GPU_calls=0, source_publication_still_required=True)))


if __name__ == '__main__':
    main()
