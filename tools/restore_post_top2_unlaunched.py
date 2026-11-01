#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Restore a published candidate after a positively returned zero-launch refusal."""
import argparse,ast,json
from pathlib import Path
from build_speculative_batch_probe import once
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--case',type=int,required=True);a=p.parse_args()
    case=Path('D:/PS5-AI/qwen-flash-next')/f'hardware-first-generation-{a.case}'
    state=json.loads((case/'active-console.private.json').read_text())
    assert state['ordinary_launch_calls']==0 and not state['native_running']
    assert not(case/'OS-launch-result.private.json').exists()
    raw=(case/'prelaunch-memory-gate/console.private.log').read_bytes()
    assert raw.count(b'END success=0 ')==1 and b'END success=1 'not in raw
    assert b'allocations=0 payload_reads=0 title_launches=0 GPU_calls=0 automatic_retry=0'in raw
    source=(ROOT/f'.local/restore_resident_cohort_{a.case+5}.py').read_text()
    left=source.index('state=op.current();op.no_native();closed=');right=source.index("assert op.load(C/'postboot-title-mount-2807",left)
    source=source[:left]+'''state=op.current();op.no_native()
assert state['ordinary_launch_calls']==0 and not state['native_running']
analysis=dict(completed=True,GPU_initializations=0,model_requests_completed=0,unknown_completion=False)
'''+source[right:]
    source=once(source,'actual_title_launches=1,','actual_title_launches=0,')
    source=once(source,'CPU_title_normally_closed=True,','CPU_title_normally_closed=False,zero_launch_refusal=True,')
    source=once(source,"native_analysis=op.record(CASE/'CPU-calibration-analysis.private.json')","native_analysis=op.record(CASE/'prelaunch-memory-gate/console.private.log')")
    source=once(source,"print('Exact fastest/settings restored after the bounded model comparison and ordinary OS close.',flush=True)","print('Exact production and settings restored after a returned zero-launch refusal; no close call.',flush=True)")
    ast.parse(source);out=case/'restore-unlaunched.private.py'
    with out.open('x',newline='\n')as f:f.write(source)
    exec(compile(source,str(out),'exec'),dict(__file__=str(ROOT/f'.local/restore_resident_cohort_{a.case+5}.py'),__name__='unlaunched_restore'))

if __name__=='__main__':main()
