#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Read fixed VM counters using the existing shell before staging a new case.

This is an inexpensive refusal screen. Passing never replaces fresh native
owner, memory-pool, file-integrity or completion admission.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import secrets
import socket
import time

FIELDS = (
    ('boot_before', 'kern.boottime', 16),
    ('page_bytes', 'hw.pagesize', 4),
    ('total', 'vm.stats.vm0.v_page_count', 4),
    ('minimum', 'vm.stats.vm0.v_free_min', 4),
    ('reserved', 'vm.stats.vm0.v_free_reserved', 4),
    ('target', 'vm.stats.vm0.v_free_target', 4),
    ('free_first', 'vm.stats.vm0.v_free_count', 4),
    ('active', 'vm.stats.vm0.v_active_count', 4),
    ('inactive', 'vm.stats.vm0.v_inactive_count', 4),
    ('wired', 'vm.stats.vm0.v_wire_count', 4),
    ('cache', 'vm.stats.vm0.v_cache_count', 4),
    ('free_last', 'vm.stats.vm0.v_free_count', 4),
    ('boot_after', 'kern.boottime', 16),
)
MAX_RESPONSE = 65536


def decode_dump(raw, length):
    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_RESPONSE:
        raise ValueError('A bounded shell response is required')
    text = raw.decode('ascii', 'strict')
    if 'sysctl:' in text:
        raise ValueError('Unavailable counters cannot grant admission')
    payload = bytearray()
    for line in text.splitlines():
        match = re.fullmatch(r'([0-9a-f]{8})  ((?:[0-9a-f]{2} )+[ ]*)\|.*', line)
        if not match:
            if re.search(r'[0-9a-f]{8} {2}', line):
                raise ValueError('Malformed counter dump')
            continue
        if int(match[1], 16) != len(payload):
            raise ValueError('Counter dump offsets are not contiguous')
        payload.extend(bytes.fromhex(match[2]))
    if len(payload) != length:
        raise ValueError('Counter size differs from the qualified ABI')
    if length == 16:
        boot = [int.from_bytes(payload[:8], 'little', signed=True),
                int.from_bytes(payload[8:], 'little', signed=True)]
        if boot[0] <= 0 or not 0 <= boot[1] < 1000000:
            raise ValueError('Invalid boot identity')
        return boot
    return int.from_bytes(payload, 'little')


def review(values, expected_boot, required_pages):
    if set(values) != {key for key, _, _ in FIELDS}:
        raise ValueError('Every ordered VM observation must complete')
    if not isinstance(expected_boot, list) or len(expected_boot) != 2 or any(type(v) is not int for v in expected_boot):
        raise ValueError('A qualified boot identity is required')
    if values['boot_before'] != expected_boot or values['boot_after'] != expected_boot:
        raise ValueError('Current boot differs from the qualified session')
    for key, _, size in FIELDS:
        if size == 4 and (type(values[key]) is not int or not 0 <= values[key] <= 0xffffffff):
            raise ValueError('Invalid unsigned VM counter')
    v = values
    if v['page_bytes'] != 16384 or not 0 < v['reserved'] <= v['minimum'] < v['target'] <= v['total']:
        raise ValueError('Kernel VM geometry differs')
    if any(v[k] > v['total'] for k in ('free_first', 'free_last', 'active', 'inactive', 'wired', 'cache')):
        raise ValueError('VM population exceeds its domain')
    floor = v['minimum'] + max(v['reserved'], 256)
    if type(required_pages) is not int or required_pages < floor:
        raise ValueError('The operational floor must not be reduced')
    enough = min(v['free_first'], v['free_last']) >= required_pages
    return dict(schema='ps5-qwen-shell-VM-preflight-v1',
                state='screen_passed_native_admission_still_required' if enough else 'refused_before_staging',
                observations=values, operational_floor_pages=floor,
                required_pages=required_pages, may_prepare_new_case=enough,
                native_admission_granted=False, inactive_counted_as_free=False,
                ELF_requests=0, title_launches=0, GPU_calls=0, kernel_entries=0,
                sysctl_writes=0, automatic_retries=0)


def session_boot(session):
    if (session.get('state') != 'fresh_readonly_context_verified' or
            session.get('double_snapshot_equal') is not True or
            type(session.get('native_eboot_count')) is not int or session['native_eboot_count'] != 0 or
            session.get('old_session_or_synthetic_owner_used') is not False or
            type(session.get('runningBigApp')) is not int or session['runningBigApp'] != -1 or
            type(session.get('kstuff_query_raw')) is not int or session['kstuff_query_raw'] != 0):
        raise ValueError('A complete qualified idle CPU session is required')
    boot = session.get('boot')
    if (not isinstance(boot, list) or len(boot) != 2 or any(type(v) is not int for v in boot) or
            boot[0] <= 0 or not 0 <= boot[1] < 1000000):
        raise ValueError('A valid qualified boot identity is required')
    return boot


def load_qualified_session(path):
    raw = Path(path).read_bytes()
    session = json.loads(raw)
    boot = session_boot(session)
    evidence = session['evidence']
    log = Path(evidence['path']).read_bytes()
    manifest_raw = Path(evidence['manifest_path']).read_bytes()
    manifest = json.loads(manifest_raw)
    if (not 0 < len(log) <= 131072 or len(log) != evidence['bytes'] or
            hashlib.sha256(log).hexdigest() != evidence['sha256'] or
            hashlib.sha256(manifest_raw).hexdigest() != evidence['manifest_sha256'] or
            evidence['boot'] != boot or manifest['expected_boot'] != boot or
            manifest['expected_firmware'] != session['FW'] or session['FW'] != '0x12400009' or
            manifest['nonce'] != evidence['nonce']):
        raise ValueError('Complete CPU evidence identity differs')
    last = log.decode('ascii', 'strict').splitlines()[-1]
    if not last.startswith('END success=1 log_healthy=1 ') or ('nonce='+manifest['nonce']) not in last.split():
        raise ValueError('The CPU observer did not positively complete')
    artifact = evidence['observer_artifact']
    binary = Path(artifact['path']).read_bytes()
    if (artifact != manifest['artifact'] or len(binary) != artifact['bytes'] or
            hashlib.sha256(binary).hexdigest() != artifact['sha256']):
        raise ValueError('Qualified CPU observer identity differs')
    actual = [*session['services'], session['parent'], session['shellcore']]
    actual += [p for p in session['compat_candidates'] if p.get('name') == 'payload' and p.get('self') is False]
    keys = ('name', 'pid', 'ppid', 'uid', 'start_sec', 'start_usec')
    identity = lambda p: tuple(p[k] for k in keys)
    expected = manifest['expected_processes']
    if len(actual) != 8 or len(expected) != 8 or sorted(map(identity, actual)) != sorted(map(identity, expected)):
        raise ValueError('CPU receipt owners differ from its actual compiled guards')
    return session, raw


def query(host, out):
    values = {}
    transport_bytes = 0
    deadline = time.monotonic() + 45
    with socket.create_connection((host, 2323), timeout=3) as connection:
        connection.settimeout(0.25)

        def receive(marker=None):
            nonlocal transport_bytes
            raw = bytearray()
            until = min(deadline, time.monotonic() + 4)
            while time.monotonic() < until:
                try:
                    block = connection.recv(4096)
                except socket.timeout:
                    continue
                if not block:
                    raise EOFError('Existing shell closed; no retry')
                raw.extend(block)
                transport_bytes += len(block)
                if transport_bytes > MAX_RESPONSE:
                    raise ValueError('Shell response exceeds its fixed bound')
                if raw.endswith(b'$ ') and (marker is None or marker in raw):
                    return bytes(raw)
            raise TimeoutError('Shell scalar query did not return; no retry')

        (out / 'greeting.private.log').write_bytes(receive())
        for index, (key, name, size) in enumerate(FIELDS):
            marker = ('QWEN_VM_DONE_' + secrets.token_hex(16)).encode('ascii')
            # Both command names and sysctl names are fixed, with no setters.
            connection.sendall(('sysctl ' + name + '\necho ').encode('ascii') + marker + b'\n')
            raw = receive(marker)
            (out / f'{index:02d}-{key}.private.log').write_bytes(raw)
            values[key] = decode_dump(raw, size)
    return values


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', required=True)
    parser.add_argument('--session', type=Path, required=True)
    parser.add_argument('--required-pages', type=int, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    session, raw = load_qualified_session(args.session)
    boot = session_boot(session)
    args.out.mkdir(parents=True, exist_ok=False)
    intent = dict(session=dict(path=str(args.session.resolve()), bytes=len(raw),
                  sha256=hashlib.sha256(raw).hexdigest()), expected_boot=boot,
                  required_pages=args.required_pages, fixed_queries=list(FIELDS),
                  maximum_connections=1, maximum_seconds=45,
                  maximum_response_bytes=MAX_RESPONSE, automatic_retries=0)
    (args.out / 'intent.private.json').write_text(json.dumps(intent, indent=2) + '\n')
    result = review(query(args.host, args.out), boot, args.required_pages)
    if args.session.read_bytes() != raw:
        raise ValueError('The input session changed during the screen')
    result['input'] = intent['session']
    with (args.out / 'complete.private.json').open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps({key: result[key] for key in ('state', 'operational_floor_pages', 'required_pages',
          'may_prepare_new_case', 'native_admission_granted', 'ELF_requests', 'title_launches', 'GPU_calls')}))


if __name__ == '__main__':
    main()
