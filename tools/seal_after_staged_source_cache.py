#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Seal a preserved upload once after positively changed owned cache state."""
import argparse
import json
from pathlib import Path
import re
import time
import urllib.parse

from build_performance_quantizer import record
from publish_iq2_up_model_overlay import finish
from start_success_route import load, need, save
from success_case_control import ALIAS, build, complete, current_files, execute, lan_module


def sealed_geometry(publication, seal, cache_intent, cache):
    """Carry an actually consumed prefix through the sealer's metadata changes."""
    known = {row['path']: row for row in seal['parts']}
    candidates = [row for row in reversed(publication['files']) if row['local']['bytes'] == 235929600]
    need(len(candidates) == 48 and candidates == cache_intent['files'], 'Preserve the exact staged carrier order')
    files, windows = [], []
    for index, row in enumerate(candidates):
        source = known[row['application']]
        old = cache['staged_identities'][str(index)]
        new = source['identity']
        need(source['bytes'] == row['local']['bytes'] and source['sha256'] == row['local']['sha256'] and
             old == cache_intent['expected_staged_identities'][index] and
             old[2] == 0o100777 and new[2] == 0o100644 and
             all(old[field] == new[field] for field in (1, 3, 4, 5, 6, 7)),
             'Whole SHA/EOF sealing must preserve inode, ownership, size and mtime; only namespace/mode/ctime may change')
        files.append(dict(source, mounted_path=ALIAS + source['path'][5:]))
        windows += [dict(file=index, offset=offset, bytes=min(64 << 20, source['bytes'] - offset))
                    for offset in range(0, source['bytes'], 64 << 20)]
    need(windows == cache_intent['windows'], 'Do not reset or reorder any consumed cache window')
    return files, windows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('workspace', 'current', 'mount-plan', 'publication', 'staged-cache', 'followup-config', 'out'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--execute-prepared', action='store_true')
    args = parser.parse_args()
    publication_path = args.publication / 'plan.private.json'
    publication, cache = load(publication_path), load(args.staged_cache)
    cache_intent = load(args.staged_cache.parent / 'intent.private.json')
    old_result_path = args.publication / 'native/result.private.json'
    old_result, old_plan = load(old_result_path), load(args.publication / 'native/plan.private.json')
    need(not old_result['completed'] and old_result['operation_calls'] == 0 and
         old_result['helper_exited'] and old_result['helper_files_removed'] and
         cache_intent['memory_refusal'] == record(old_result_path) and
         cache_intent['publication'] == record(publication_path) and
         cache['completed'] and cache['native']['completed'] and cache['native']['helper_exited'] and
         cache['native']['helper_files_removed'] and cache['all_mappings_and_FDs_positively_retired'] and
         cache['sufficient_for_changed_sealer'] and cache['observations']['free_after'] >= 7374 and
         cache['starting_window'] == 0 and 0 < cache['observations']['scanned'] < 192 and
         cache['observations']['returned_error'] == 0 and cache['source_writes'] == 0,
         'Only positive newly retired source pages may change the returned zero-operation sealing refusal')
    state_path = args.current / 'active-console.private.json'
    state = load(state_path)
    need(state['original_restored'] and not state['native_running'] and not state['model_loaded'] and
         not state['unknown_completion'] and not state.get('CPU_source_seal_owner') and
         state['source_publication_owner']['plan'] == record(publication_path) and
         state['source_publication_owner']['staged_cache_results'] == [record(args.staged_cache)] and
         cache_intent['boot'] == state['current_boot'], 'The same positively idle source owner must remain reserved')
    selected = current_files(args.current)
    need(old_plan['old_files'] == old_plan['new_files'] == selected and
         not (args.publication / 'result.private.json').exists(), 'The original current application must remain selected')
    original_context = Path(old_plan['context']['path']).read_text(encoding='utf-8')
    first = original_context.index('#define SHARED_Q4_FILE_COUNT ')
    last = original_context.index('\n#include "shared_q4_publication.h"', first)
    context = original_context[first:last]
    config = load(args.followup_config)
    need(config['cache_pools'][0]['scope'] == 'Down48' and
         Path(config['cache_pools'][0]['publication']) == args.publication / 'result.private.json' and
         not config['cache_pools'][0]['completed_scopes'], 'The queued successor must accept this exact new Down prefix once')
    facts = dict(publication=record(publication_path), returned_original_sealer=record(old_result_path),
                 staged_cache=record(args.staged_cache), selected=selected, boot=state['current_boot'],
                 original_context=record(old_plan['context']['path']), successor_config=record(args.followup_config),
                 source=record(Path(__file__)), original_sealer_submissions=1, changed_state_sealer_submissions=1,
                 total_source_sealer_submissions=2, source_payload_retransmissions=0,
                 readiness_pages_unchanged=7374, cache_prefix_must_transfer_before_owner_release=True)
    if not args.execute_prepared:
        args.out.mkdir(parents=True, exist_ok=False)
        native = build(args.workspace, args.mount_plan, selected, selected, [], 'seal-shared-Q4',
            args.out / 'native', source_seal_context=context,
            source_seal_window_proof=Path(old_plan['qualified_large_window']['path']))
        actual_context = Path(native['context']['path']).read_text(encoding='utf-8')
        need(native['whole_integrity_window_bytes'] == 262144 and native['CPU_metadata_margin_pages'] == 97 and
             native['minimum_live_free_pages'] == 1201 and not native['CPU_control_independent_thresholds'] and
             context == actual_context[actual_context.index('#define SHARED_Q4_FILE_COUNT '):
                 actual_context.index('\n#include "shared_q4_publication.h"')],
             'The full original source seal context and all original stronger memory/IO guards must stay exact')
        save(args.out / 'intent.private.json', dict(facts, native_plan=record(args.out / 'native/plan.private.json')))
        print(json.dumps(dict(prepared=True, original_context_exact=True, metadata_margin=97, minimum_free_pages=1201, PS5_operations=0)))
        return
    intent = load(args.out / 'intent.private.json')
    need(all(intent[key] == value for key, value in facts.items()) and
         intent['native_plan'] == record(args.out / 'native/plan.private.json'), 'The exact changed-state source handoff changed')
    native = load(args.out / 'native/plan.private.json')
    state['CPU_source_seal_owner'] = dict(plan=intent['native_plan'], publication=str(args.publication),
        phase='changed-owned-cache-full-source-seal', ordinary_helper_completion_pending=True, GPU_calls=0, title_launches=0)
    state['source_publication_owner']['phase'] = 'changed-owned-cache-full-source-seal'
    state_path.write_text(json.dumps(state, indent=2) + '\n', encoding='utf-8')
    lan = lan_module()
    try:
        result = execute(lan, native, args.out / 'native', observation_seconds=1)
    except RuntimeError:
        need((args.out / 'native/execution/execution.once.private.json').exists() and
             not (args.out / 'native/result.private.json').exists(), 'Only collect this same submitted source helper')
        deadline = time.monotonic() + 1800
        for interval in range(7):
            print(json.dumps(dict(phase='same-source-sealer-quiet-collection', quiet_seconds_remaining=350 - interval * 50,
                                  additional_PS5_probes=0, native_resubmissions=0)), flush=True)
            time.sleep(50)
        while True:
            raw = lan.web('/fs' + urllib.parse.quote(native['log'], safe='/'), 64 << 20, 8)
            if re.search(rb'\nEND success=\d+ operation_calls=\d+ app_id=-?\d+ log_healthy=\d+ GPU_calls=0 initializer_requests=0 mount_calls=0\n$', raw):
                raw_path = args.out / 'native/late-console.private.log'
                raw_path.write_bytes(raw)
                result = complete(lan, native, args.out / 'native', raw, raw_path)
                break
            need(time.monotonic() < deadline, 'Retain the same unknown source helper; never resubmit it')
            print(json.dumps(dict(same_helper_pending=True, journal_bytes=len(raw), quiet_seconds=180)), flush=True)
            for _ in range(3):
                time.sleep(min(60, max(0, deadline - time.monotonic())))
    need(result['completed'] and result['helper_exited'] and result['helper_files_removed'], 'The exact source helper must positively retire')
    handoff = args.out / 'positive-seal-handoff.private.json'
    save(handoff, dict(intent=record(args.out / 'intent.private.json'), native_result=record(args.out / 'native/result.private.json'),
                       total_source_sealer_submissions=2, original_sealer_operations=0, source_payload_retransmissions=0))
    finish(args.publication, Path(publication['preparation']['path']), publication, result,
           native_result_path=args.out / 'native/result.private.json', source_handoff=handoff)
    published = load(args.publication / 'result.private.json')
    seal = load(published['source_integrity']['path'])
    files, windows = sealed_geometry(publication, seal, cache_intent, cache)
    bridge = args.out / 'sealed-cache-prefix'
    bridge.mkdir(exist_ok=False)
    save(bridge / 'intent.private.json', dict(publication=record(args.publication / 'result.private.json'),
        plan=record(publication_path), files=files, windows=windows, starting_window=0, boot=state['current_boot'],
        selected=selected, publication_scope='Down48', staged_cache=record(args.staged_cache),
        retirement_performed_before_sealing=True, native_data_operations_unchanged=True,
        inode_ownership_size_mtime_and_whole_SHA_EOF_bound=True, expected_mode_transition='0777 to0644; ctime changes permitted'))
    save(bridge / 'result.private.json', dict(completed=True, native=cache['native'], observations=cache['observations'],
        starting_window=0, remaining_windows=cache['remaining_windows'], all_mappings_and_FDs_positively_retired=True,
        source_writes=0, staged_cache=record(args.staged_cache), retirement_performed_before_sealing=True,
        whole_source_seal=published['source_integrity'], cache_windows_replayed=0, model_launch_admission=False))
    save(args.out / 'successor-config-before.private.json', config)
    config['cache_pools'][0]['completed_scopes'] = [str(bridge / 'result.private.json')]
    temporary = args.followup_config.with_name(args.followup_config.name + '.staged-prefix.tmp')
    temporary.write_text(json.dumps(config, indent=2) + '\n', encoding='utf-8')
    temporary.replace(args.followup_config)
    save(args.out / 'result.private.json', dict(completed=True, publication=record(args.publication / 'result.private.json'),
        native_result=record(args.out / 'native/result.private.json'), consumed_cache_prefix=record(bridge / 'result.private.json'),
        successor_config=record(args.followup_config), total_source_sealer_submissions=2, payload_retransmissions=0,
        source_sealer_minimum_pages_unchanged=1201, model_readiness_pages_unchanged=7374))
    state = load(state_path)
    need(state['CPU_source_seal_owner']['plan'] == intent['native_plan'] and
         state['source_publication_owner']['plan'] == record(publication_path), 'Never release another source owner')
    state.pop('CPU_source_seal_owner')
    state.pop('source_publication_owner')
    state_path.write_text(json.dumps(state, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(completed=True, source_files=len(publication['files']), original_source_writes=0,
        total_source_sealer_submissions=2, consumed_cache_windows_preserved=cache['observations']['scanned'],
        queued_successor_released=True)), flush=True)


if __name__ == '__main__':
    main()
