#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Audit saved allocation/graph evidence without model evaluation or console access."""
import argparse,json,struct
from pathlib import Path
from check_model_checkpoint import record

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in('cache','native-link-receipt','self-receipt','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    headers=a.cache/'performance-layout-screen-1374/headers.private.json'
    graph=a.cache/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569/src/models/qwen4exp.cpp'
    perf=a.cache/'hardware-first-generation-2240/native-plan-observation'
    profiles=[perf/('native-result.private.json.'+name+'.performance')for name in('demo1','demo2')]
    files=[Path(__file__),headers,graph,a.native_link_receipt,a.self_receipt,*profiles]
    link=json.loads(a.native_link_receipt.read_text());package=json.loads(a.self_receipt.read_text())
    if not link['input_hashes_stable'] or not package['integrity_verified'] or not package['roundtrip_segments_verified']:
        raise ValueError('Completed native link and SELF evidence required')
    elf=Path(package['converted_elf']['path']);files.append(elf);fixed=[record(f)for f in files]
    tensors=[t for h in json.loads(headers.read_text())for t in h['tensors']if t['name'].startswith('blk.')and int(t['name'].split('.')[1])<48]
    summaries={}
    for suffix,count,dtype,shape in(
        ('ssm_a',36,0,[48]),('ssm_dt.bias',36,0,[48]),('ffn_gate_inp.weight',48,0,[2560,512]),
        ('ple_conv1d.weight',1,30,[4,10240]),('attn_qkv.weight',36,30,[2560,10240]),
        ('attn_gate.weight',36,30,[2560,6144])):
        selected=[t for t in tensors if t['name'].endswith('.'+suffix)]
        if len(selected)!=count or any(t['type']!=dtype or t['shape']!=shape for t in selected):
            raise ValueError('Original tensor eligibility changed: '+suffix)
        summaries[suffix]=dict(count=count,GGML_type=dtype,shape=shape,total_bytes=sum(t['bytes']for t in selected))
    source=graph.read_text()
    markers=['ggml_tensor * alpha_biased   = ggml_add(ctx0, alpha, model.layers[il].ssm_dt);',
        'ggml_tensor * alpha_softplus = ggml_softplus(ctx0, alpha_biased);',
        'ggml_tensor * gate = ggml_mul(ctx0, alpha_softplus, model.layers[il].ssm_a);',
        'ggml_tensor * wk = ggml_cont(ctx0,','if (wk->type != GGML_TYPE_F32)',
        'wk = ggml_cast(ctx0, wk, GGML_TYPE_F32);','ggml_tensor * gated = ggml_sigmoid(ctx0, gate);']
    if any(x not in source for x in markers):raise ValueError('Audited graph operations changed')
    with elf.open('rb')as f:
        h=f.read(64)
        if h[:6]!=b'\x7fELF\x02\x01':raise ValueError('Expected little-endian ELF64')
        offset=struct.unpack_from('<Q',h,32)[0];entry,count=struct.unpack_from('<HH',h,54);segments=[]
        if entry<56 or count>64:raise ValueError('Unexpected program-header bounds')
        for i in range(count):
            f.seek(offset+i*entry);r=struct.unpack('<IIQQQQQQ',f.read(56))
            if r[0]==1:
                if r[6]<r[5]:raise ValueError('Invalid mapped segment extent')
                segments.append(dict(flags=r[1],file_bytes=r[5],memory_bytes=r[6],zero_fill_bytes=r[6]-r[5]))
    costs=[]
    for name,path in zip(('first_external','repeated_external'),profiles):
        j=json.loads(path.read_text());d=j['delta']
        if j['prefill_batch_tokens']!=4 or j['generated_token_batch_tokens']!=1 or d['process_calls']!=30:
            raise ValueError('Completed fixed workload profile changed')
        # Width four is the largest measured clear/add/set metadata loop.
        # Applying it to EVERY process overestimates even that microbenchmark
        # opportunity; it does not bound unmeasured context/backend metadata.
        metadata_ns=d['process_calls']*4446.675290
        costs.append(dict(request=name,process_ns=d['process_ns'],source_producer_wait_ns=d['source_read_ns'],
            unpartitioned_non_source_remainder_ns=d['process_ns']-d['source_read_ns'],
            all_width_four_batch_microbenchmark_opportunity_ns=metadata_ns,
            batch_microbenchmark_opportunity_fraction=metadata_ns/d['process_ns']))
    assert fixed==[record(f)for f in files]
    result=dict(schema='ps5-qwen-remaining-feasibility-audit-v1',tensor_metadata=summaries,profiles=costs,
        mapped_ELF_segments=segments,total_zero_fill_bytes=sum(s['zero_fill_bytes']for s in segments),
        invariant_GDN_parameters_already_F32=True,dynamic_alpha_softplus_must_remain=True,
        PLE_tap_gather_and_lossless_BF16_to_F32_cast_recur=True,PLE_tap_reuse_F32_bytes=4*10240*4,
        dual_projection_original_BF16_bytes_per_recurrent_layer=2560*(10240+6144)*2,
        dual_projection_logical_F32_input_bytes_width_one=2560*4,
        additional_physical_headroom_proven=False,physical_allocation_lifetime_measurement_complete=False,
        native_kernel_memory_decline_cause_identified=False,PS5_operations=0,model_arithmetic=False,CI_runs=0)
    (a.out/'receipt.private.json').write_text(json.dumps(dict(result,inputs=fixed),indent=2)+'\n')
    print(json.dumps(result),flush=True)
if __name__=='__main__':main()
