#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Restore after a returned launcher guard proves zero actual title launches."""
import argparse,ast,json
from pathlib import Path
from build_speculative_batch_probe import once
from expert_q4 import record,require,write_json
ROOT=Path(__file__).resolve().parents[1]

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--case',type=int,required=True);a=p.parse_args();case=Path('D:/PS5-AI/qwen-flash-next')/f'hardware-first-generation-{a.case}'
 state=json.loads((case/'active-console.private.json').read_text());result=json.loads((case/'OS-launch-result.private.json').read_text());raw=(case/'launch-native/console.private.log').read_bytes()
 require(state['ordinary_launch_calls']==1 and state['native_running']is None and result['OS_accepted']is False,'One unaccepted guarded request required')
 require(raw.count(b'END mode=launch success=0 launch_calls=0 ')==1 and b'END mode=launch success=1'not in raw and
  b'eboot_count=0 no_signals=1'in raw and b'metadata_writes=0 mount_calls=0 registration_calls=0 GPU_calls=0 signals=0'in raw,'Actual zero-launch native guard terminal required')
 require(not(case/'native-owner.private.json').exists()and not(case/'pre-staged-close.private.json').exists(),'No native owner/close attempt may be assumed')
 proof=case/'guarded-zero-launch-refusal.private.json';write_json(proof,dict(completed=True,actual_title_launches=0,GPU_initializations=0,unknown_completion=False,
  helper_request_count=1,actual_app_launch_calls=0,raw=record(case/'launch-native/console.private.log'),original_host_attempt_result_preserved=record(case/'OS-launch-result.private.json')))
 source=(ROOT/f'.local/restore_resident_cohort_{a.case+5}.py').read_text();left=source.index('state=op.current();op.no_native();closed=');right=source.index("assert op.load(C/'postboot-title-mount-2807",left)
 source=source[:left]+'''state=op.current();op.no_native()
assert state['ordinary_launch_calls']==1 and state['native_running']is None
analysis=dict(completed=True,GPU_initializations=0,model_requests_completed=0,unknown_completion=False)
'''+source[right:]
 source=once(source,'actual_title_launches=1,','actual_title_launches=0,');source=once(source,'CPU_title_normally_closed=True,','CPU_title_normally_closed=False,returned_launcher_guard_zero_actual_launches=True,')
 source=once(source,"native_analysis=op.record(CASE/'CPU-calibration-analysis.private.json')","native_analysis=op.record(CASE/'guarded-zero-launch-refusal.private.json')")
 source=once(source,"print('Exact fastest/settings restored after the bounded model comparison and ordinary OS close.',flush=True)","print('Exact production/settings restored after launcher guard returned zero actual launches; no close call.',flush=True)")
 ast.parse(source);out=case/'restore-zero-launcher.private.py'
 with out.open('x',newline='\n')as f:f.write(source)
 exec(compile(source,str(out),'exec'),dict(__file__=str(ROOT/f'.local/restore_resident_cohort_{a.case+5}.py'),__name__='zero_launcher_restore'))
if __name__=='__main__':main()
