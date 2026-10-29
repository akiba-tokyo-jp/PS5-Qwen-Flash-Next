#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Relink the bounded Q4 passive monitor using exactly qualified model providers."""
import json,sys
from pathlib import Path
import build_expert_q4_model as builder
from expert_q4 import record,require,write_json
from expert_q4_monitor_source import MONITOR_SCOPE,monitor_entry_source

def main():
    out=Path(sys.argv[sys.argv.index('--out')+1])
    root=Path(__file__).resolve().parents[1]
    files=[Path(__file__),root/'tools/expert_q4_monitor_source.py']
    frozen=[record(p)for p in files]
    builder.entry_source=monitor_entry_source;builder.SCOPE=MONITOR_SCOPE
    builder.main()
    for row in frozen:require(record(row['path'])==row,'Monitor adapter changed during the native link')
    path=out/'receipt.private.json';receipt=json.loads(path.read_text())
    receipt['inputs_before']+=frozen
    receipt['expert_q4_model'].update(passive_monitor=True,HTTP_requests=2,VideoOut_starts=1,
        same_Q4_reference_from_completed_warmup=True,normal_application_validation_pending=True)
    write_json(path,receipt)
    print(json.dumps(dict(Q4_passive_monitor_built=True,PS5_operations=0,CI_runs=0)),flush=True)
if __name__=='__main__':main()
