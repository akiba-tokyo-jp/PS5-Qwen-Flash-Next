#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check fixed CPU diagnostic ordering, bounds and policy; no model execution."""
import argparse,json,os,subprocess
from pathlib import Path
from check_model_checkpoint import record
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in('workspace','cache','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);(a.out/'tmp').mkdir()
    policy=json.loads((a.cache/'hardware-first-generation-2601/private-policy/development.json').read_text())
    policy.pop('native_prefix_validation')
    policy['native_metadata_memory_diagnostic']=dict(schema='ps5-qwen-metadata-memory-policy-v1',enabled=True,CPU_only=True,
        maximum_files=76,phases_per_file=5,maximum_records=380,GPU_calls=0,virtual_source_calls=0,ordinary_OS_close_required=True)
    pp=a.out/'policy.private.json';pp.write_text(json.dumps(policy,indent=2)+'\n')
    host=a.workspace/'toolchain/msys-clang64/clang64/bin';up=a.cache/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569'
    exe=a.out/'metadata-memory-tests.exe'
    commands=[[str(host/'clang++.exe'),'-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'native/app'),'-I',str(up/'vendor'),
        str(ROOT/'tests/metadata_memory_probe.cpp'),'-o',str(exe)],[str(exe),str(pp)]]
    inputs=[record(ROOT/n)for n in('native/app/metadata_memory_probe.h','native/app/metadata_memory_policy.h','native/app/native_main.cpp','native/app/validation_policy.h','tests/metadata_memory_probe.cpp','tools/check_metadata_memory_probe.py')]
    env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''),TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp'))
    for i,c in enumerate(commands):
        r=subprocess.run(c,capture_output=True,timeout=120,env=env);(a.out/f'{i}.private.log').write_bytes(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace')[-2000:])
    controls=json.loads(r.stdout);assert controls['all_380_records_exact']and controls['refusals']==31
    assert inputs==[record(Path(x['path']))for x in inputs]
    (a.out/'receipt.private.json').write_text(json.dumps(dict(inputs=inputs,commands=commands,controls=controls,PS5_operations=0,CI_runs=0),indent=2)+'\n')
    print(json.dumps(controls),flush=True)
if __name__=='__main__':main()
