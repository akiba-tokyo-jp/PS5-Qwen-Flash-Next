#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Stage one new model part through the isolated, bounded CPU Direct receiver."""
import argparse
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
from direct_self_staging import qualification
from start_success_route import load, need, save
from success_case_control import build, complete, current_files, execute, lan_module


def stage(capture, remote, out, lan, *, workspace, current_rows, mount_plan, original_proof, receiver_proof):
    """Create a new staging file only; a separate source seal admits publication."""
    host = load(receiver_proof)
    need(host['completed'] and host['only_finite_payload_ceiling_changed'] and host['maximum_model_part_bytes'] == 512 << 20 and
         host['new_boundary_controls']['new_byte_boundary_cases'] == 7 and
         host['original_qualification'] == qualification(original_proof) and
         record(host['receiver']['path']) == host['receiver'] and record(host['original_receiver']['path']) == host['original_receiver'],
         'Exact old transport proof, seven changed boundaries and isolated receiver required')
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
    save(out/'intent.private.json', dict(model_part=capture, remote=remote, receiver=record(receiver/'plan.private.json'),
        receiver_proof=record(receiver_proof), original_proof=record(original_proof), nonce=nonce, peer=peer,
        payload_window_bytes=16384, receive_buffer_bytes=32768, maximum_connections=1, automatic_retries=0,
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
        port = int(ports[0])
        sent, digest = 0, hashlib.sha256()
        started = time.monotonic()
        header = struct.pack('<8s32sQ64s16s', b'QWENDIR1', nonce.encode(), capture['bytes'], capture['sha256'].encode(), bytes(16))
        with socket.create_connection((lan.HOST, port), timeout=20) as channel:
            channel.settimeout(20)
            channel.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 32768)
            channel.sendall(header)
            notice = time.monotonic()+30
            with source.open('rb') as stream:
                while True:
                    block = stream.read(16384)
                    if not block:
                        break
                    channel.sendall(block)
                    sent += len(block)
                    digest.update(block)
                    need(sent <= capture['bytes'], 'Model part exceeded its declared size')
                    if time.monotonic() >= notice:
                        print(json.dumps(dict(model_part_sent=sent, total=capture['bytes'], connections=1)), flush=True)
                        notice = time.monotonic()+30
            response = b''
            while len(response) < 8:
                part = channel.recv(8-len(response))
                need(part, 'Native Direct readback acknowledgement was short')
                response += part
            need(response == b'QWENDONE', 'Native complete Direct SHA/EOF acknowledgement required')
        elapsed = time.monotonic()-started
        stamp = lambda value: (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns)
        need(sent == capture['bytes'] and digest.hexdigest() == capture['sha256'] and stamp(before) == stamp(source.stat()),
             'The complete streamed part and local source identity must remain exact')
        save(out/'transfer-returned.private.json', dict(bytes=sent, sha256=digest.hexdigest(), one_connection=True,
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
    result = dict(completed=True, model_part=capture, remote=remote, bytes=sent, sha256=digest.hexdigest(),
        receiver=record(receiver/'result.private.json'), receiver_proof=record(receiver_proof),
        raw_HTTP_payload_readbacks=0, buffered_FTP_model_part_writes=0, connections=1,
        payload_window_bytes=16384, receive_buffer_bytes=32768, host_transfer_and_readback_ack_seconds=elapsed,
        canonical_file_writes=0, source_publication_still_required=True, model_GPU_operations=0, automatic_retries=0)
    save(out/'result.private.json', result)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('workspace', 'current', 'mount-plan', 'original-proof', 'receiver-proof', 'model-part', 'out'):
        p.add_argument('--'+name, type=Path, required=True)
    a = p.parse_args()
    state = load(a.current/'active-console.private.json')
    need(state['original_restored'] and not state['native_running'] and not state['model_loaded'] and
         not state['unknown_completion'], 'Positive idle current ownership required')
    part = load(a.model_part)
    need(part['completed'] and (part.get('complete_layer') or part.get('all_complete_carriers_independently_inverse_verified')),
         'A completed actual model encoding/carrier part is required')
    remote = '/data/ai/moss-qwen-case-'+secrets.token_hex(16)+'-candidate-SELF.bin'
    result = stage(part['pack'], remote, a.out, lan_module(), workspace=a.workspace, current_rows=current_files(a.current),
                   mount_plan=a.mount_plan, original_proof=a.original_proof, receiver_proof=a.receiver_proof)
    print(json.dumps(dict(completed=True, bytes=result['bytes'], transfer_and_readback_ack_seconds=result['host_transfer_and_readback_ack_seconds'],
                          title_launches=0, GPU_calls=0, source_publication_still_required=True)))


if __name__ == '__main__':
    main()
