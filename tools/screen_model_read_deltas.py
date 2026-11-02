#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Advance the zero-recurrence read screen with a relative-offset refinement."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

from build_performance_quantizer import record
from finalize_model_pread_observation import decode
from read_delta_predictor import DeltaSuccessor
from read_transition_predictor import simulate
from start_success_route import load, need, save

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prior-screen', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=False)
    prior = load(a.prior_screen)
    need(prior['completed'] and prior['PS5_operations'] == 0 and
         all(r['statistics']['predictions'] == 0 for r in prior['refinements']),
         'The completed zero-recurrence screen is required')
    for item in prior['source_inputs']:
        need(record(item['path']) == item, 'Prior screened input changed')
    proof_path = Path(prior['source_inputs'][0]['path'])
    proof = load(proof_path)
    case = load(proof['case']['path'])
    terminal = load(case['terminal']['path'])
    inputs = [record(a.prior_screen), *prior['source_inputs'],
              record(Path(__file__)), record(ROOT / 'tools/read_delta_predictor.py'),
              record(ROOT / 'tests/test_read_delta_predictor.py')]
    controls = subprocess.run([sys.executable, '-B', str(ROOT / 'tests/test_read_delta_predictor.py')],
                              capture_output=True, timeout=30)
    (a.out / 'host-controls.private.log').write_bytes(controls.stdout + controls.stderr)
    need(controls.returncode == 0, controls.stderr.decode(errors='replace')[-3000:])
    binding = {name: terminal[name] for name in ('run_id', 'pid', 'candidate_SELF_sha256', 'model_receipt_sha256')}
    rows = decode(Path(proof['raw']['path']).read_bytes(), load(proof['native_audit']['path']), binding)
    statistics = simulate(rows, DeltaSuccessor)
    result = dict(completed=True, source_inputs=inputs, prior_absolute_transition_screen_reused_without_replay=True,
                  implementation_change='Predict offset differences from one/two completed deltas instead of exact offset recurrence',
                  host_controls_passed=8, statistics=statistics,
                  maximum_predictions_per_original_producer=6, maximum_pending_spans_per_producer=1,
                  maximum_transition_entries_per_table=512, transition_tables_per_producer=2,
                  maximum_immutable_source_histories_per_producer=64,
                  predictions_use_only_completed_prior_reads=True, hypothetical_completion_is_optimistic=True,
                  source_admission_latency_and_contention_not_simulated=True,
                  actual_prefetch_IO_submitted=0, PS5_operations=0, model_decode_tok_s_measured=False,
                  native_prefetch_integration=False, production_adopted=False)
    save(a.out / 'result.private.json', result)
    print(json.dumps(dict(completed=True, host_controls=8, statistics=statistics,
                          prior_absolute_screen_not_replayed=True, model_decode_tok_s_measured=False, PS5_operations=0)))


if __name__ == '__main__':
    main()
