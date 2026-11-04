#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Ordinarily close the source-bound returned IQ2 guard and restore current P1."""
import argparse
import copy
import json
from pathlib import Path
import time
import urllib.parse

from build_performance_quantizer import record
from iq2_route_refusal import ENTRY_SHA, SELF_SHA, audit, close_proof_valid
from run_native_paired_down import completed_operation
from run_successful_model_case import publish
from start_success_route import load, need, save
from success_case_control import PHYSICAL, build, current_files, lan_module


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('workspace', 'current', 'mount-plan', 'case-plan', 'build-proof', 'direct-staging-proof', 'out'):
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--execute', action='store_true')
    a = p.parse_args()
    case, built = load(a.case_plan), load(a.build_proof)
    first = load(a.case_plan.parent / 'native-first-start.private.json')
    launch = load(a.case_plan.parent / 'launch/result.private.json')
    package = load(case['package']['path'])
    link = load(package['relink']['path'])
    source = Path(package['relink']['path']).parent.parent / 'entry.private.cpp'
    obj = source.with_name('entry.o')
    need(case['SELF']['sha256'] == first['candidate_SELF_sha256'] == SELF_SHA and
         first['run_id'] == case['run_id'] and launch['completed'] and launch['operation_calls'] == 1 and
         built['packages']['candidate'] == case['package'], 'The exact consumed candidate must remain bound')
    for row in (case['SELF'], case['package'], package['relink']):
        need(record(row['path']) == row, 'A consumed application input changed')
    need(record(source)['sha256'] == ENTRY_SHA and record(obj) in link['new_inputs'] and
         link['link_command'].count(str(obj)) == 1, 'The exact compiled entry must be linked')
    need(any('-c' in c and '-o' in c and c[c.index('-c') + 1] == str(source) and
             c[c.index('-o') + 1] == str(obj) for c in built['commands']),
         'The recorded actual compiler command must bind this source and object')
    text = source.read_text(encoding='utf-8')
    need('uploaded!=misses*1536000ull+result.predictive_bytes' in text and
         'if(native_resources_started){qwen_native_driver_retain();engine.release();}' in text and
         text.index('routes[ordinal]=completed_route_evidence(') <
         text.index('if(!routes[ordinal].complete)throw std::runtime_error("Complete actual additional routes required");') and
         text.index('resident_additional_exception_work_stopped') < text.index('engine.release();', text.index('resident_additional_exception_work_stopped')),
         'The CPU accounting guard and intentional owner retention must be exact')
    local_failure = a.case_plan.parent / 'native.failure.private.json'
    local_stages = a.case_plan.parent / 'native-stages.private.log'
    failure, stages = load(local_failure), local_stages.read_bytes()
    audit(stages, failure)
    mutations = [lambda s, f: (s + b'\nnative_driver_single_producer_entered\n', f),
        lambda s, f: (s.replace(b'first_generation_request_reset_completed', b'missing_reset'), f),
        lambda s, f: (s.replace(b'native_driver_producer_completed_resources_owned\n', b'', 1), f),
        lambda s, f: (s + b'first_generation_intent_persisted\n', f),
        lambda s, f: (s, dict(f, CPU_worker_completion_unknown=True)),
        lambda s, f: (s, dict(f, model_loaded=False)),
        lambda s, f: (s, dict(f, message='different failure'))]
    for mutate in mutations:
        ss, ff = mutate(stages, copy.deepcopy(failure))
        try:
            audit(ss, ff)
        except RuntimeError:
            pass
        else:
            raise AssertionError('A differently completed owner must refuse')
    a.out.mkdir(parents=True, exist_ok=False)
    state_path = a.current / 'active-console.private.json'
    state = load(state_path)
    need(state['active_successful_native_case']['run_id'] == case['run_id'] and
         state['unknown_completion'] and not state['original_restored'] and
         not state.get('source_publication_owner') and not state.get('CPU_source_seal_owner'),
         'Only the exact parked exception owner may close')
    lan = lan_module()
    base = PHYSICAL + case['report'][5:]
    boot = state['current_boot']
    remote_stages = PHYSICAL + '/qwen-runtime/entry-b' + str(boot[0]) + '-' + str(boot[1]) + '-' + str(first['pid']) + '.stages'
    remote = lambda path: lan.web('/fs' + urllib.parse.quote(path, safe='/'), 8 << 20)
    need(remote(base + '.failure') == local_failure.read_bytes() and remote(remote_stages) == stages,
         'The actual parked failure and stage sequence must remain unchanged')
    time.sleep(.25)
    need(remote(remote_stages) == stages, 'The exact positive idle journal must remain parked')
    reports = []
    for name, raw, target in [('failure', local_failure.read_bytes(), base + '.failure'), ('stages', stages, remote_stages)]:
        path = a.out / (name + '.private.log')
        path.write_bytes(raw)
        reports.append(dict(record(path), remote=target))
    proof = dict(known_IQ2_post_request_route_accounting_refusal=True, model_loaded=True,
        completed_requests=1, completed_GPU_epochs=30, completed_token_records=22,
        post_reset_GPU_submissions=0, all_source_IO_completed=True, CPU_worker_completion_unknown=False,
        source_audit_SHA256=ENTRY_SHA, SELF_SHA256=SELF_SHA, pid=first['pid'],
        app_id=launch['app_id'], reports=reports)
    need(close_proof_valid(proof), 'The narrow ordinary-close contract must pass')
    save(a.out / 'source-audit.private.json', dict(completed=True, source=record(source), entry=record(obj),
        build=record(a.build_proof), proof=proof, positive_controls=1, negative_controls=7,
        model_and_device_backing_retained_until_ordinary_OS_exit=True,
        preclose_zero_device_ledger_claimed=False))
    plan = build(a.workspace, a.mount_plan, case['new_files'], case['new_files'], [],
                 'close', a.out / 'ordinary-close', close=proof)
    if not a.execute:
        return
    result = completed_operation(lan, plan, a.out / 'ordinary-close')
    need(result['operation_calls'] == 1, 'Exactly one ordinary close may run')
    deadline = time.monotonic() + 15
    while True:
        with lan.OPENER.open('http://' + lan.HOST + ':8084/processes_list', timeout=8) as response:
            owners = [r for r in json.loads(response.read())['processes'] if r['name'] == 'eboot.bin']
        if not owners:
            break
        need(time.monotonic() < deadline, 'Ordinary exit remains unknown; never repeat the close')
        time.sleep(.25)
    old = current_files(a.current)
    need(old == case['old_files'], 'The selected current inputs changed')
    prefix = '/data/ai/moss-qwen-case-' + case['run_id']
    pending = [dict(row, target=row['remote'], remote=prefix + ('-restore-SELF.bin' if i == 0 else '-restore-' + str(i) + '.json')) for i, row in enumerate(old[:3])]
    restore = build(a.workspace, a.mount_plan, case['new_files'], old, pending, 'publish', a.out / 'restore')
    publish(lan, pending, restore, a.out / 'restore', direct_staging=dict(
        workspace=a.workspace, mount_plan=a.mount_plan, qualified=a.direct_staging_proof))
    result_path = a.out / 'result.private.json'
    save(result_path, dict(completed=True, ordinary_OS_closes=1, ordinary_exit_observed=True,
        current_seven_restored_and_native_hashed=True, all_five_initialization_GPU_epochs_completed=False,
        target_request_operations=1, completed_GPU_epochs=30, completed_token_records=22,
        IQ2_post_request_route_accounting_refusal=True, post_reset_GPU_submissions=0,
        source_audit=record(a.out / 'source-audit.private.json'), native_owners=0, unknown_completion=False,
        GPU_capacity_readmission_pending=True, initializer_requests=0, automatic_retries=0))
    state.update(state='IQ2_route_accounting_refusal_ordinarily_closed_current_restored', original_restored=True,
        native_running=False, model_loaded=False, native_owners=0, unknown_completion=False,
        GPU_retirement_readmission_pending=True, GPU_retirement_readmission_proof=record(result_path))
    state.pop('temporary_installed_SELF', None)
    state['active_successful_native_case']['phase'] = 'IQ2-route-accounting-refusal-ordinary-close-current-restored'
    state_path.write_text(json.dumps(state, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(completed=True, ordinary_close=1, current_restored=True, GPU_calls=0)), flush=True)


if __name__ == '__main__':
    main()
