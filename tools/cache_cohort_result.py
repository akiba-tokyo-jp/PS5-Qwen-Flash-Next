#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Review one frozen A53/B128/B128/A53 cohort offline; never deploy or launch.

Each arm binds the raw result, independent native binding, published policy,
app configuration and every result sidecar by path/size/SHA256. Existing native
numerical, source, resource, route and performance reviewers remain mandatory.
A speed decision is separate from ordinary-close and production-placement proof.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path

from cache128_result import CACHE_BYTES, digest
from expert_route_result import validate_routes
from first_generation_result import integer, read_record, require, validate
from performance_result import validate_backpressure, validate_first_performance, validate_performance

ORDER = (53, 128, 128, 53)
TIMING = 'first_to_last_generated_token_including_intervening_IO_and_backend_work'


def captured(row, root):
    require(type(row) is dict and set(row) == {'path', 'bytes', 'sha256'}, 'Exact evidence capture required')
    require(type(row['path']) is str and row['path'] and integer(row['bytes'], 1, 32 << 20)
        and digest(row['sha256']), 'Invalid bounded evidence capture')
    path = (root / row['path']).resolve()
    require(path.is_file() and path.stat().st_size == row['bytes'], 'Captured evidence size differs')
    require(hashlib.sha256(path.read_bytes()).hexdigest() == row['sha256'], 'Captured evidence SHA256 differs')
    return path


def canonical(value):
    # JSON equality must not accept true as an integer or ignore an extra key.
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def comparable_policy(policy, expected, slots):
    policy = copy.deepcopy(policy)
    gate = policy['native_first_generation_validation']
    require(gate['run_id'] == expected['run_id'] and
        gate['candidate_SELF_sha256'] == expected['candidate_SELF_sha256'] and
        gate['model_receipt_sha256'] == expected['model_receipt_sha256'], 'Published policy producer differs')
    require(gate['persistent_caches_enabled'] is False, 'Persistent caches must remain disabled')
    gate['run_id'] = '<cohort-arm>'
    for key in ('native_model_checkpoint_validation', 'native_prefix_validation',
                'native_model_free_speculation', 'native_padded_bank_layout_probe'):
        require(key not in policy, 'The cache comparison cannot combine another experiment')
    padded = policy['native_padded_expert_cache']
    require(padded.get('active_slots') == slots and type(padded.get('active_slots')) is int,
        'Published cache capacity differs')
    if slots == 128:
        require('cache128' in expected, 'An independent expanded-cache binding is required')
        proof = expected['cache128']['layout_qualification']
        scope = dict(schema='ps5-qwen-cache-128-experiment-v1', stage='model', active_slots=128,
            physical_planes=129, cache_request_bytes=CACHE_BYTES, context_tokens=256,
            context_allowance_bytes=256 << 20, CPU_heap_cap_bytes=512 << 20,
            device_ledger_cap_bytes=1792 << 20, precision_unchanged=True, automatic_retries=0,
            layout_qualification=proof)
        require(canonical(policy.pop('native_large_cache_scope')) == canonical(scope),
            'The published expanded-cache resource scope differs')
        for key, value in dict(schema='ps5-qwen-owned-padded-expert-cache-v2', physical_planes=129,
                cache_cap_bytes=CACHE_BYTES, layout_qualification_SELF_SHA256=proof['SELF_sha256'],
                layout_qualification_result_SHA256=proof['report_sha256']).items():
            require(type(padded.get(key)) is type(value) and padded[key] == value,
                'The expanded-cache allocation/proof differs')
    else:
        require('cache128' not in expected and 'native_large_cache_scope' not in policy,
            'The control must use its original cache scope')
        for key, value in dict(schema='ps5-qwen-owned-padded-expert-cache-v1', physical_planes=54,
                cache_cap_bytes=512 << 20,
                layout_qualification_SELF_SHA256='5bb22cdf4603b038d8247597caafe8b08479c2e9bcc1fda44982b777ae2018db',
                layout_qualification_result_SHA256='d277b1d03fcabe981408b8027a559e16134eb8b7e746bef366bb20ea63703cb5').items():
            require(type(padded.get(key)) is type(value) and padded[key] == value, 'The control allocation/proof differs')
    # Only the explicitly priced geometry/proof changes. Every remaining policy
    # key, including source schedules, driver and monitoring, must match exactly.
    for key in ('schema', 'active_slots', 'physical_planes', 'cache_cap_bytes',
                'layout_qualification_SELF_SHA256', 'layout_qualification_result_SHA256'):
        padded.pop(key)
    return canonical(policy)


def comparable_app(app, expected):
    app = copy.deepcopy(app)
    require(app.get('schema') == 'ps5-qwen-app-v1' and app.get('mode') == 'first-generation-validation'
        and app.get('native_display') is False and type(app.get('port')) is int and app['port'] == 8086,
        'The published model startup scope differs')
    require(app.pop('admission_report') == '/app0/qwen-runtime/plan-' + expected['run_id'] + '.json',
        'The published report path differs')
    clock = app.pop('clock_calibration')
    require(set(clock) == {'schema', 'console_epoch_ms', 'utc_epoch_ms', 'uncertainty_ms'} and
        clock['schema'] == 'ps5-qwen-clock-offset-v1' and
        integer(clock['console_epoch_ms'], 0, 4102444800000) and
        integer(clock['utc_epoch_ms'], 946684800000, 4102444800000) and
        integer(clock['uncertainty_ms'], 0, 5000), 'A bounded current monitor calibration is required')
    return canonical(app)


def validate_after_load(record, slots):
    cache, reserve = (CACHE_BYTES, 1152 << 20) if slots == 128 else (512 << 20, 1920 << 20)
    exact = dict(model_loaded=True, expert_cache_requested_bytes=cache,
        remaining_context_workspace_staging_reserve_bytes=reserve,
        device_budget_source='canary-validated native Direct allocator')
    require(all(type(record.get(k)) is type(v) and record[k] == v for k, v in exact.items()),
        'The actual postload cache and retained reserves differ')
    counters = [record.get(k) for k in ('native_Direct_available_bytes', 'native_Direct_owned_bytes', 'native_Direct_pool_bytes')]
    require(all(integer(v, 1) for v in counters) and counters[0] + counters[1] <= counters[2]
        and counters[0] >= cache + reserve, 'The actual postload Direct pool cannot retain the selected cache and reserves')


def review_arm(arm, root):
    require(type(arm) is dict and set(arm) == {'active_slots', 'result', 'binding', 'policy', 'app', 'evidence'},
        'Exact independent cohort arm required')
    slots = arm['active_slots']
    require(type(slots) is int and slots in ORDER, 'Unsupported cohort capacity')
    path = captured(arm['result'], root)
    expected = read_record(captured(arm['binding'], root))
    policy = read_record(captured(arm['policy'], root))
    app = read_record(captured(arm['app'], root))
    require(type(arm['evidence']) is list and 0 < len(arm['evidence']) <= 256, 'Complete sidecar captures required')
    files = [captured(row, root) for row in arm['evidence']]
    actual = {p.resolve() for p in path.parent.glob(path.name + '.*') if p.is_file()}
    require(len(set(files)) == len(files) and set(files) == actual,
        'Missing, duplicate or additional captured native sidecars')
    validate(path, expected)
    result = read_record(path)
    validate_after_load(read_record(Path(str(path) + '.memory.after-load')), slots)
    validate_backpressure(read_record(Path(str(path) + '.memory.backpressure')))
    require(result.get('source_pipeline_worker_stopped') is True, 'The source worker did not positively stop')
    requests = [read_record(Path(str(path) + '.first.result')), *result['demonstration']['requests']]
    route_rows, performance, prompts = [], [], []
    for ordinal, (suffix, request) in enumerate(zip(('.first', '.demo1', '.demo2'), requests)):
        record = read_record(Path(str(path) + suffix + '.performance'))
        require(record.get('schema') == 'ps5-qwen-completed-performance-v5' and
            record.get('owned_padded_bank_IO') is True, 'The original complete performance scope is required')
        if ordinal == 0:
            summary = validate_first_performance(record, result, request, split_sources=True)
        else:
            summary = validate_performance(record, request, split_sources=True)
        routes = read_record(Path(str(path) + suffix + '.expert-routes'))
        require(routes.get('sidecar_written_after_model_and_source_retirement') is True and
            routes.get('JSON_created_after_model_and_source_retirement') is True,
            'Expert routes were not finalized after retirement')
        validate_routes(routes, request, width=4, pid=expected['pid'], run_id=expected['run_id'],
            cold=ordinal < 2, expected_slots=slots)
        route_rows.append(routes['records'])
        performance.append(summary['delta'])
        prompts.append(read_record(Path(str(path) + suffix + '.intent'))['rendered_prompt'])
    frames = [read_record(Path(str(path) + '.demo' + str(i) + '.display.json'))['epoch_ms'] for i in (1, 2)]
    require(frames[0] < frames[1], 'The request display epochs are not ordered')
    policy_key = comparable_policy(policy, expected, slots)
    app_key = comparable_app(app, expected)
    # Recheck complete captures after all dependent reads, including bitmaps.
    for row in [arm[k] for k in ('result', 'binding', 'policy', 'app')] + arm['evidence']:
        captured(row, root)
    require({p.resolve() for p in path.parent.glob(path.name + '.*') if p.is_file()} == actual,
        'Native evidence changed during review')
    common = {k: v for k, v in expected.items() if k not in ('pid', 'run_id', 'cache128')}
    return dict(run_id=expected['run_id'], common=canonical(common), policy=policy_key, app=app_key,
        requests=requests, routes=route_rows, prompts=prompts, performance=performance,
        frame_epochs=frames, clock_uncertainty_ms=app['clock_calibration']['uncertainty_ms'],
        CPU_heap_peak_bytes=result['CPU_heap_peak_bytes'], postload_device_peak_bytes=result['postload_device_peak_bytes'])


def spread(values):
    return max(values) / min(values) - 1


def compare(arms):
    require(len(arms) == 4 and len({a['run_id'] for a in arms}) == 4, 'Four distinct completed native runs required')
    for key in ('common', 'policy', 'app', 'routes', 'prompts'):
        require(all(canonical(a[key]) == canonical(arms[0][key]) for a in arms[1:]),
            'A non-capacity configuration, source, driver or selected expert route differs')
    require(all(a['frame_epochs'][-1] + a['clock_uncertainty_ms'] <
        b['frame_epochs'][0] - b['clock_uncertainty_ms'] for a, b in zip(arms, arms[1:])),
        'Completed calibrated epochs do not establish the declared A/B/B/A order')
    measured = []
    for ordinal in range(3):
        requests = [a['requests'][ordinal] for a in arms]
        for key in ('token_ids', 'output_bytes', 'stop_reason'):
            require(all(canonical(r[key]) == canonical(requests[0][key]) for r in requests[1:]),
                'The original-model output differs across cohort arms')
        for key in ('prompt_tokens', 'generated_tokens'):
            require(all(type(r['metrics'][key]) is int and r['metrics'][key] == requests[0]['metrics'][key]
                for r in requests), 'The measured workload differs')
        speeds = [r['metrics']['decode_tokens_per_second'] for r in requests]
        require(all(type(s) in (int, float) and 0 < s < float('inf') for s in speeds), 'A finite decode interval is required')
        control_noise, candidate_noise = spread([speeds[0], speeds[3]]), spread([speeds[1], speeds[2]])
        gains = [speeds[1] / speeds[0] - 1, speeds[2] / speeds[3] - 1]
        latencies = {}
        for key in ('total_ms', 'prefill_ms', 'TTFT_ms' if ordinal == 0 else 'ttft_ms'):
            values = [r['metrics'][key] for r in requests]
            require(all(type(v) in (int, float) and 0 < v < float('inf') for v in values), 'A finite latency is required')
            # Candidate instability cannot enlarge the control's tolerated
            # latency regression and hide an expensive setup/prefill phase.
            noise = spread([values[0], values[3]])
            ratios = [values[1] / values[0], values[2] / values[3]]
            latencies[key] = dict(values=values, observed_spread=noise,
                pair_ratios=ratios, no_regression_beyond_observed_spread=all(r <= 1 + noise for r in ratios))
        measured.append(dict(request_ordinal=ordinal, included_in_primary_speed=ordinal > 0,
            decode_tokens_per_second=speeds, paired_relative_gains=gains,
            observed_control_spread=control_noise, observed_candidate_spread=candidate_noise,
            repeatable_gain_above_observed_spread=min(gains) > max(control_noise, candidate_noise),
            latency=latencies, completed_IO_counters=[a['performance'][ordinal] for a in arms]))
    external = measured[1:]
    faster = all(r['repeatable_gain_above_observed_spread'] for r in external)
    latency_ok = all(v['no_regression_beyond_observed_spread'] for r in measured for v in r['latency'].values())
    losing = any(max(r['paired_relative_gains']) <= 0 for r in external)
    state = 'speed_candidate_requires_ordinary_close_and_placement' if faster and latency_ok else (
        'retain_control_latency_regression' if not latency_ok else
        'retain_control_slower_in_both_orders' if losing else 'inconclusive_observed_variation')
    return dict(schema='ps5-qwen-cache-capacity-cohort-result-v1', state=state,
        order=list(ORDER), timing_boundary=TIMING, requests=measured,
        speed_qualified=faster and latency_ok, production_adopted=False,
        placement_and_ordinary_close_proof_required=True, statistical_significance_claimed=False,
        resource_peaks=[{k: a[k] for k in ('CPU_heap_peak_bytes', 'postload_device_peak_bytes')} for a in arms])


def review(path):
    path = Path(path).resolve()
    identity = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest = read_record(path)
    require(set(manifest) == {'schema', 'timing_boundary', 'arms'} and
        manifest['schema'] == 'ps5-qwen-cache-capacity-cohort-v1' and manifest['timing_boundary'] == TIMING,
        'One frozen same-boundary cache cohort is required')
    arms = manifest['arms']
    require(type(arms) is list and len(arms) == 4 and
        [a.get('active_slots') for a in arms] == list(ORDER), 'The predeclared A/B/B/A order differs')
    result = compare([review_arm(arm, path.parent) for arm in arms])
    require(hashlib.sha256(path.read_bytes()).hexdigest() == identity, 'The cohort manifest changed during review')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(review(args.manifest), indent=2, ensure_ascii=False, allow_nan=False))


if __name__ == '__main__':
    main()
