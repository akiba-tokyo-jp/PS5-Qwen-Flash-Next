#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Run one independent CPU loader measurement and ordinarily restore production."""
import argparse
import json
from pathlib import Path
import secrets
import struct
import time
import urllib.error
import urllib.parse

from build_performance_quantizer import record
from kernel_vm_preflight import query
from run_successful_model_case import publish
from start_success_route import load, need, save
from success_case_control import PHYSICAL, build, current_files, execute, lan_module


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('workspace', 'current', 'mount-plan', 'package', 'direct-staging-proof', 'out'):
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--execute', action='store_true')
    p.add_argument('--external-rodata-controls',type=Path)
    p.add_argument('--native-VM-proof',type=Path)
    p.add_argument('--cold-payload-proof',type=Path,help='Reuse only the already sealed exact unchanged prototype payload')
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=False)
    package = load(a.package)
    need(package['completed'] and package['CPU_only'] and not package['driver_code_linked'] and
         package['normalized_SELF_roundtrip_equal'] and package['CPU_libc_parameter_policy']['selected_heap_size'] == 8 << 20,
         'The separately audited8MiB CPU-only package is required')
    relink = load(package['relink']['path'])
    need(record(package['relink']['path']) == package['relink'] and not relink['model_engine_linked'] and
         relink['context_controls'] == relink['libc_parameter_controls'] == 8 and
         {'malloc', 'free'} <= relink['real_module_import_audit']['resolved'].keys(),
         'Actual CPU source and non-eliminated small libc allocation required')
    image = package['SELF']
    need(record(image['path']) == image and image['bytes'] <= 4 << 20, 'Exact independently bounded CPU SELF required')
    cold=package.get('external_rodata_probe')
    if cold:
        need(a.external_rodata_controls is not None and a.native_VM_proof is not None,
             'New restorer fault controls and the qualified shell-free VM reader are required')
        controls=load(a.external_rodata_controls)
        need(controls['completed'] and controls['relink']==package['relink'] and controls['positive_controls']==2 and
             controls['negative_controls']==18 and controls['zero_link_native_title_view_qualified'] and
             all(record(controls[k]['path'])==controls[k] for k in ('source','test')) and
             cold==relink['external_rodata_probe'] and cold['payload']['bytes']==8<<20 and
             record(cold['payload']['path'])==cold['payload'] and cold['layout']['external_range_has_no_LOAD_coverage'],
             'Exact standalone payload, actual restorer controls and the absent LOAD range are required')
    state_path = a.current / 'active-console.private.json'
    state = load(state_path)
    need(state['original_restored'] and not state['native_running'] and not state['model_loaded'] and
         not state['unknown_completion'], 'Positively idle current deployment required')
    # An operational screen for this different, driver-free C program. No old
    # model threshold is reduced, no inactive pages count as free, and the
    # encoded libc parameter is not claimed to bound all kernel allocations.
    raw = Path(relink['artifact']['path']).read_bytes()
    offset = struct.unpack_from('<Q', raw, 32)[0]
    stride, count = struct.unpack_from('<HH', raw, 54)
    headers = [struct.unpack_from('<IIQQQQQQ', raw, offset + i * stride) for i in range(count)]
    load_pages = sum((h[6] + 16383) // 16384 for h in headers if h[0] == 1)
    required = 898 + 256 + 512 + load_pages + 1024
    if cold:required+=512
    pricing = dict(CPU_only=True, ordinary_model_screen_unchanged=7374,
        OS_minimum=898, operational_reserve=256, encoded_libc_heap_pages=512,
        actual_ELF_LOAD_pages=load_pages, independent_process_allowance_pages=1024,
        selected_CPU_scope_screen_pages=required, universal_kernel_allocation_bound_claimed=False,
        inactive_pages_counted_as_free=False, source_workers=0, GPU_calls=0)
    if cold:pricing.update(new_Direct_metadata_allowance_pages=512,external_readonly_CPU_bytes=8<<20,
        original_CPU_scope_rule_preserved=True,empirical_previous_loader_global_drop_pages=3428,
        previous_global_drop_is_not_an_exclusive_allocation_bound=True)
    save(a.out / 'pricing.private.json', pricing)
    if not a.execute:
        print(json.dumps(dict(prepared=True, pricing=pricing, PS5_operations=0)))
        return
    lan = lan_module()
    vm_dir = a.out / 'VM-before'
    if a.native_VM_proof:
        proof=load(a.native_VM_proof)
        need(proof['completed'] and proof['shell_commands']==proof['title_launches']==proof['GPU_calls']==0 and
             proof['same_original_counter_names_sizes_and_shape_review'], 'Qualified original-size native VM reader required')
        from native_VM_observation import query as native_query
        before=native_query(a.workspace,a.current,a.mount_plan,a.out/'native-VM-observation')
    else:
        vm_dir.mkdir()
        before = query(lan.HOST, vm_dir)
    if not vm_dir.exists():vm_dir.mkdir()
    need(before['boot_before'] == before['boot_after'] == state['current_boot'] and before['minimum'] == 898 and
         before['page_bytes'] == 16384, 'Exact current native CPU geometry required')
    admitted = min(before['free_first'], before['free_last']) >= required
    save(vm_dir / 'result.private.json', dict(completed=True, observations=before, pricing=pricing,
        admitted=admitted, title_launches=0, GPU_calls=0))
    need(admitted, 'Independent CPU scope refuses before any publication or launch')
    if cold:
        if a.cold_payload_proof:
            prior=load(a.cold_payload_proof)
            need(prior['completed'] and all(prior['pack'][k]==cold['payload'][k] for k in ('bytes','sha256')) and prior['whole_SHA256_both_namespaces'] and
                prior['immutable_mode']==292 and prior['current_seven_unchanged'] and prior['target']==PHYSICAL+cold['application_path'][5:],
                'Only the exact already sealed CPU payload may be reused')
            save(a.out/'cold-payload-reuse.private.json',dict(completed=True,prior=record(a.cold_payload_proof),
                payload=cold['payload'],new_transfers=0,new_publications=0,fresh_native_whole_SHA_before_use_required=True))
        else:
            from publish_cold_rodata_payload import publish_payload
            publish_payload(a,lan,cold,current_files(a.current),a.out/'cold-payload')
    run = secrets.token_hex(16)
    report = '/app0/qwen-runtime/plan-' + run + '.json'
    policy = dict(schema='ps5-qwen-CPU-loader-v1', run_id=run, SELF_bytes=image['bytes'],
                  SELF_sha256=image['sha256'], heap_bytes=8 << 20)
    policy_path = a.out / 'development.json'
    policy_path.write_text(json.dumps(policy, separators=(',', ':')) + '\n', encoding='utf-8', newline='\n')
    old = current_files(a.current)
    replacements = [dict(image, remote=old[0]['remote']), old[1], dict(record(policy_path), remote=old[2]['remote'])]
    new = replacements + old[3:]
    prefix = '/data/ai/moss-qwen-case-' + run
    pending = [dict(row, target=row['remote'], remote=prefix + ('-candidate-SELF.bin' if i == 0 else '-' + str(i) + '.json'))
               for i, row in enumerate(replacements)]
    publication = build(a.workspace, a.mount_plan, old, new, pending, 'publish', a.out / 'publication')
    launch = build(a.workspace, a.mount_plan, new, new, [], 'launch', a.out / 'launch')
    save(a.out / 'plan.private.json', dict(completed=True, package=record(a.package), run_id=run,
        report=report, SELF=image, old_files=old, new_files=new, pending=pending, CPU_only=True,
        source_payload_reads=128 if cold else 0, GPU_calls=0, maximum_title_launches=1, initializer_requests=0,
        ordinary_close_and_exact_production_restore_required=True))
    state['active_successful_native_case'] = dict(plan=record(a.out / 'plan.private.json'), run_id=run, phase='CPU-loader-publication')
    state['state'] = 'independent_CPU_loader_publication_in_progress'
    state_path.write_text(json.dumps(state, indent=2) + '\n')
    direct = dict(workspace=a.workspace, mount_plan=a.mount_plan, qualified=a.direct_staging_proof)
    print(json.dumps(dict(phase='CPU-only-publication', screen=required, observed_free=before['free_last'])), flush=True)
    publish(lan, pending, publication, a.out / 'publication', direct_staging=direct)
    state.update(original_restored=False, temporary_installed_SELF=image)
    state_path.write_text(json.dumps(state, indent=2) + '\n')
    print(json.dumps(dict(phase='ordinary-CPU-title-launch', maximum_calls=1)), flush=True)
    launched = execute(lan, launch, a.out / 'launch')
    need(launched['operation_calls'] == 1 and launched['app_id'] > 0, 'One accepted ordinary CPU launch required')
    state.update(native_running=True, unknown_completion=True)
    state['active_successful_native_case'].update(phase='CPU-loader-completion-pending', app_id=launched['app_id'])
    state_path.write_text(json.dumps(state, indent=2) + '\n')
    remote = PHYSICAL + report[5:]
    deadline = time.monotonic() + 60
    while True:
        try:
            first_raw = lan.web('/fs' + urllib.parse.quote(remote + '.first.start', safe='/'), 4096, 8)
            terminal_raw = lan.web('/fs' + urllib.parse.quote(remote, safe='/'), 4096, 8)
            first, terminal = json.loads(first_raw), json.loads(terminal_raw)
            need(first['run_id'] == terminal['run_id'] == run and first['SELF_sha256'] == terminal['SELF_sha256'] == image['sha256'] and
                 first['pid'] == terminal['pid'] and terminal['all_CPU_IO_returned'] and
                 terminal['GPU_calls'] == terminal['model_loads'] == terminal['source_workers'] == 0,
                 'Exact CPU owner, returned synchronous I/O and zero backend work required')
            break
        except urllib.error.HTTPError as error:
            need(error.code == 404, 'CPU report state is unknown')
        need(time.monotonic() < deadline, 'CPU completion unknown; retain this same process and do not resubmit')
        time.sleep(1)
    boot = state['current_boot']
    stage_remote = PHYSICAL + '/qwen-runtime/entry-b' + str(boot[0]) + '-' + str(boot[1]) + '-' + str(first['pid']) + '.stages'
    stages = lan.web('/fs' + urllib.parse.quote(stage_remote, safe='/'), 1 << 20, 8)
    marker = b'CPU_loader_footprint_returned_GPU_not_started_waiting_for_ordinary_close'
    need(stages.splitlines()[-1] == marker and stages.count(marker) == 1, 'The exact returned CPU-only terminal stage is required')
    reports = []
    for name, content, remote_path in (('native-first.private.json', first_raw, remote + '.first.start'),
                                        ('native-result.private.json', terminal_raw, remote),
                                        ('native-stages.private.log', stages, stage_remote)):
        path = a.out / name
        path.write_bytes(content)
        reports.append(dict(record(path), remote=remote_path))
    if cold:
        cold_raw=lan.web('/fs'+urllib.parse.quote(remote+'.cold',safe='/'),4096,8)
        cold_path=a.out/'native-cold.private.json';cold_path.write_bytes(cold_raw)
        reports.append(dict(record(cold_path),remote=remote+'.cold'))
        detail=lan.web('/fs'+urllib.parse.quote(remote+'.cold-source',safe='/'),4096,8)
        detail_path=a.out/'native-cold-source.private.json';detail_path.write_bytes(detail)
        reports.append(dict(record(detail_path),remote=remote+'.cold-source'))
    close_proof = dict(CPU_only=True, all_CPU_IO_returned=True, pid=first['pid'],
                       app_id=launched['app_id'], reports=reports)
    state.update(unknown_completion=False, native_owners=1, observed_native_pid=first['pid'])
    state_path.write_text(json.dumps(state, indent=2) + '\n')
    close = build(a.workspace, a.mount_plan, new, new, [], 'close', a.out / 'ordinary-close', close=close_proof)
    print(json.dumps(dict(phase='positive-CPU-completion-ordinary-close', native_completed=terminal['completed'])), flush=True)
    closed = execute(lan, close, a.out / 'ordinary-close')
    need(closed['operation_calls'] == 1, 'Exactly one ordinary close required')
    until = time.monotonic() + 15
    while True:
        with lan.OPENER.open('http://' + lan.HOST + ':8084/processes_list', timeout=8) as response:
            owners = [row for row in json.loads(response.read())['processes'] if row['name'] == 'eboot.bin']
        if not owners:
            break
        need(time.monotonic() < until, 'Ordinary CPU exit unknown; never repeat close')
        time.sleep(.25)
    need(old == current_files(a.current), 'Selected production inputs changed')
    restore_pending = [dict(row, target=row['remote'], remote=prefix + ('-restore-SELF.bin' if i == 0 else '-restore-' + str(i) + '.json'))
                       for i, row in enumerate(old[:3])]
    restoration = build(a.workspace, a.mount_plan, new, old, restore_pending, 'publish', a.out / 'restore')
    print(json.dumps(dict(phase='restore-exact-production')), flush=True)
    publish(lan, restore_pending, restoration, a.out / 'restore', direct_staging=direct)
    state.update(state='CPU_loader_returned_ordinary_exit_exact_current_restored', original_restored=True,
                 native_running=False, model_loaded=False, gateway_running=False, native_owners=0, unknown_completion=False)
    state.pop('temporary_installed_SELF', None)
    state['active_successful_native_case'].update(phase='CPU-loader-completed-ordinary-close-original-restored', native_pid=first['pid'])
    state_path.write_text(json.dumps(state, indent=2) + '\n')
    save(a.out / 'result.private.json', dict(completed=True, CPU_probe_passed=terminal['completed'],
        native=record(a.out / 'native-result.private.json'), before=record(vm_dir / 'result.private.json'),
        ordinary_exit_observed=True, ordinary_close_calls=1, current_seven_restored_and_native_hashed=True,
        observed_free_before=before['free_last'], observed_free_at_main=terminal['VM_main_free'],
        observed_global_startup_drop_pages=before['free_last'] - terminal['VM_main_free'],
        empirical_global_observation_not_exclusive_allocation=True, native_owners=0, unknown_completion=False,
        GPU_calls=0, model_loads=0, initializer_requests=0, model_launch_admission_granted=False))
    print(json.dumps(dict(completed=True, CPU_probe_passed=terminal['completed'], observed_before=before['free_last'],
        observed_main=terminal['VM_main_free'], observed_final=terminal['VM_final_free'],
        exact_current_restored=True, GPU_calls=0)), flush=True)


if __name__ == '__main__': main()
