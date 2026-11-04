#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compare explicit F16 rounding hypotheses with the completed Q2_K negative."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import types

from build_performance_quantizer import record
from prepare_shared_q4 import REVISION
from start_success_route import load,need,save


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('cache','samples','native-component','shader-audit','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();os.environ['OPENBLAS_NUM_THREADS']='6';import numpy as np
    package=types.ModuleType('gguf');package.__path__=[str(a.cache/('upstream/llama.cpp-'+REVISION)/'gguf-py/gguf')];sys.modules['gguf']=package
    from gguf.quants import Q2_K
    sample=load(a.samples);native=load(a.native_component);shaders=load(a.shader_audit)
    need(sample['completed'] and record(sample['pack']['path'])==sample['pack'] and shaders['completed'] and
         shaders['original_encoded_and_SPIRV_bytes_unchanged'],'Exact original encoded weights and selected SPIR-V audit required')
    negative=next(r for r in native['cases'] if not r['all_outputs_and_canaries_passed'])
    need(negative['group']==0 and negative['width']==30 and negative['selected_Experts']==10 and negative['GPU_graphs']==1 and
         negative['mismatches']==73401 and native['all_backends_positively_retired'],'The consumed first Q2_K prefill control must be positively retired')
    width=30;selected=10;columns=2560;rows=640
    x=np.asarray([[(int((col+3*token)%13)-6)/1009.0 for col in range(columns)] for token in range(width)],dtype=np.float32)
    weights=[]
    for matrix in sample['matrices'][:3]:
        part=matrix['Q2_K']
        with Path(sample['pack']['path']).open('rb') as stream:stream.seek(part['offset']);raw=stream.read(part['bytes'])
        need(hashlib.sha256(raw).hexdigest()==part['sha256'],'Whole original Q2_K extent changed')
        weights.append(Q2_K.dequantize(np.frombuffer(raw,np.uint8).reshape(-1,84)).reshape(rows,columns))
    def output(half_weights,half_inputs):
        operands=x.astype(np.float16).astype(np.float32) if half_inputs else x
        result=np.empty((width,selected,rows),np.float64)
        products=[operands.astype(np.float64)@(w.astype(np.float16).astype(np.float32) if half_weights else w).astype(np.float64).T for w in weights]
        for token in range(width):
            for slot in range(selected):
                plane=(slot+token)%10;owner=2 if plane==9 else plane%3;result[token,slot]=products[owner][token]
        return result
    original=output(False,False);cases=[];a.out.mkdir(parents=True,exist_ok=False)
    for hw,hx in ((True,False),(False,True),(True,True)):
        values=output(hw,hx);error=np.abs(values-original);bad=error>(1e-5+2e-4*np.abs(original))
        row=dict(weights_rounded_to_F16=hw,inputs_rounded_to_F16=hx,mismatches_against_original_reference=int(bad.sum()),
            maximum_absolute_error=float(error.max()),mismatch_count_difference_from_native=int(bad.sum())-negative['mismatches'],
            maximum_error_difference_from_native=float(error.max())-negative['maximum_absolute_GPU_reference_error'])
        cases.append(row);print(json.dumps(row),flush=True)
    save(a.out/'result.private.json',dict(completed=True,samples=record(a.samples),native_component=record(a.native_component),
        shader_audit=record(a.shader_audit),source=record(Path(__file__)),cases=cases,output_values=int(original.size),
        original_tolerance_unchanged=True,actual_GPU_outputs_available=False,arithmetic_hypotheses_not_native_output_equivalence=True,
        unchanged_native_case_replayed=False,CPU_reference_correction_qualified=False,PS5_operations=0,production_adopted=False))


if __name__=='__main__':main()
