#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Two distinct causal transition refinements over one qualified read trace."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

from build_performance_quantizer import record
from finalize_model_pread_observation import decode
from read_transition_predictor import ContextSuccessor, LastSuccessor, simulate
from start_success_route import load, need, save

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--trace-proof', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=False)
    proof = load(a.trace_proof)
    need(proof['completed'] and proof['all23_full_F32_rows_and_actual_routes_exact'] and
         proof['all_original_calls_preserved_without_retries'], 'A completed original model trace is required')
    inputs = [record(a.trace_proof)]
    for name in ('raw', 'native_audit', 'case', 'closure'):
        need(record(proof[name]['path']) == proof[name], 'A qualified trace input changed')
        inputs.append(proof[name])
    case = load(proof['case']['path'])
    terminal = load(case['terminal']['path'])
    need(record(case['terminal']['path']) == case['terminal'], 'Native terminal changed')
    inputs.append(case['terminal'])
    for path in (Path(__file__), ROOT / 'tools/read_transition_predictor.py',
                 ROOT / 'tests/test_read_transition_predictor.py'):
        inputs.append(record(path))
    controls = subprocess.run([sys.executable, '-B', str(ROOT / 'tests/test_read_transition_predictor.py')],
                              capture_output=True, timeout=30)
    (a.out / 'host-controls.private.log').write_bytes(controls.stdout + controls.stderr)
    need(controls.returncode == 0, controls.stderr.decode(errors='replace')[-3000:])
    binding = {key: terminal[key] for key in ('run_id', 'pid', 'candidate_SELF_sha256', 'model_receipt_sha256')}
    rows = decode(Path(proof['raw']['path']).read_bytes(), load(proof['native_audit']['path']), binding)
    rounds = [dict(round=1, change='Most recently completed successor; bounded single-read context',
                   statistics=simulate(rows, LastSuccessor)),
              dict(round=2, change='Two-read context with two-observation agreement; single-read fallback requires three',
                   statistics=simulate(rows, ContextSuccessor))]
    report = dict(completed=True, source_inputs=inputs, host_controls_passed=10, refinements=rounds,
                  original_calls=len(rows), original_producers=proof['original_producers'],
                  maximum_predictions_per_original_producer=6, maximum_pending_spans_per_producer=1,
                  maximum_transition_entries_per_table=512, round_one_tables_per_producer=1,
                  round_two_tables_per_producer=2, immediate_next_read_grading=True,
                  unsupported_or_short_reads_break_transition_history=True,
                  predictions_use_only_completed_prior_reads=True,
                  future_calls_only_grade_previously_chosen_predictions=True,
                  optimistic_instantaneous_completion=True, source_admission_or_contention_simulated=False,
                  completed_trace_decoded_once=True, unchanged_native_test_replayed=False,
                  actual_prefetch_IO_submitted=0, PS5_operations=0, model_decode_tok_s_measured=False,
                  native_prefetch_integration=False, production_adopted=False)
    save(a.out / 'result.private.json', report)
    print(json.dumps(dict(completed=True, host_controls=10, original_calls=len(rows), refinements=rounds,
                          model_decode_tok_s_measured=False, PS5_operations=0)))


if __name__ == '__main__':
    main()
