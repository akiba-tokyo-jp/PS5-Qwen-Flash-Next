#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check a past-token-only draft prototype against saved completed token metadata."""
import argparse,json,os,subprocess
from pathlib import Path
from check_model_checkpoint import record
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in('workspace','cache','result','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args()
    if not a.result.resolve().is_relative_to(a.cache.resolve())or a.result.stat().st_size>2<<20:
        raise ValueError('Bounded private completed metadata required')
    source=json.loads(a.result.read_text())
    if(source.get('schema')!='ps5-qwen-plan-validation-result-v1'or source.get('state')!='completed_waiting_for_ordinary_close'or
       source.get('source_pipeline_worker_stopped')is not True or source.get('postload_device_live_bytes')!=0):
        raise ValueError('Positive original completed model result required')
    a.out.mkdir(parents=True,exist_ok=False)
    traces=[source['token_ids']]+[r['token_ids']for r in source['demonstration']['requests']]
    data=a.out/'past-only-traces.private.json';data.write_text(json.dumps(dict(requests=[dict(token_ids=x)for x in traces]))+'\n')
    files=[Path(__file__),ROOT/'native/app/model_free_draft.h',ROOT/'tests/model_free_draft.cpp',a.result,data]
    fixed=[record(f)for f in files];host=a.workspace/'toolchain/msys-clang64/clang64/bin';up=a.cache/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569';exe=a.out/'model-free-draft.exe'
    commands=[[str(host/'clang++.exe'),'-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'native/app'),'-I',str(up/'vendor'),
        str(ROOT/'tests/model_free_draft.cpp'),'-o',str(exe)],[str(exe),str(data)]]
    env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''))
    for i,c in enumerate(commands):
        r=subprocess.run(c,capture_output=True,timeout=120,env=env);(a.out/f'{i}.private.log').write_bytes(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError('Past-only draft check '+str(i)+': '+r.stderr.decode(errors='replace')[-1800:])
    result=json.loads(r.stdout);assert result['input_refusals']==12 and result['past_only_controls_passed']
    assert fixed==[record(f)for f in files]
    (a.out/'receipt.private.json').write_text(json.dumps(dict(inputs=fixed,commands=commands,controls=result,PS5_operations=0,CI_runs=0),indent=2)+'\n')
    print(json.dumps(dict(past_only_controls=True,input_refusals=12,requests=[{k:v for k,v in r.items()if k!='points'}for r in result['requests']],
        prompt_lookup_evaluated_on_model_trace=False,actual_speculative_verification=False,speedup_qualified=False,PS5_operations=0)),flush=True)
if __name__=='__main__':main()
