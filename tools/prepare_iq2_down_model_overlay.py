#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Prepare all48 inverse-qualified IQ2 Down carriers over the selected model."""
import argparse
import collections
import copy
import hashlib
import json
from pathlib import Path
import sys
import types
from build_performance_quantizer import record
from prepare_iq2_up_model_overlay import literal, rewrite_header, selected_header
from prepare_shared_q4 import REVISION
from resident_all_q8 import placement
from start_success_route import load, need, save


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('current','cache','carriers','native-proof','out'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();finished,native=load(a.carriers),load(a.native_proof)
    need(finished['completed'] and native['completed'] and native['native_passed'] and
         native['GGML_carrier_ABI'] and native['ordinary_exit_observed'] and
         native['current_seven_restored_and_native_hashed'],'Complete carrier conversion and native arithmetic retirement required')
    terminal=load(native['native']['path'])
    need(record(native['native']['path'])==native['native'] and terminal['all_outputs_passed'] and
         terminal['completed_GGML_case_prefix']==2 and len(terminal['cases'])==10,
         'The ten positive changed GGML cases with the separately bound two-case prefix are required')
    rows=finished['parts']
    need([r['layer'] for r in rows]==list(range(48)),'A complete uniform48-layer Down source is required')
    selected=load(a.current/'provenance/selected-entry-build.private.json')
    policy=load(selected['application_policy']['path'])
    header=Path(policy['source']['path']).parent/'precision-plan.private.h';text=header.read_text()
    old_raw,parent_raw=literal(text,'precision_candidate_raw'),literal(text,'precision_parent_raw')
    need(hashlib.sha256(old_raw.encode()).hexdigest()==literal(text,'precision_candidate_sha256') and
         hashlib.sha256(parent_raw.encode()).hexdigest()==literal(text,'precision_parent_sha256'),
         'The selected complete model ancestry changed')
    old,parent=json.loads(old_raw),json.loads(parent_raw)
    need(old['precision_candidate']=='dense-Q4' and len(old['precision_overlay']['tensors'])==109,
         'The selected complete dense overlay is required')
    candidate=copy.deepcopy(old);detail=candidate['precision_overlay']
    retained=copy.deepcopy(detail['parts']);parts=retained.copy()
    for part in retained:
        need(Path(part['path']).stat().st_size==part['bytes'],'A selected retained extent changed')
    tensors={t['name']:t for t in candidate['tensors']};before={t['name']:t for t in old['tensors']}
    receipts=[];changed_files=set();importance=None
    for row in rows:
        proof=load(row['result']['path'])
        need(record(row['result']['path'])==row['result'] and proof['completed'] and proof['role']=='down' and
             proof['layer']==row['layer'] and proof['planes']==512 and proof['plane_bytes']==460800 and
             proof['original_encoded_bytes_preserved'] and proof['all_complete_carriers_independently_inverse_verified'] and
             proof['Q2_0_carrier_type_is_not_the_encoded_weight_format'] and proof['pack']==row['pack'],
             'Every whole carrier must retain its independent inverse proof')
        pack=Path(proof['pack']['path'])
        need(pack.stat().st_size==235929600 and pack.stat().st_mtime_ns<=Path(row['result']['path']).stat().st_mtime_ns,
             'A completed whole carrier changed after its receipt')
        encoded=load(proof['encoded_layer']['path'])
        need(record(proof['encoded_layer']['path'])==proof['encoded_layer'] and encoded['completed'] and
             encoded['role']=='down' and encoded['layer']==row['layer'] and encoded['codec']=='IQ2_XXS' and
             encoded['logical_shape']==[640,2560,512] and encoded['encoded_row_shape']==[1280,1280] and
             encoded['paired_original_rows'] and encoded['encoded_Experts']==512 and not encoded['host_model_inference'] and
             encoded['original_BF16_source']['path'].replace('\\','/').startswith(a.cache.as_posix()+'/converted-bf16-002/'),
             'Every carrier must derive directly from its paired original BF16 Down encoding')
        if importance is None:importance=encoded['importance']
        need(encoded['importance']==importance,'One actual prefill-only calibration is required')
        name='blk.'+str(row['layer'])+'.ffn_down_exps.weight';original=before[name];target=tensors[name]
        need(original['type']=='Q2_0' and original['shape']==[640,2560,512] and original['bytes']==235929600,
             'The selected Down cache ABI changed')
        index=len(parts);parts.append(proof['pack']);target['payload_sha256']=proof['pack']['sha256']
        detail['tensors'].append(dict(name=name,part=index,pack_offset=0,bytes=235929600,original_bytes=235929600,
            parent_payload_sha256=original['payload_sha256'],payload_sha256=proof['pack']['sha256'],type='Q2_0',
            encoded_format='paired-row IQ2_XXS',storage_format='sealed Q2_0 ABI carrier',
            original_BF16_encoding=proof['encoded_layer'],carrier= row['result'],original_BF16_direct_quantization=True))
        receipts.append(row['result']);changed_files.add(original['file'])
    package=types.ModuleType('gguf');package.__path__=[str(a.cache/('upstream/llama.cpp-'+REVISION)/'gguf-py/gguf')]
    sys.modules['gguf']=package
    from gguf.constants import GGMLQuantizationType as Type
    kinds={v.name:int(v) for v in Type}
    a.out.mkdir(parents=True,exist_ok=False);header_path=a.out/'IQ2-Down-headers.bin'
    rebuilt=[];base_headers=None;header_index=len(parts)
    with header_path.open('xb') as stream:
        for name in sorted(changed_files):
            raw,base_headers=selected_header(old,parent,retained,name,base_headers)
            left=[t for t in old['tensors'] if t['file']==name];right=[t for t in candidate['tensors'] if t['file']==name]
            raw,end=rewrite_header(raw,left,right,kinds)
            need(end<=next(f['bytes'] for f in old['files'] if f['path']==name),'The selected logical extent changed')
            stream.write(bytes((-stream.tell())%16384));offset=stream.tell();stream.write(raw)
            rebuilt.append(dict(file=name,part=header_index,pack_offset=offset,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
    parts.append(record(header_path))
    detail['headers']=[h for h in detail['headers'] if h['file'] not in changed_files]+rebuilt
    detail.update(mode='dense-Q4-and-IQ2-Down-carriers',parts=parts,IQ2_Down_layers=list(range(48)),
        original_selected_cache_slots=3712,old_bundle_payloads_compatible=False,compressed_cache_or_IO_saving_claimed=False,
        prefill_only_importance=importance,current_Q2_requantization=False)
    candidate['precision_candidate']=detail['mode'];path=a.out/'model-receipt.json'
    path.write_text(json.dumps(candidate,separators=(',',':'))+'\n',newline='\n')
    need(path.stat().st_size<=1<<20,'The original bounded model-receipt extent is required')
    footprint=collections.Counter()
    for tensor in candidate['tensors']:footprint[placement(tensor['name'])]+=tensor['bytes']
    save(a.out/'result.private.json',dict(completed=True,selected_header=record(header),selected_model_sha256=hashlib.sha256(old_raw.encode()).hexdigest(),
        parent_model_sha256=hashlib.sha256(parent_raw.encode()).hexdigest(),candidate=record(path),IQ2_Up_layers=[],IQ2_Down_layers=list(range(48)),
        selected_tensors=len(detail['tensors']),retained_precision_parts=retained,new_parts=parts[len(retained):],footprint=dict(footprint),
        carriers=record(a.carriers),native_operator_proof=record(a.native_proof),completed_encoding_receipts=receipts,
        host_payload_rehash_deferred_to_native_sealing=True,complete_native_SHA256_EOF_sealing_required_before_model_admission=True,
        all_changed_headers_independently_parsed=True,old_bundle_payloads_must_be_rebuilt_or_disabled=True,
        unchanged_cache_and_source_payload_bytes=True,compressed_cache_or_IO_saving_claimed=False,PS5_operations=0,
        native_source_publication_and_model_quality_and_rate_qualified=False))
    print(dict(completed=True,IQ2_Down_layers=48,new_parts=len(parts)-len(retained),PS5_operations=0))


if __name__=='__main__':
    main()
