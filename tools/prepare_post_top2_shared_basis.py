#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Prepare a one-layer rank32 residual prototype; no activation/model inference."""
import argparse,hashlib,json,os,sys,types
from pathlib import Path
from expert_q4 import record,require,write_json

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in('capture','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();capture=json.loads(a.capture.read_text());require(capture['completed']and capture['GPU_calls']==capture['title_launches']==0 and len(capture['selected_source_triplets'])==3,'Complete same-layer native sample capture required')
 require(len({x['layer']for x in capture['selected_source_triplets']})==1 and record(capture['local']['path'])==capture['local'],'Exact same-layer bytes required')
 for k in('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='2'
 import numpy as np
 base=a.cache/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569/gguf-py/gguf';pkg=types.ModuleType('gguf');pkg.__path__=[str(base)];sys.modules['gguf']=pkg
 from gguf.constants import GGMLQuantizationType as Type
 from gguf.quants import quantize,dequantize
 a.out.mkdir(parents=True,exist_ok=False);data=Path(capture['local']['path']).read_bytes();rank=32;rng=np.random.default_rng(20261101);sections=[];payload=bytearray();metrics={}
 def append(name,values,kind,ne):
  array=np.ascontiguousarray(values,dtype=np.uint8);offset=(len(payload)+65535)//65536*65536;payload.extend(bytes(offset-len(payload)));raw=array.tobytes();payload.extend(raw)
  sections.append(dict(name=name,type=int(kind),type_name=kind.name,ne=ne,offset=offset,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
 for role,offset in(('gate',0),('up',537600)):
  encoded=np.stack([np.frombuffer(data[i*1540096+offset:i*1540096+offset+537600],dtype=np.uint8).reshape(640,840)for i in range(3)])
  weights=dequantize(encoded,Type.Q2_K).astype(np.float32);require(weights.shape==(3,640,2560)and np.isfinite(weights).all()and np.linalg.norm(weights)>0,'Original Q2_K weight decode failed')
  matrix=weights.reshape(1920,2560);omega=rng.standard_normal((2560,rank+8),dtype=np.float32);q,_=np.linalg.qr(matrix@omega,mode='reduced');_,_,vh=np.linalg.svd(q.T@matrix,full_matrices=False);basis=vh[:rank].astype(np.float32);factors=(matrix@basis.T).reshape(3,640,rank)
  basis_q=quantize(basis,Type.Q8_0);factor_q=quantize(factors,Type.Q8_0);b=dequantize(basis_q,Type.Q8_0);u=dequantize(factor_q,Type.Q8_0)
  shared=(u.reshape(1920,rank)@b).reshape(weights.shape);residual_q=quantize(weights-shared,Type.TQ1_0);flat_q=quantize(weights,Type.TQ1_0)
  restored=dequantize(residual_q,Type.TQ1_0)+shared;flat=dequantize(flat_q,Type.TQ1_0);energy=float(np.mean(np.square(weights,dtype=np.float64)))
  metrics[role]=dict(source_squared_mean=energy,shared_rank=rank,flat_TQ1_relative_squared_error=float(np.mean(np.square(flat-weights,dtype=np.float64)))/energy,
   factored_TQ1_relative_squared_error=float(np.mean(np.square(restored-weights,dtype=np.float64)))/energy,
   original_encoded_bytes_per_Expert=537600,residual_encoded_bytes_per_Expert=residual_q.nbytes//3,factor_bytes_per_Expert=factor_q.nbytes//3,shared_basis_bytes=basis_q.nbytes)
  append('base_'+role,encoded,Type.Q2_K,[2560,640,3]);append('flat_'+role,flat_q,Type.TQ1_0,[2560,640,3]);append('residual_'+role,residual_q,Type.TQ1_0,[2560,640,3]);append('factor_'+role,factor_q,Type.Q8_0,[rank,640,3]);append('basis_'+role,basis_q,Type.Q8_0,[2560,rank])
 final=(len(payload)+65535)//65536*65536;payload.extend(bytes(final-len(payload)));local=a.out/'shared-basis-fixture.private.bin';local.write_bytes(payload)
 original=1536000;candidate=sum(metrics[r]['residual_encoded_bytes_per_Expert']+metrics[r]['factor_bytes_per_Expert']for r in('gate','up'))+460800;shared=sum(metrics[r]['shared_basis_bytes']for r in('gate','up'))
 write_json(a.out/'complete.private.json',dict(completed=True,kind='one_layer_three_Expert_rank32_weight_representation',capture=record(a.capture),dataset=capture['selected_source_triplets'],
  artifact=record(local),sections=sections,rank=rank,metrics=metrics,baseline_Expert_payload_bytes=original,candidate_Expert_payload_bytes=candidate,unchanged_Down_Q2_0_bytes=460800,
  shared_bytes_per_layer=shared,payload_reduction_percent=100*(1-candidate/original),same_selected_Expert_count=True,additional_GPU_math_required=True,
  residual_type='TQ1_0_1.6875bits_per_weight',factor_and_shared_basis_type='Q8_0',not_a_lossless_or_same_bits_reencoding=True,
  only_three_training_Experts=True,held_out_quality_evaluation=False,weight_error_is_not_answer_quality=True,PS5_speed_measured=False,
  learned_host_inference=False,host_weight_factorization_and_quantization_only=True,inputs=[record(__file__),record(base/'constants.py'),record(base/'quants.py')]))
 print(json.dumps(dict(completed=True,rank=rank,bytes=final,payload_reduction_percent=100*(1-candidate/original),candidate_Expert_bytes=candidate,shared_bytes_per_layer=shared,metrics=metrics,learned_host_inference=False)))
if __name__=='__main__':main()
