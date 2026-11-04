# SPDX-License-Identifier: MIT
"""Continue only qualified actual model-read owners and archived observations."""
from pathlib import Path

from build_performance_quantizer import record
from retire_completed_model_source_cache import LEDGER, cohort_entry, sources, validate_owner
from start_success_route import load, need
from success_case_control import current_files

ROOT = Path(__file__).resolve().parents[1]


def qualification(controls, compact_control):
    checked = load(controls)
    need(checked['completed'] and checked['PS5_operations'] == 0 and
         checked['source'] == record(ROOT / 'tools/retire_completed_model_source_cache.py') and
         checked['owner_negatives'] == 8 and checked['ledger_negatives'] == 4,
         'The exact completed-model owner and no-reset ledger admission must be qualified')
    compact = load(compact_control)
    need(compact['completed'] and compact['PS5_operations'] == 0 and
         compact['source'] == record(ROOT / 'tools/compact_case_integrity_markers.py'),
         'The unchanged compact diagnostic marker control must remain bound')
    return [record(controls), record(compact_control), checked['source'], compact['source'], record(Path(__file__))]


def last_owner(current):
    state = load(current / 'active-console.private.json')
    active = state.get('active_successful_native_case')
    if not active or active.get('phase') != 'model-complete-ordinary-close-original-restored':
        return None
    case = Path(active['plan']['path']).parents[1]
    plan, native, closed, files, windows, _ = sources(current, case)
    validate_owner(state, plan, native, closed, current_files(current))
    row = record(case / 'result.private.json')
    matches = [entry for entry in state.get(LEDGER, []) if entry['case_result'] == row]
    need(len(matches) <= 1, 'One latest model may own only one source-residency ledger')
    completed = matches[0]['completed_scopes'] if matches else []
    cohort_entry(state.get(LEDGER, []), row, completed)
    first = sum(load(item['path'])['observations']['scanned'] for item in completed)
    need(first <= len(windows), 'The completed source prefix exceeded this actual model cohort')
    return dict(case=case, completed=completed, has_windows=first < len(windows))


def available(current):
    value = last_owner(current)
    return value is not None and value['has_windows']


def flags(current, common, compact_control, out):
    owner = last_owner(current)
    need(owner is not None and owner['has_windows'], 'No new actual completed model read owner or unscanned suffix is available')
    result = list(common) + ['--case', owner['case'], '--compact-marker-control', compact_control, '--out', out]
    for row in owner['completed']:
        result += ['--completed-scope', Path(row['path'])]
    return result


def validate_reused_observation(plan, result, closed, native, package):
    need(plan['package'] == package and result['completed'] and result['all_counting_and_finite_checks'] and
         closed['completed'] and closed['ordinary_exit_observed'] and closed['current_seven_restored_and_native_hashed'] and
         not closed['unknown_completion'] and closed['native_owners'] == 0 and
         closed['all_model_source_device_owners_positively_retired'] and
         native['completed'] and native['candidate_SELF_sha256'] == plan['SELF']['sha256'] and
         native['all_model_source_device_owners_positively_retired'] and native['device_ledger_live_bytes'] == 0,
         'Reuse only the exact compiled observed case with completed outputs, ordinary exit and selected-file restoration')


def reused_observation(root, package):
    paths = [root / 'case/plan.private.json', root / 'result.private.json', root / 'closed/result.private.json']
    plan, result, closed = map(load, paths)
    terminal = closed['native_terminal']
    need(record(terminal['path']) == terminal, 'The archived observed terminal changed')
    validate_reused_observation(plan, result, closed, load(terminal['path']), record(package))
    profile = load(load(package)['effective_application_policy']['profile']['path'])
    need(profile['qualification_observer'] is not None and not profile['performance_timings_usable'],
         'Only an already completed independently instrumented observation may be reused here')
    return result, [record(path) for path in paths] + [terminal, record(package)]
