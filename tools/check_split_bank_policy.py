#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Validate exact independent-backing scope and pinned original matrix provenance."""
import argparse,json,os,re,subprocess
from pathlib import Path
from build_preservation_integrity import record
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in('workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    up=a.cache/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569'
    source=ROOT/'native/app/split_bank_admission.cpp';header=ROOT/'native/app/split_bank_admission.h'
    original=a.cache/'vector-bank-assets-2494/policy.private.json';pack=json.loads(original.read_text())
    original_scope=pack.get('native_vector_bank_validation',pack)
    items=original_scope['groups'][0]['matrices']
    rows=re.findall(r'\{(\d+),(\d+),"([0-9a-f]{64})","([0-9a-f]{64})"\}',source.read_text())
    assert len(rows)==6
    assert [dict(offset=int(o),residue=int(r),raw_sha256=h,envelope_sha256=e)for o,r,h,e in rows]==items
    selected=original_scope['packs'][0]
    assert selected==dict(path='/app0/qwen-runtime/vector-bank-0.pack',bytes=63488000,
        sha256='4d6247378c577a586d8cc552b14c771f63a732f8b9762ead8405612aea2d371d')
    host=a.workspace/'toolchain/msys-clang64/clang64/bin';test=ROOT/'tests/split_bank_policy.cpp';exe=a.out/'split-policy.exe'
    commands=[[str(host/'clang++.exe'),'-std=c++17','-O2','-Wall','-Wextra','-Werror',
        '-I',str(ROOT/'native/app'),'-isystem',str(up/'vendor'),str(test),'-o',str(exe)],[str(exe)]]
    files=[Path(__file__),test,source,header,original,up/'vendor/nlohmann/json.hpp'];fixed=[record(f)for f in files]
    env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''));controls=None
    for i,c in enumerate(commands):
        r=subprocess.run(c,capture_output=True,timeout=180,env=env);(a.out/f'{i}.private.log').write_bytes(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace')[-3000:])
        if i==1:controls=json.loads(r.stdout)
    assert controls['exact_scope_passed']and controls['refusal_controls']>=50
    assert fixed==[record(f)for f in files]
    result=dict(schema='ps5-qwen-split-bank-policy-host-v1',inputs=fixed,commands=commands,controls=controls,
        six_matrix_hashes_match_qualified_original_pack=True,new_weight_corpus=False,PS5_operations=0,CI_runs=0)
    (a.out/'receipt.private.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(controls),flush=True)
if __name__=='__main__':main()
