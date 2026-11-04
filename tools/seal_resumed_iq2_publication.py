#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Submit an existing unconsumed source sealer after its complete suffix transfer."""
import argparse
import json
from pathlib import Path
import re
import time
import urllib.parse

from build_performance_quantizer import record
from publish_iq2_up_model_overlay import finish
from start_success_route import load, need, save
from success_case_control import complete, current_files, execute, lan_module


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('current', 'publication', 'transfer-proof'):
        p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args()
    publication_path = a.publication / 'plan.private.json'
    publication = load(publication_path)
    transfer = load(a.transfer_proof)
    rows = transfer['rows']
    need(transfer['complete'] and transfer['exit_code'] == 0 and
         transfer['publication'] == record(publication_path) and
         transfer['native_submissions'] == transfer['completed_payload_retransmissions'] == 0 and
         [r['uploaded_file'] for r in rows] == list(range(1, len(publication['files']) + 1)) and
         all(r['total'] == len(rows) and r['bytes'] == f['local']['bytes'] for r, f in zip(rows, publication['files'])),
         'Every exact whole-file store must complete before this one native submission')
    interrupted = load(transfer['interruption']['path'])
    need(record(transfer['interruption']['path']) == transfer['interruption'], 'The source interruption proof changed')
    if transfer.get('disk_full_resolved'):
        need('550 No space left on device' in interrupted['terminal_output'] and
             record(transfer['capacity_reclaim_proof']['path']) == transfer['capacity_reclaim_proof'] and
             load(transfer['capacity_reclaim_proof']['path'])['completed'], 'Positive disk reclamation must remain bound')
    else:
        need('ConnectionResetError' in interrupted['terminal_output'], 'Only a qualified retired source failure may hand off')
    native_dir = a.publication / 'native'
    plan_path = native_dir / 'plan.private.json'
    plan = load(plan_path)
    need(plan['operation'] == 'seal-shared-Q4' and plan['whole_integrity_window_bytes'] == 262144 and
         plan['CPU_metadata_margin_pages'] == 97 and not plan['CPU_control_independent_thresholds'] and
         plan['full_physical_alias_SHA256_EOF_unchanged'] and
         plan['old_files'] == plan['new_files'] == current_files(a.current) and
         not (native_dir / 'execution/execution.once.private.json').exists() and
         not (native_dir / 'result.private.json').exists(), 'Only the exact stronger unconsumed prepared sealer may run')
    for key in ('artifact', 'controller', 'context', 'source', 'project_source'):
        need(record(plan[key]['path']) == plan[key], 'A prepared native sealing input changed')
    state_path = a.current / 'active-console.private.json'
    state = load(state_path)
    need(state['original_restored'] and not state['native_running'] and not state['model_loaded'] and
         not state['unknown_completion'] and not state.get('CPU_source_seal_owner') and
         state['source_publication_owner']['plan'] == record(publication_path), 'The same idle source owner must hand off')
    handoff = a.publication / 'resumed-seal-handoff.private.json'
    save(handoff, dict(completed=True, publication=record(publication_path), transfer=record(a.transfer_proof),
         native_plan=record(plan_path), native_submissions=1, payload_retransmissions=0))
    state['CPU_source_seal_owner'] = dict(plan=record(plan_path), publication=str(a.publication),
        GPU_calls=0, title_launches=0, ordinary_helper_completion_pending=True)
    state_path.write_text(json.dumps(state, indent=2) + '\n', encoding='utf-8')
    lan = lan_module()
    try:
        result = execute(lan, plan, native_dir, observation_seconds=1)
    except RuntimeError:
        need((native_dir / 'execution/execution.once.private.json').exists() and
             not (native_dir / 'result.private.json').exists(), 'Only the same submitted helper may be collected')
        deadline = time.monotonic() + 1800
        print(json.dumps(dict(submitted_once=True, quiet_seconds=350, native_resubmissions=0)), flush=True)
        time.sleep(350)
        while True:
            raw = lan.web('/fs' + urllib.parse.quote(plan['log'], safe='/'), 64 << 20, 8)
            if re.search(rb'\nEND success=\d+ operation_calls=\d+ app_id=-?\d+ log_healthy=\d+ GPU_calls=0 initializer_requests=0 mount_calls=0\n$', raw):
                path = native_dir / 'late-console.private.log'
                path.write_bytes(raw)
                result = complete(lan, plan, native_dir, raw, path)
                break
            need(time.monotonic() < deadline, 'Retain the same unknown sealer; never resubmit')
            print(json.dumps(dict(same_helper_pending=True, journal_bytes=len(raw), quiet_seconds=180)), flush=True)
            time.sleep(min(180, max(0, deadline - time.monotonic())))
    need(result['completed'] and result['helper_exited'] and result['helper_files_removed'], 'Positive sealing retirement is required')
    finish(a.publication, Path(publication['preparation']['path']), publication, result, source_handoff=handoff)
    state = load(state_path)
    need(state['CPU_source_seal_owner']['plan'] == record(plan_path) and
         state['source_publication_owner']['plan'] == record(publication_path), 'Never clear another IO owner')
    state.pop('CPU_source_seal_owner')
    state.pop('source_publication_owner')
    state_path.write_text(json.dumps(state, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(completed=True, physical_alias_SHA256_EOF=True, native_submissions=1, payload_retransmissions=0)))


if __name__ == '__main__':
    main()
