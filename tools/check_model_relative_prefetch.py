#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Qualify only the new concurrent speculative-I/O adapter on the host."""
import argparse
import os
from pathlib import Path
import subprocess
from build_performance_quantizer import record
from start_success_route import load,need,save
ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','predictor-proof','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();prior=load(a.predictor_proof)
    need(prior['completed'] and prior['all_independent_reference_statistics_exact'] and
        record(prior['source']['path'])==prior['source'] and prior['statistics']['largest_prediction_bytes']<=2<<20,
        'Exact native predictor and actual bounded trace coverage required')
    a.out.mkdir(parents=True,exist_ok=False);host=a.workspace/'toolchain/msys-clang64/clang64/bin'
    exe=a.out/'relative-IO-check.exe';test=ROOT/'tests/model_relative_prefetch_test.cpp'
    source=ROOT/'native/app/model_relative_prefetch.h'
    jobs=[[str(host/'clang++.exe'),'-std=c++17','-O2','-Wall','-Wextra','-Werror','-pthread','-I',str(ROOT/'native/app'),str(test),'-o',str(exe)],[str(exe)]]
    env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''),TMP=str(a.out),TEMP=str(a.out))
    for i,job in enumerate(jobs):
        run=subprocess.run(job,capture_output=True,timeout=45,env=env)
        (a.out/(str(i)+'.private.log')).write_bytes(run.stdout+run.stderr)
        need(not run.returncode,(run.stdout+run.stderr).decode(errors='replace')[-3500:])
    save(a.out/'result.private.json',dict(completed=True,predictor_proof=record(a.predictor_proof),source=record(source),
        test=record(test),commands=jobs,new_concurrent_controls=9,original_read_parallelism=4,
        maximum_extra_workers=1,maximum_pending_spans=1,actual_scratch_bytes=2<<20,additional_FDs=0,
        fd_close_waits_for_same_pending_read=True,unknown_completion_retains_actual_backing=True,
        old_predictor_and_IO_fixture_tests_replayed=0,PS5_operations=0,model_integration_qualified=False))
    print(dict(completed=True,new_concurrent_controls=9,maximum_parallel_reads=4,PS5_operations=0))


if __name__=='__main__':main()
