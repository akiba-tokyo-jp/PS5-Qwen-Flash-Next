#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check the actual ready-wave coordinator and two-call controller without I/O."""
import argparse,json,os,subprocess
from pathlib import Path
from build_preservation_integrity import record
ROOT=Path(__file__).resolve().parents[1]
SCENARIOS=('overlap','serial','before-start','null-callback','invalid-mode','aliased-groups',
    'already-bound','wrong-thread','first-exception','second-exception','missing-role','cancel-before-second',
    'repeat-start','repeat-release','repeat-join','first-deadline','second-deadline','wrong-active-wave','early-release')
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in('workspace','cache','qualified-native','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);host=a.workspace/'toolchain/msys-clang64/clang64/bin'
    test=ROOT/'tests/ready_source_coordinator.cpp';exe=a.out/'ready-source.exe'
    host_cmd=[str(host/'clang++.exe'),'-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'native/app'),str(test),'-o',str(exe)]
    prior=json.loads(a.qualified_native.read_text());native=next(c.copy()for c in prior['compile_commands']if '-c'in c and Path(c[c.index('-c')+1]).name=='native_main.cpp')
    native[native.index('-c')+1]=str(test);native[native.index('-o')+1]=str(a.out/'ready-source-PS5.o');native+=['-Wall','-Wextra','-Werror']
    files=[Path(__file__),test,a.qualified_native,*[ROOT/'native/app'/n for n in('ready_source_coordinator.h','ready_expert_wave.h','split_padded_bank.h','padded_bank.h','vectored_source_batch.h')]]
    fixed=[record(f)for f in files];env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''));controls=[]
    for i,c in enumerate([host_cmd,*[[str(exe),s]for s in SCENARIOS],native]):
        r=subprocess.run(c,capture_output=True,timeout=60,env=env);(a.out/f'{i}.private.log').write_bytes(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError('Ready coordinator step '+str(i)+': '+r.stderr.decode(errors='replace')[-3000:])
        if 1<=i<=len(SCENARIOS):
            result=json.loads(r.stdout);assert result['passed']and result['GPU_calls']==result['file_reads']==result['PS5_operations']==0
            controls.append(dict(scenario=SCENARIOS[i-1],**result))
    assert controls[0]['callbacks_during_GPU_lease']==15 and controls[0]['peak_two_call_depth']==2
    assert controls[1]['callbacks_during_GPU_lease']==0 and controls[1]['peak_two_call_depth']==2
    assert fixed==[record(f)for f in files]
    result=dict(schema='ps5-qwen-ready-source-coordinator-host-v1',inputs=fixed,commands=[host_cmd,native],controls=controls,
        actual_application_scheduler_and_two_call_controller=True,native_SDK_object=record(a.out/'ready-source-PS5.o'),
        physical_backing_or_GPU_overlap_qualified=False,PS5_operations=0,CI_runs=0)
    (a.out/'receipt.private.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(scenarios=len(controls),actual_two_call_depth_preserved=True,native_SDK_compiled=True,PS5_operations=0)),flush=True)
if __name__=='__main__':main()
