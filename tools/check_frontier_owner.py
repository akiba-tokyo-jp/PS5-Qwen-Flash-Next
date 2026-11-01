#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check the real frontend certificate with ownership and journal invalidations."""
import argparse,os,subprocess
from pathlib import Path
from build_frontier_owner import transform,ROOT
from build_service_completion import transform as idle_transform
from build_speculative_batch_probe import once
from expert_q4 import record,require,write_json

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in('workspace','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);src=a.out/'lifecycle.cpp';src.write_text(transform(idle_transform((ROOT/'native/app/driver_lifecycle.cpp').read_text())),newline='\n')
 test=(ROOT/'tests/driver_lifecycle.cpp').read_text();prefix='''#include "service_options.h"
#include "frontier_options.h"
#include "owner_checkpoint_certificate.h"
static ps5_ai_native_arena_journal_stats mock_journal{1,1,1,1,1,1,48};
static ps5_ai_arena_stats mock_owner{};
extern "C" void ps5_ai_native_arena_journal_snapshot(ps5_ai_native_arena_journal_stats*out){*out=mock_journal;}
'''
 test=prefix+test;test=once(test,'*out={};if(mode==6)','*out=mock_owner;if(mode==6)');test=once(test,'bool checkpoint() {++checkpoints;return true;}','bool checkpoint() {++checkpoints;++mock_journal.records;++mock_journal.fsync_calls;return mock_journal.log_healthy==1;}')
 marker='        std::cout<<"Own log before sole AGC8'
 block='''        qwen_service::mode=4;qwen_frontier::mode=1;
        reset(0);DriverLifecycle cached(ops);current=&cached;cached.initialize("own.log");cached.begin_work();cached.register_device(99);cached.before_submit();cached.after_submit();
        cached.checkpoint_work();check(waits==1&&checkpoints==2&&retires==1);
        cached.checkpoint_work();check(waits==1&&checkpoints==2&&retires==2);
        ++mock_owner.allocation_attempts; // Equal live byte/node totals still invalidate.
        cached.checkpoint_work();check(checkpoints==3);
        cached.checkpoint_work();check(checkpoints==3);
        ++mock_owner.used_bytes;cached.checkpoint_work();check(checkpoints==4);
        ++mock_journal.records;cached.checkpoint_work();check(checkpoints==5);
        cached.before_submit();cached.after_submit();cached.checkpoint_work();check(waits==2&&checkpoints==6);
        cached.complete_work();check(checkpoints==6&&retires==8&&!retains);
        mock_owner={};
        for(int fault:{8,9,10,11,12}) {
            reset(0);DriverLifecycle bad(ops);current=&bad;bad.initialize("own.log");bad.begin_work();bad.register_device(99);bad.before_submit();bad.after_submit();bad.checkpoint_work();mode=fault;
            refused([&]{bad.complete_work();});check(bad.faulted()&&retains==1);
        }
        reset(0);DriverLifecycle log_bad(ops);current=&log_bad;log_bad.initialize("own.log");log_bad.begin_work();log_bad.register_device(99);log_bad.before_submit();log_bad.after_submit();log_bad.checkpoint_work();mock_journal.log_healthy=0;
        refused([&]{log_bad.complete_work();});check(log_bad.faulted()&&retains==1);mock_journal.log_healthy=1;
        qwen_frontier::mode=0;qwen_service::mode=0;
'''
 test=once(test,marker,block+marker);test=once(test,'void check(bool value) {if(!value)throw std::runtime_error("Native lifecycle API-stub contract failed");}','void check_at(bool value,int line) {if(!value)throw std::runtime_error("Native lifecycle API-stub contract failed at line "+std::to_string(line));}\n#define check(value) check_at((value),__LINE__)');fixture=a.out/'fixture.cpp';fixture.write_text(test,newline='\n');host=a.workspace/'toolchain/msys-clang64/clang64/bin';env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''));exe=a.out/'fixture.exe'
 commands=[[str(host/'clang++.exe'),'-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'native/app'),str(src),str(fixture),'-o',str(exe)],[str(exe)]]
 for i,c in enumerate(commands):
  r=subprocess.run(c,capture_output=True,env=env,timeout=90);(a.out/f'{i}.private.log').write_bytes(r.stdout+r.stderr);require(r.returncode==0,r.stderr.decode(errors='replace'));print(r.stdout.decode(errors='replace').strip()or'Focused owner certificate source compiled')
 write_json(a.out/'receipt.private.json',dict(completed=True,original_refusals_preserved=True,allocation_ABA_invalidates=True,journal_change_invalidates=True,byte_change_invalidates=True,new_submit_invalidates=True,log_failure_retains=True,sources=[record(src),record(fixture)],PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()
