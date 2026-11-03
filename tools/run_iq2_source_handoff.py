#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Wait locally for a source suffix, then submit and collect its sealer once."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

from build_performance_quantizer import record
from start_success_route import load, need, save


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('current', 'publication', 'sealer', 'transfer-proof', 'out'):
        p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args()
    tool = Path(__file__).with_name('finish_iq2_source_seal.py')
    frozen = record(tool)
    a.out.mkdir(parents=True, exist_ok=False)
    save(a.out / 'intent.private.json', dict(finalizer=frozen,
        transfer_proof=str(a.transfer_proof), original_publication=str(a.publication),
        native_submissions=1, automatic_retries=0, local_wait_limit_seconds=14400,
        quiet_collection_intervals_seconds=[350, 180, 180, 180, 180]))
    deadline = time.monotonic() + 14400
    while not a.transfer_proof.exists():
        need(time.monotonic() < deadline, 'Source suffix has no positive completion; preserve its owner')
        time.sleep(30)
    transfer = load(a.transfer_proof)
    need(transfer['complete'] and transfer['exit_code'] == 0,
         'The exact source suffix must finish before native handoff')
    args = [sys.executable, '-B', str(tool)]
    for name in ('current', 'publication', 'sealer', 'transfer-proof'):
        args += ['--' + name, str(getattr(a, name.replace('-', '_')))]
    for attempt in range(6):
        if attempt:
            time.sleep(350 if attempt == 1 else 180)
        need(record(tool) == frozen, 'The reserved finalizer changed before its next phase')
        phase = 'submit' if attempt == 0 else 'collect-' + str(attempt)
        with (a.out / (phase + '.private.log')).open('xb') as log:
            child = subprocess.run(args + ['--submit' if attempt == 0 else '--collect'],
                stdout=log, stderr=subprocess.STDOUT, timeout=600)
        need(child.returncode == 0, 'Stop without replay; inspect ' + phase + '.private.log')
        if (a.publication / 'result.private.json').exists():
            save(a.out / 'result.private.json', dict(completed=True,
                publication=record(a.publication / 'result.private.json'),
                sealer=record(a.sealer / 'result.private.json'),
                transfer=record(a.transfer_proof), native_submissions=1,
                automatic_retries=0, completed_payload_retransmissions=0))
            print(json.dumps(dict(completed=True, native_submissions=1)), flush=True)
            return
    raise RuntimeError('Same sealer remains pending; preserve ownership and never resubmit')


if __name__ == '__main__':
    main()
