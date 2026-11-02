#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Read a boot/owner-guarded clock and bind an application-local UTC offset."""
import argparse
import json
from pathlib import Path
import re
import time

from start_success_route import need,save
from success_case_control import build,current_files,execute,lan_module


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','mount-plan','out'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--execute',action='store_true');args=parser.parse_args()
    files=current_files(args.current)
    plan=build(args.workspace,args.mount_plan,files,files,[],'clock',args.out)
    if not args.execute:print('Read-only application clock scope prepared; PS5 operations=0');return
    before=time.time_ns()//1000000;start=time.monotonic_ns()
    execute(lan_module(),plan,args.out)
    elapsed=(time.monotonic_ns()-start)//1000000;after=time.time_ns()//1000000
    raw=(args.out/'execution/console.private.log').read_bytes()
    samples=re.findall(rb'CURRENT_CLOCK seconds=(\d+) nanoseconds=(\d+)',raw)
    need(len(samples)==1,'One guarded native clock observation required')
    interval=after-before
    need(0<=interval<=8000 and abs(interval-elapsed)<=250,'Bounded continuous host UTC interval required')
    seconds,nanoseconds=map(int,samples[0]);console=seconds*1000+nanoseconds//1000000
    need(0<=nanoseconds<1000000000 and abs((before+after)//2-console)<=86400000,'Bounded application-only clock offset required')
    clock=dict(schema='ps5-qwen-clock-offset-v1',console_epoch_ms=console,utc_epoch_ms=(before+after)//2,
               uncertainty_ms=(interval+1)//2+1)
    need(clock['uncertainty_ms']<=5000,'Native monitor clock uncertainty exceeded its bound')
    save(args.out/'clock.private.json',clock)
    save(args.out/'host-interval.private.json',dict(before_ms=before,after_ms=after,monotonic_elapsed_ms=elapsed))
    print(json.dumps(dict(completed=True,uncertainty_ms=clock['uncertainty_ms'],system_clock_writes=0,
                         initializer_requests=0,GPU_calls=0,title_launches=0)))


if __name__=='__main__':main()
