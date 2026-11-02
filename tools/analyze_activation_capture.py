#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Validate a positively closed real PS5 stream and accumulate sparse importance."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

from build_performance_quantizer import record
from start_success_route import load,need,save

ALIGN=16384


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();run=load(args.capture)
    need(run['completed'] and run['native_and_host_whole_SHA256_equal'] and run['native_requests']==1,
         'A complete native stream downloaded after ordinary restoration is required')
    for key in ('case','closure','capture','raw'):need(record(run[key]['path'])==run[key],'Bound native capture evidence changed')
    closed=load(run['closure']['path']);case=load(run['case']['path']);capture=load(run['capture']['path'])
    need(closed['completed'] and closed['ordinary_exit_observed'] and closed['current_seven_restored_and_native_hashed'] and
         not closed['unknown_completion'] and capture['completed'] and capture['full_native_SHA256_and_EOF_verified'],
         'Positive resource retirement, close and complete native file seal required')
    need(run['raw']['bytes']==capture['bytes'] and run['raw']['sha256']==capture['sha256'],'Independent whole-stream digests differ')
    import numpy as np
    args.out.mkdir(parents=True,exist_ok=False)
    accum={};seen={};record_count=0;payload_bytes=0;by_evaluation={};rows=0
    with Path(run['raw']['path']).open('rb') as stream:
        header=stream.read(ALIGN);need(len(header)==ALIGN and header[:8]==b'QWENACT1','Exact stream header required')
        version,size,limit,json_size=struct.unpack_from('<IIQI',header,8)
        need((version,size,limit)==(1,ALIGN,256<<20) and 0<json_size<=ALIGN-128 and
             not any(header[28:128]) and not any(header[128+json_size:]),'Header bounds or zero padding differs')
        binding=json.loads(header[128:128+json_size]);gate=load(Path(run['case']['path']).parent/'development.json')['native_first_generation_validation']
        need(binding['run_id']==case['run_id'] and binding['candidate_SELF_sha256']==case['SELF']['sha256'] and
             binding['model_receipt_sha256']==gate['model_receipt_sha256'] and binding['scope']['headless'],
             'The raw stream must bind the actual run, SELF and current model')
        while True:
            header=stream.read(ALIGN)
            if not header:break
            need(len(header)==ALIGN and header[:8]==b'QACTREC1','Record header is truncated or invalid')
            evaluation,role,layer,k,tokens,xslots,selected,payload,padded,weight_type=struct.unpack_from('<Q6I2QI',header,8)
            need(1<=evaluation<=33 and role in (0,1) and layer<48 and k==(640 if role else 2560) and
                 1<=tokens<=32 and 1<=selected<=10 and xslots in (1,selected) and (not role or xslots==selected) and
                 payload==tokens*xslots*k*4 and padded==(payload+ALIGN-1)//ALIGN*ALIGN and ALIGN+padded<=4<<20,
                 'Actual operand geometry or bounded record extent differs')
            ids=np.frombuffer(header,dtype='<i4',count=tokens*selected,offset=64).reshape(tokens,selected).copy()
            slots=np.frombuffer(header,dtype='<i4',count=tokens*selected,offset=1344).reshape(tokens,selected).copy()
            need((ids>=0).all() and (ids<512).all() and (slots>=0).all() and (slots<3713).all() and
                 all(len(set(map(int,row)))==selected for row in ids),'Original Expert IDs or physical slot IDs differ')
            need(not any(header[60:64]) and not any(header[64+4*tokens*selected:1344]) and
                 not any(header[1344+4*tokens*selected:]),'Record reserved bytes or padding changed')
            raw=stream.read(padded);need(len(raw)==padded and not any(raw[payload:]),'Payload padding or EOF differs')
            values=np.frombuffer(raw,dtype='<f4',count=payload//4).reshape(tokens,xslots,k)
            need(np.isfinite(values).all(),'Independent host activation finite check failed')
            key=(evaluation,layer,role);need(key not in seen,'Duplicate layer/role record')
            seen[key]=(ids,slots);peer=seen.get((evaluation,layer,1-role))
            if peer is not None:need(np.array_equal(ids,peer[0]) and np.array_equal(slots,peer[1]),'Up/Down original selection or slot mapping differs')
            shape=(tokens,selected)
            need(evaluation not in by_evaluation or by_evaluation[evaluation]==shape,'One graph has inconsistent layer widths')
            by_evaluation[evaluation]=shape
            group=accum.setdefault((layer,role),dict(experts={},total=np.zeros(k,np.float64),count=0,weight_types=set()))
            squares=np.square(values,dtype=np.float64)
            group['total']+=squares.sum(axis=(0,1));group['count']+=tokens*xslots;group['weight_types'].add(weight_type)
            for token in range(tokens):
                for slot in range(selected):
                    expert=int(ids[token,slot]);entry=group['experts'].setdefault(expert,[np.zeros(k,np.float64),0])
                    entry[0]+=squares[token,0 if xslots==1 else slot];entry[1]+=1
            record_count+=1;payload_bytes+=payload;rows+=tokens*xslots
    evaluations=len(by_evaluation)
    need(set(by_evaluation)==set(range(1,evaluations+1)) and record_count==96*evaluations==capture['records'] and
         evaluations==capture['evaluations'] and len(accum)==96 and
         set(seen)=={(e,l,r) for e in range(1,evaluations+1) for l in range(48) for r in range(2)},
         'Every evaluation must contain both original operands for all48 layers')
    coverage=[];outputs=[]
    for (layer,role),group in sorted(accum.items()):
        experts=sorted(group['experts']);counts=np.array([group['experts'][e][1] for e in experts],np.uint64)
        sums=np.stack([group['experts'][e][0] for e in experts]);fallback=group['total']/group['count']
        need(np.isfinite(sums).all() and np.isfinite(fallback).all() and np.all(sums>=0) and np.all(fallback>=0) and
             np.any(fallback>0),'Measured second moments are invalid or empty')
        label='down' if role else 'up';path=args.out/('layer-'+str(layer).zfill(2)+'-'+label+'.npz')
        np.savez_compressed(path,expert_ids=np.array(experts,np.int32),sum_squares=sums,counts=counts,
                            real_layer_mean_square=fallback,layer=np.array(layer,np.int32),role=np.array(role,np.int32))
        outputs.append(record(path));coverage.append(dict(layer=layer,role=label,visited_Experts=len(experts),
            unvisited_Experts_using_real_layer_mean=512-len(experts),selected_token_samples=int(counts.sum()),
            real_input_vectors=group['count'],actual_weight_types=sorted(group['weight_types'])))
    save(args.out/'result.private.json',dict(completed=True,native_capture=record(args.capture),bound_run=binding,
        evaluations=evaluations,records=record_count,payload_bytes=payload_bytes,real_input_vectors=rows,coverage=coverage,outputs=outputs,
        moments='F64 sums of squared actual F32 indexed-matmul inputs; divide each Expert sum by its actual sample count',
        unvisited_Expert_fallback='Measured real per-layer mean square for the same operand; coverage is explicit',
        synthetic_uniform_importance_used=False,up_and_down_operands_independently_observed=True,
        Gate_input_sharing_with_Up_not_independently_qualified=True,calibration_prompts=1,broad_calibration_coverage_qualified=False,
        real_model_IQ2_encoded=False,native_IQ2_operator_qualified=False,learned_host_inference=False,PS5_operations=0,production_adopted=False))
    print(json.dumps(dict(completed=True,evaluations=evaluations,records=record_count,importance_files=len(outputs),
        real_PS5_activation_moments=True,Gate_input_sharing_qualified=False,production_adopted=False)))


if __name__=='__main__':main()
