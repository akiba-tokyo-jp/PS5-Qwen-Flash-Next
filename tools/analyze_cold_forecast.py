#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Price a completed early-router observer without issuing speculative reads."""
import argparse
import json
import statistics
from pathlib import Path


def analyze(terminal):
    if not (terminal['completed'] and terminal['all_model_source_device_owners_positively_retired']):
        raise ValueError('A positively completed native observer is required')
    rows = []
    for request in terminal['requests']:
        forecast = request['deadline_forecast']
        if forecast['speculative_reads'] != 0 or not forecast['authoritative_routing_unchanged']:
            raise ValueError('The observer must preserve authoritative routing without speculative I/O')
        observations = forecast['observations']
        useful = []
        for observation in observations:
            predicted_missing = {e for e, missing in zip(observation['predicted'], observation['early_missing']) if missing}
            actual_missing = {e for e, missing in zip(observation['actual'], observation['actual_missing']) if missing}
            useful.append(len(predicted_missing & actual_missing))
        rows.append(dict(
            ordinal=request['ordinal'], observations=len(observations),
            predicted_missing=sum(sum(o['early_missing']) for o in observations),
            actual_missing=sum(sum(o['actual_missing']) for o in observations),
            useful_missing_predictions=sum(useful),
            median_lead_ms=statistics.median(o['lead_ns'] for o in observations) / 1e6,
            maximum_lead_ms=max(o['lead_ns'] for o in observations) / 1e6,
            callback_wall_ms=sum(o['callback_wall_ns'] for o in observations) / 1e6,
            optimistic_sum_per_Expert_hidden_ms=sum(o['lead_ns'] * n for o, n in zip(observations, useful)) / 1e6,
            optimistic_sum_per_projection_hidden_ms=3 * sum(o['lead_ns'] * n for o, n in zip(observations, useful)) / 1e6,
        ))
    return dict(completed=True, read_only_analysis=True, rows=rows,
                physical_speculative_reads_tested=False,
                disposition='Close this layer23 pre-attention Top6 forecast; do not enable speculative I/O',
                reason='Few predictions cover actual misses; even tripling the sum of useful leads for three projections is below callback wall time. Extra GPU work and wrong-read contention are not free.',
                limitations='Callback wall includes synchronization of preceding work; it is not isolated added kernel cost. This is an economic screen of this observer, not a universal bound on other predictors.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--terminal', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise ValueError('Do not replace completed evidence')
    result = analyze(json.loads(args.terminal.read_text()))
    args.out.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
