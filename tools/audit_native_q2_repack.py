#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Audit compact headers and exact native payload proof without retransferring weights."""
import argparse,hashlib,json,sys,types
from pathlib import Path
from expert_q4 import LOCK,require,record,write_json
from audit_shared_q8_headers import parse

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('preparation','cache','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();prep=json.loads(a.preparation.read_text());require(prep['completed']and prep['mode']=='expert-Q2_0','Completed native preparation required')
    for r in (prep['candidate'],prep['parent'],prep['native_generation']):require(record(r['path'])==r,'Native preparation provenance changed')
    done=json.loads(Path(prep['native_generation']['path']).read_text());require(done['completed']and done['Direct_positively_released']and done['current_input_whole_SHA256_passed']and done['all_output_whole_SHA256_and_EOF_passed'],'Complete native input/output proof required')
    parent=json.loads(Path(prep['parent']['path']).read_text());candidate=json.loads(Path(prep['candidate']['path']).read_text());details=candidate['precision_overlay'];tensors={t['name']:t for t in candidate['tensors']};old={t['name']:t for t in parent['tensors']};names={t['name']for t in details['tensors']}
    require(len(names)==len(details['tensors'])==len(done['parts'])==96,'All96 routed Gate/Up tensors required')
    for i,(change,native)in enumerate(zip(details['tensors'],done['parts'])):
        t=tensors[change['name']];prior=old[change['name']]
        require(prior['type']=='Q2_K'and t['type']=='Q2_0'and t['bytes']==native['bytes']==235929600 and t['shape']==prior['shape']==[2560,640,512]and t['payload_sha256']==change['payload_sha256']==native['sha256']and change['parent_payload_sha256']==prior['payload_sha256']and change['part']==i and change['pack_offset']==0,'Native payload binding changed')
    require(all({k:v for k,v in t.items()if k!='offset'}=={k:v for k,v in tensors[t['name']].items()if k!='offset'}for t in parent['tensors']if t['name']not in names),'Unselected payload/type/shape fields changed')
    pkg=types.ModuleType('gguf');pkg.__path__=[str(a.cache/('upstream/llama.cpp-'+LOCK['llama_cpp']['revision'])/'gguf-py/gguf')];sys.modules['gguf']=pkg
    from gguf.constants import GGMLQuantizationType as Type
    pack=prep['parts'][96];require(record(pack['path'])=={k:pack[k]for k in ('path','bytes','sha256')},'Complete host header pack hash differs')
    checked=0
    with Path(pack['path']).open('rb')as stream:
        for h in details['headers']:
            require(h['part']==96,'All headers must use the sole host pack');stream.seek(h['pack_offset']);raw=stream.read(h['bytes']);require(hashlib.sha256(raw).hexdigest()==h['sha256'],'Header slice SHA256 differs');cursor=0
            for name,shape,kind,offset in parse(raw):
                t=tensors[name];require(t['file']==h['file']and t['shape']==shape and t['type']==Type(kind).name and offset==cursor and t['offset']==h['bytes']+offset,'Serialized native tensor descriptor differs');cursor+=t['bytes'];checked+=1
            require(cursor+h['bytes']<=next(f['bytes']for f in parent['files']if f['path']==h['file']),'Complete logical GGUF bound exceeded')
    require(checked==sum(t['file']in{h['file']for h in details['headers']}for t in candidate['tensors']),'Not every compacted tensor was checked')
    write_json(a.out,dict(completed=True,preparation=record(a.preparation),native_generation=prep['native_generation'],
        all_native_output_whole_SHA256_and_EOF_passed=True,all_current_input_whole_SHA256_passed=True,
        all_unselected_tensor_payloads_shapes_and_types_unchanged=True,original_PLE_convolution_preserved=True,
        host_whole_native_payload_readback_claimed=False,header_pack=record(pack['path']),serialized_tensor_descriptors_checked=checked,PS5_operations=0))
    print('Exact native payload proof and all compacted header descriptors pass; large payloads remain on PS5.')

if __name__=='__main__':main()
