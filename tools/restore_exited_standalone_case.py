#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Restore current files after observed standalone process exit, without inferring GPU completion."""
import argparse
import json
from pathlib import Path

from build_performance_quantizer import record
from run_successful_model_case import publish
from start_success_route import load, need, save
from success_case_control import build, current_files, lan_module


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('workspace', 'current', 'mount-plan', 'case', 'direct-staging-proof'):
        p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args()
    case = load(a.case / 'plan.private.json')
    first = load(a.case / 'observed-first.private.json')
    state_path = a.current / 'active-console.private.json'
    state = load(state_path)
    old = current_files(a.current)
    need(case['mode'] == 'GPU' and case['old_files'] == old and
         first['run_id'] == case['run_id'] and first['candidate_SELF_sha256'] == case['SELF']['sha256'] and
         state['active_successful_native_case']['run_id'] == case['run_id'] and
         state['temporary_installed_SELF'] == case['SELF'] and not state['original_restored'],
         'Only the exact installed standalone case and unchanged current files may be restored')
    publication = load(a.case / 'publication/result.private.json')
    launch = load(a.case / 'launch/result.private.json')
    need(publication['completed'] and publication['operation_calls'] == 3 and launch['completed'] and
         launch['operation_calls'] == 1 and launch['helper_exited'], 'Exact accepted publication and launch required')
    out = a.case / 'process-exited-restoration'
    out.mkdir(exist_ok=False)
    lan = lan_module()
    for phase in ('before', 'confirmed'):
        with lan.OPENER.open('http://' + lan.HOST + ':8084/processes_list', timeout=8) as response:
            raw = response.read(1 << 20)
        processes = json.loads(raw)['processes']
        need(not any(int(r['pid']) == first['pid'] or r['name'] == 'eboot.bin' for r in processes),
             'The same exited PID and all native application owners must be absent')
        (out / ('processes-' + phase + '.private.json')).write_bytes(raw)
    prefix = '/data/ai/moss-qwen-case-' + case['run_id']
    pending = [dict(r, target=r['remote'], remote=prefix +
        ('-restore-SELF.bin' if i == 0 else '-restore-' + str(i) + '.json')) for i, r in enumerate(old[:3])]
    plan = build(a.workspace, a.mount_plan, case['new_files'], old, pending, 'publish', out / 'restore')
    save(out / 'intent.private.json', dict(case=record(a.case / 'plan.private.json'),
        first=record(a.case / 'observed-first.private.json'), prior_publication=record(a.case / 'publication/result.private.json'),
        native_process_exit_observed=True, ordinary_exit_claimed=False, GPU_completion_inferred=False,
        native_close_calls=0, initializer_requests=0, automatic_retries=0))
    publish(lan, pending, plan, out / 'restore', direct_staging=dict(workspace=a.workspace,
        mount_plan=a.mount_plan, qualified=a.direct_staging_proof))
    result = dict(completed=True, native_process_exit_observed=True, exited_PID=first['pid'],
        exact_current_seven_restored_and_native_hashed=True, ordinary_exit_claimed=False,
        GPU_completion_inferred=False, GPU_retirement_readmission_pending=True,
        native_close_calls=0, title_launches=0, GPU_calls=0, initializer_requests=0, automatic_retries=0)
    save(out / 'result.private.json', result)
    state.update(state='standalone_process_exited_current_restored_GPU_completion_unclassified',
        original_restored=True, native_running=False, native_owners=0, model_loaded=False,
        unknown_completion=True, GPU_retirement_readmission_pending=True)
    state.pop('temporary_installed_SELF', None)
    state['active_successful_native_case'].update(phase='process-exited-current-restored-completion-unclassified',
        restoration=record(out / 'result.private.json'))
    state_path.write_text(json.dumps(state, indent=2) + '\n', newline='\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
