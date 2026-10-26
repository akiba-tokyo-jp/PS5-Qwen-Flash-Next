#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Price an unlinked 54-slot byte-storage view with actual GGML metadata only."""
import argparse,json,os,subprocess
from pathlib import Path
from check_model_checkpoint import record
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in('workspace','cache','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    up=a.cache/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569';host=a.workspace/'toolchain/msys-clang64/clang64/bin'
    candidates=list((a.cache/'host-CPU-reference-066/build').rglob('ggml-base.a'))+list((a.cache/'host-CPU-reference-066/build').rglob('libggml-base.a'))
    if len(candidates)!=1:raise ValueError('Exact existing metadata provider required')
    library=candidates[0];test=ROOT/'tests/packed_cache_geometry.cpp';exe=a.out/'packed-cache-metadata.exe'
    command=[str(host/'clang++.exe'),'-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'native/app'),'-I',str(up/'ggml/include'),
        str(test),str(library),'-o',str(exe)]
    files=[Path(__file__),test,library,ROOT/'native/app/padded_bank.h',ROOT/'native/app/padded_bank_layout.h',up/'ggml/include/ggml.h'];fixed=[record(f)for f in files]
    env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''))
    for i,c in enumerate((command,[str(exe)])):
        r=subprocess.run(c,capture_output=True,env=env,timeout=120);(a.out/(str(i)+'.private.log')).write_bytes(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace')[-3000:])
    result=json.loads(r.stdout);assert result['original_residue_role_views']==60 and result['bounded_read_envelopes']==3240
    assert fixed==[record(f)for f in files]
    (a.out/'receipt.private.json').write_text(json.dumps(dict(controls=result,inputs=fixed,command=command,native_54_slot_quality_qualified=False,PS5_operations=0),indent=2)+'\n')
    print(json.dumps(result),flush=True)
if __name__=='__main__':main()
