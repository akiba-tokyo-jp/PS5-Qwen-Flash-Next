#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Retain eight cold output rows to test a projection path beyond one-row GEMV."""
import argparse
import copy
import os
from pathlib import Path
import subprocess

from build_performance_quantizer import record
from build_speculative_batch_probe import once
from start_success_route import load,need,save

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','refinement','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();old=load(a.refinement)
    need(old['completed'] and len(old['new_selector_controls'])==16,'Completed cold-only phase controls required')
    need(all(record(r['path'])==r for r in old['source_inputs']),'Original completed selector sources must remain unchanged')
    a.out.mkdir(parents=True,exist_ok=False)
    wrapper=a.out/'prefill_cold_candidate.cpp';wrapper.write_bytes((ROOT/'native/app/prefill_cold_candidate.cpp').read_bytes())
    base=ROOT/'native/app/prefill_process_candidate.cpp';text=base.read_text(encoding='utf-8')
    text=once(text,'i+1==count','i+8>=count')
    text=once(text,'unsigned(QWEN_PERF_PREFILL_POST_TRUNK?1:count)','unsigned(QWEN_PERF_PREFILL_POST_TRUNK?(count<8?count:8):count)')
    implementation=a.out/'prefill_process_candidate.cpp';implementation.write_text(text,encoding='utf-8',newline='\n')
    test=a.out/'tail-scope.cpp';test.write_text(once((ROOT/'tests/prefill_cold_candidate_test.cpp').read_text(encoding='utf-8'),
        'expect_narrow?1:b->tokens.size()','expect_narrow?std::min(std::size_t(8),b->tokens.size()):b->tokens.size()'),encoding='utf-8',newline='\n')
    stubs=Path(old['commands'][0][old['commands'][0].index('-o')+1]).parent
    for name in ('llama','llama-batch'):
        (a.out/(name+'.h')).write_bytes((stubs/('host-'+name+'.stub')).read_bytes())
    host=a.workspace/'toolchain/msys-clang64/clang64/bin';environment=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''),TMP=str(a.out),TEMP=str(a.out))
    commands=[]
    def run(command,label):
        commands.append(command);done=subprocess.run(command,capture_output=True,env=environment,timeout=120)
        (a.out/(label+'.private.log')).write_bytes(done.stdout+done.stderr)
        need(done.returncode==0,(done.stdout+done.stderr).decode(errors='replace')[-3000:])
    executable=a.out/'tail-controls.exe'
    run([str(host/'clang++.exe'),'-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(a.out),'-I',str(ROOT/'native/app'),str(test),'-o',str(executable)],'host-compile')
    checks=[]
    for length in (1,2,7,8,9,30,33,65):
        for enabled in (False,True):
            run([str(executable),str(length),str(int(enabled))],str(length)+'-'+str(int(enabled)))
            checks.append(dict(tokens=length,candidate=enabled,cold_output_tail_rows=8,later_requests_unchanged=True,
                decode_selection_preserved=True,exceptions_restore_flags=True))
    for name in ('llama','llama-batch'):(a.out/(name+'.h')).rename(a.out/('host-'+name+'.stub'))
    command=old['commands'][1].copy();command[1:1]=['-I',str(a.out)]
    command[command.index('-c')+1]=str(wrapper);target=a.out/'tail-selector.o';command[command.index('-o')+1]=str(target)
    run(command,'native-selector')
    result=copy.deepcopy(old);result.update(selector=record(target),new_selector_controls=checks,cold_output_tail_rows=8,
        original_cold_refinement=record(a.refinement),source_inputs=[record(p) for p in (wrapper,implementation,test)],
        commands=old['commands']+commands,prior_graph_and_phase_controls_replayed=0,native_model_qualified=False,
        native_model_rate_measured=False,production_adopted=False)
    save(a.out/'result.private.json',result);print(dict(completed=True,new_tail_controls=16,cold_output_rows=8,PS5_operations=0))


if __name__=='__main__':main()
