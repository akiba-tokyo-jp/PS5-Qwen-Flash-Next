#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Resume only the uncompleted suffix of an interrupted source publication."""
import argparse
import json
from pathlib import Path

from build_performance_quantizer import record
from publish_iq2_up_model_overlay import verify_input
from start_success_route import load, need, save
from success_case_control import lan_module


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('current', 'publication', 'interruption', 'out'):
        p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args()
    plan_path = a.publication / 'plan.private.json'
    plan = load(plan_path)
    interrupted = load(a.interruption)
    rows = interrupted['rows']
    files = plan['files']
    first = len(rows)
    need(interrupted['complete'] and interrupted['exit_code'] != 0 and
         'ConnectionResetError' in interrupted['terminal_output'] and
         not interrupted['expected_quarantined_helper_error'],
         'A terminal interrupted transfer with no native handoff is required')
    need(0 < first < len(files) and
         [r['uploaded_file'] for r in rows] == list(range(1, first + 1)) and
         all(r['total'] == len(files) and r['bytes'] == f['local']['bytes']
             for r, f in zip(rows, files)), 'Preserve the exact positive prefix')
    need(not (a.publication / 'native/execution/execution.once.private.json').exists(),
         'No native helper may have been submitted before the interrupted suffix')
    state_path = a.current / 'active-console.private.json'
    state = load(state_path)
    owner = state['source_publication_owner']
    need(owner['plan'] == record(plan_path) and not state.get('CPU_source_seal_owner') and
         state['original_restored'] and not state['native_running'] and
         not state['model_loaded'] and not state['unknown_completion'],
         'Only the existing positively idle source owner may resume')
    a.out.mkdir(parents=True, exist_ok=False)
    save(a.out / 'intent.private.json', dict(publication=record(plan_path),
        interruption=record(a.interruption), preserved_positive_files=first,
        first_uncompleted_file=first + 1, completed_payload_retransmissions=0,
        automatic_retries=0, native_submissions=0, GPU_calls=0))
    owner.update(phase='interrupted-source-suffix', continuation=str(a.out))
    state_path.write_text(json.dumps(state, indent=2) + '\n', encoding='utf-8')
    lan = lan_module()
    with lan.ftplib.FTP() as ftp:
        ftp.connect(lan.HOST, 2121, timeout=30)
        ftp.login()
        need(ftp.sendcmd('SELF') == '226 SELF transfer mode disabled', 'Raw transfer mode required')
        ftp.voidcmd('TYPE I')
        partial = files[first]
        need(partial['physical'].startswith(plan['directory'].rstrip('/') + '/'),
             'The partial file must be inside this exact owned publication')
        try:
            partial_bytes = ftp.size(partial['physical'])
        except lan.ftplib.error_perm as error:
            need(str(error).startswith('550'), 'Only absence is an accepted missing partial')
            partial_bytes = None
        need(partial_bytes is None or 0 <= partial_bytes <= partial['local']['bytes'],
             'The interrupted file must have a bounded partial size')
        partial_removed = partial_bytes is not None
        save(a.out / 'partial-observation.private.json', dict(
            path=partial['physical'], observed_bytes=partial_bytes,
            expected_bytes=partial['local']['bytes'], preserved_positive_files=first))
        if partial_removed:
            reply = ftp.sendcmd('DELE ' + partial['physical'])
            need(reply.startswith(('226 ', '250 ')), 'The exact owned partial must retire positively')
        for i in range(first, len(files)):
            f = files[i]
            verify_input(f)
            lan.absent(f['physical'])
            with Path(f['local']['path']).open('rb') as stream:
                reply = ftp.storbinary('STOR ' + f['physical'], stream, 65536)
            need(reply.startswith(('226 ', '250 ')), 'The complete suffix store must finish positively')
            row = dict(uploaded_file=i + 1, total=len(files), bytes=f['local']['bytes'])
            rows.append(row)
            temporary = a.out / 'progress.next.private.json'
            temporary.write_text(json.dumps(dict(rows=rows, completed=False)) + '\n', encoding='utf-8')
            temporary.replace(a.out / 'progress.private.json')
            print(json.dumps(row), flush=True)
    save(a.out / 'result.private.json', dict(complete=True, exit_code=0, rows=rows,
        expected_quarantined_helper_error=False, resumed_after_source_disconnect=True,
        publication=record(plan_path), interruption=record(a.interruption),
        preserved_positive_files=first, completed_payload_retransmissions=0,
        interrupted_file_restarts=int(partial_removed), native_submissions=0,
        automatic_retries=0, GPU_calls=0))


if __name__ == '__main__':
    main()
