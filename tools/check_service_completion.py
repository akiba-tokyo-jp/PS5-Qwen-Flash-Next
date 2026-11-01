#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Focused API-stub checks of positive-generation reuse and required invalidation."""
import argparse,json,os,subprocess
from pathlib import Path
from build_service_completion import transform,ROOT
from build_speculative_batch_probe import once
from expert_q4 import require,record,write_json
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in('workspace','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);src=a.out/'lifecycle.cpp';src.write_text(transform((ROOT/'native/app/driver_lifecycle.cpp').read_text()),newline='\n');test=(ROOT/'tests/driver_lifecycle.cpp').read_text();test='#include "service_options.h"\n'+test
 marker='        std::cout<<"Own log before sole AGC8'
 block='''        qwen_service::mode=4;
        reset(0);DriverLifecycle cached(ops);current=&cached;cached.initialize("own.log");cached.begin_work();cached.register_device(99);cached.before_submit();cached.after_submit();
        cached.checkpoint_work();check(waits==1&&retires==1);
        cached.checkpoint_work();check(waits==1&&retires==2&&!retains);
        cached.before_submit();cached.after_submit();cached.checkpoint_work();check(waits==2&&retires==3);
        cached.complete_work();check(waits==2&&retires==4&&!retains);
        for(int fault:{8,9,10,11,12}){
            reset(0);DriverLifecycle bad(ops);current=&bad;bad.initialize("own.log");bad.begin_work();bad.register_device(99);bad.before_submit();bad.after_submit();bad.checkpoint_work();check(waits==1);mode=fault;
            refused([&]{bad.complete_work();});check(bad.faulted()&&retains==1);
        }
        qwen_service::mode=0;
'''
 test=once(test,marker,block+marker);fixture=a.out/'fixture.cpp';fixture.write_text(test,newline='\n');host=a.workspace/'toolchain/msys-clang64/clang64/bin';env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''));exe=a.out/'fixture.exe';commands=[[str(host/'clang++.exe'),'-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'native/app'),str(src),str(fixture),'-o',str(exe)],[str(exe)]]
 for i,c in enumerate(commands):
  result=subprocess.run(c,capture_output=True,env=env,timeout=90);(a.out/f'{i}.private.log').write_bytes(result.stdout+result.stderr);require(result.returncode==0,result.stderr.decode(errors='replace'));print(result.stdout.decode(errors='replace').strip()or'Focused contract source compiled')
 write_json(a.out/'receipt.private.json',dict(completed=True,original_refusals_preserved=True,positive_generation_reuse=True,new_submit_invalidates=True,pending_epoch_log_snapshot_retirement_faults_retained=True,sources=[record(src),record(fixture)],PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()
