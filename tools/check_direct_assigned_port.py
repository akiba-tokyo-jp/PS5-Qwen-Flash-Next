#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check the actual assigned-port adapter without opening an OS socket."""
import argparse
import json
import os
from pathlib import Path
import subprocess
from build_performance_quantizer import record
from start_success_route import need,save


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--workspace',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);root=Path(__file__).resolve().parents[1];host=a.workspace/'toolchain/msys-clang64/clang64/bin'
    source=root/'native/qwen_flash_next/direct_stage_assigned_port.h';test=root/'tests/direct_stage_assigned_port_test.c';exe=a.out/'assigned-port-test.exe'
    env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''));command=[str(host/'clang.exe'),'-std=c11','-O2','-Wall','-Wextra','-Werror','-I',str(source.parent),str(test),'-o',str(exe)]
    run=subprocess.run(command,capture_output=True,env=env,timeout=60);(a.out/'build.private.log').write_bytes(run.stdout+run.stderr);need(run.returncode==0,run.stderr.decode(errors='replace'))
    run=subprocess.run([str(exe)],capture_output=True,env=env,timeout=10);need(run.returncode==0,'Actual assigned-port adapter controls failed');result=json.loads(run.stdout)
    need(result['completed'] and result['cases']==10 and result['OS_objects']==0,'All assigned-port controls required')
    result.update(inputs=[record(r) for r in (source,test,Path(__file__))],command=command,PS5_operations=0);save(a.out/'result.private.json',result);print(json.dumps(result))


if __name__=='__main__':main()
