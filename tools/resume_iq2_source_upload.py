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
    p.add_argument('--capacity-reclaim-proof', type=Path)
    p.add_argument('--reserved-publication-plan', type=Path)
    p.add_argument('--preflight-only', action='store_true')
    a = p.parse_args()
    plan_path = a.publication / 'plan.private.json'
    plan = load(plan_path)
    interrupted = load(a.interruption)
    files = plan['files']
    disk_full = '550 No space left on device' in interrupted['terminal_output']
    rows = interrupted.get('rows', [])
    reclaim = None
    if disk_full:
        need(a.capacity_reclaim_proof and a.reserved_publication_plan and
             interrupted['publication'] == record(plan_path) and not interrupted['native_submitted'],
             'Disk-full continuation requires an exact retired writer and actual capacity reclamation')
        reclaim = load(a.capacity_reclaim_proof)
        native = reclaim['native']
        raw = Path(native['raw']['path']).read_text()
        need(reclaim['completed'] and reclaim['actual_allocation_release_verified'] and
             reclaim['all_current_and_prepared_sources_preserved'] and reclaim['authenticated_PC_originals_preserved'] and
             native['completed'] and native['helper_exited'] and native['helper_files_removed'] and
             native['operation_calls'] == reclaim['truncated_unused_chunks'] == 52 and
             raw.count('RECLAIM_CHUNK index=') == 52 and
             'RECLAIM_COMPLETE files=52 ' in raw and record(native['raw']['path']) == native['raw'],
             'Actual allocated-byte release and complete helper retirement must precede any suffix store')
        receipts = sorted(a.publication.glob('positive-store-*.private.json'))
        need([load(path) for path in receipts] == interrupted['positive_files'],
             'Preserve every durable positive whole-file store')
        rows = []
        for i, path in enumerate(receipts):
            receipt = load(path)
            need(receipt['completed'] and receipt['file'] == i and receipt['source'] == files[i]['local'] and
                 receipt['target'] == files[i]['physical'] and receipt['positive_reply'].startswith(('226 ', '250 ')),
                 'The exact completed prefix is immutable')
            rows.append(dict(uploaded_file=i + 1, total=len(files), bytes=files[i]['local']['bytes']))
        reserved = load(a.reserved_publication_plan)
        remaining = sum(f['local']['bytes'] for f in files[len(rows):])
        remaining += sum(f['local']['bytes'] for f in reserved['files'])
        need(reclaim['logical_bytes_released'] >= remaining + (1 << 30),
             'Reclaimed bytes alone must cover both remaining publications plus one GiB')
    first = len(rows)
    need(interrupted['complete'] and interrupted['exit_code'] != 0 and
         (disk_full or 'ConnectionResetError' in interrupted['terminal_output']) and
         not interrupted.get('expected_quarantined_helper_error', False),
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
    if a.preflight_only:
        print(json.dumps(dict(preflight_passed=True, preserved_positive_files=first,
            remaining_files=len(files) - first, PS5_calls=0, reserved_bytes=remaining if disk_full else None)))
        return
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
            need(not disk_full or owner.get('partial_retired_path') != partial['physical'],
                 'An already retired partial must not be deleted twice')
            reply = ftp.sendcmd('DELE ' + partial['physical'])
            need(reply.startswith(('226 ', '250 ')), 'The exact owned partial must retire positively')
        for i in range(first, len(files)):
            f = files[i]
            verify_input(f)
            lan.absent(f['physical'])
            sent, notice = 0, 16 << 20
            def progress(block):
                nonlocal sent, notice
                sent += len(block)
                if sent >= notice:
                    print(json.dumps(dict(uploading_file=i + 1, total=len(files), sent_bytes=sent,
                        file_bytes=f['local']['bytes'], additional_PS5_probes=0)), flush=True)
                    notice += 16 << 20
            with Path(f['local']['path']).open('rb') as stream:
                reply = ftp.storbinary('STOR ' + f['physical'], stream, 65536, callback=progress)
            need(reply.startswith(('226 ', '250 ')), 'The complete suffix store must finish positively')
            row = dict(uploaded_file=i + 1, total=len(files), bytes=f['local']['bytes'])
            rows.append(row)
            save(a.out / ('positive-store-' + str(i).zfill(3) + '.private.json'),
                 dict(completed=True, file=i, source=f['local'], target=f['physical'], positive_reply=reply))
            temporary = a.out / 'progress.next.private.json'
            temporary.write_text(json.dumps(dict(rows=rows, completed=False)) + '\n', encoding='utf-8')
            temporary.replace(a.out / 'progress.private.json')
            print(json.dumps(row), flush=True)
    save(a.out / 'result.private.json', dict(complete=True, exit_code=0, rows=rows,
        expected_quarantined_helper_error=False, resumed_after_source_disconnect=True,
        disk_full_resolved=disk_full,
        capacity_reclaim_proof=record(a.capacity_reclaim_proof) if reclaim else None,
        reserved_publication_plan=record(a.reserved_publication_plan) if reclaim else None,
        publication=record(plan_path), interruption=record(a.interruption),
        preserved_positive_files=first, completed_payload_retransmissions=0,
        interrupted_file_restarts=int(partial_removed), native_submissions=0,
        automatic_retries=0, GPU_calls=0))


if __name__ == '__main__':
    main()
