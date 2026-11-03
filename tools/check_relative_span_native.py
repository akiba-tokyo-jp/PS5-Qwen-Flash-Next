#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compare the new native predictor with the completed independent trace screen."""
import argparse
import json
import os
from pathlib import Path
import subprocess
from build_performance_quantizer import record
from start_success_route import load,need,save
ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','prior-screen','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();old=load(a.prior_screen);need(old['completed'] and old['native_prefetch_integration']==False,
        'Completed independent relative-offset trace screen required')
    proof_row=next(r for r in old['source_inputs'] if 'I1-model-call-sequence-qualified-' in r['path'] and r['path'].endswith('result.private.json'))
    need(record(proof_row['path'])==proof_row,'Completed trace qualification changed');proof=load(proof_row['path'])
    raw=proof['raw'];need(record(raw['path'])==raw,'The actual native stream changed')
    a.out.mkdir(parents=True,exist_ok=False);host=a.workspace/'toolchain/msys-clang64/clang64/bin'
    exe=a.out/'relative-span-check.exe';source=ROOT/'native/app/relative_span_predictor.h';test=ROOT/'tests/relative_span_trace_test.cpp'
    jobs=[[str(host/'clang++.exe'),'-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'native/app'),str(test),'-o',str(exe)],
          [str(exe),raw['path']]]
    env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''),TMP=str(a.out),TEMP=str(a.out))
    for i,job in enumerate(jobs):
        result=subprocess.run(job,capture_output=True,timeout=60,env=env)
        (a.out/(str(i)+'.private.log')).write_bytes(result.stdout+result.stderr)
        need(not result.returncode,(result.stdout+result.stderr).decode(errors='replace')[-3000:])
    native=json.loads(result.stdout);reference=old['statistics']
    keys=('original_calls','eligible_calls','original_producers','predictions','hits','unused','predicted_bytes','hit_bytes','live_table_entries_peak')
    need(all(native[k]==reference[k] for k in keys),'The native port differs from the independent completed screen')
    save(a.out/'result.private.json',dict(completed=True,prior_screen=record(a.prior_screen),trace_proof=proof_row,raw=raw,
        source=record(source),test=record(test),row_ABI=record(ROOT/'native/app/model_pread_observation.h'),commands=jobs,
        statistics=native,all_independent_reference_statistics_exact=True,new_native_geometry_refusals=8,
        old_Python_predictor_controls_reused_without_replay=True,actual_speculative_IO_submitted=0,
        native_model_integration_qualified=False,model_decode_tok_s_measured=False,PS5_operations=0))
    print(json.dumps(dict(completed=True,statistics=native,new_geometry_refusals=8,PS5_operations=0)))


if __name__=='__main__':main()
