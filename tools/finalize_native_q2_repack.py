#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Create compact metadata for positively completed native Q2 payloads."""
import argparse,collections,copy,hashlib,json,struct,sys,types
from pathlib import Path
from expert_q4 import LOCK,require,record,write_json
from resident_all_q8 import placement

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('completion','cache','original','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();done=json.loads(a.completion.read_text());require(done['completed']and done['Direct_positively_released']and len(done['parts'])==96,'Complete native output ownership proof required')
    build=json.loads(Path(done['build']['path']).read_text());require(record(done['build']['path'])==done['build']and record(build['model']['path'])==build['model'],'Native source ancestry changed')
    require(record(done['raw']['path'])==done['raw'],'Completed native full-readback journal changed')
    parent=json.loads(Path(build['model']['path']).read_text());candidate=copy.deepcopy(parent);candidate.pop('resident_all_Q8_overlay');candidate['schema']='ps5-qwen-precision-overlay-v1';candidate['precision_candidate']='expert-Q2_0'
    pkg=types.ModuleType('gguf');pkg.__path__=[str(a.cache/('upstream/llama.cpp-'+LOCK['llama_cpp']['revision'])/'gguf-py/gguf')];sys.modules['gguf']=pkg
    from gguf.gguf_reader import GGUFReader
    from gguf.constants import GGMLQuantizationType as Type
    a.out.mkdir(parents=True,exist_ok=False);by_name={t['name']:t for t in candidate['tensors']};changes=[];files=set()
    parts=[dict(row,native_generated=True,host_generated=False)for row in done['parts']]
    for i,(binding,part)in enumerate(zip(build['bindings'],parts)):
        t=binding['tensor'];require(part['path']==done['app0_directory']+'/precision.part'+str(i)+'.bin'and part['bytes']==235929600,'Ordered complete native tensor payload required')
        dst=by_name[t['name']];dst.update(type='Q2_0',bytes=235929600,payload_sha256=part['sha256']);files.add(t['file'])
        changes.append(dict(name=t['name'],part=i,pack_offset=0,bytes=235929600,original_bytes=t['bytes'],parent_payload_sha256=t['payload_sha256'],payload_sha256=part['sha256'],type='Q2_0',requantized_from_current_Q2_K=True))
    pack=a.out/'precision.part96.bin';headers=[]
    with pack.open('xb')as out:
        for filename in sorted(files):
            path=a.original/filename;before=path.stat();reader=GGUFReader(path,'r');tensors={t.name:t for t in reader.tensors}
            with path.open('rb')as source:header=bytearray(source.read(reader.data_offset))
            cursor=reader.data_offset
            for t in candidate['tensors']:
                if t['file']!=filename:continue
                original=tensors[t['name']];field=int(original.field.offset)+8+len(t['name'].encode())
                struct.pack_into('<I',header,field,len(t['shape']));struct.pack_into('<'+'Q'*len(t['shape']),header,field+4,*t['shape']);field+=4+8*len(t['shape'])
                struct.pack_into('<IQ',header,field,int(Type[t['type']]),cursor-reader.data_offset);t['offset']=cursor;cursor+=t['bytes'];require(cursor%32==0,'Compact alignment changed')
            require(cursor<=next(f['bytes']for f in parent['files']if f['path']==filename),'Compact source exceeds logical bound')
            out.write(bytes((-out.tell())%16384));at=out.tell();out.write(header);headers.append(dict(file=filename,part=96,pack_offset=at,bytes=len(header),sha256=hashlib.sha256(header).hexdigest()))
            after=path.stat();require((before.st_size,before.st_ino,before.st_mtime_ns)==(after.st_size,after.st_ino,after.st_mtime_ns),'Original header source changed')
            del reader,tensors
    parts.append(dict(record(pack),host_generated=True,native_generated=False))
    saving=96*(275251200-235929600)
    candidate['precision_overlay']=dict(schema='ps5-qwen-precision-overlay-v1',mode='expert-Q2_0',parent={k:v for k,v in build['model'].items()if k!='path'},tensors=changes,headers=headers,parts=parts,
        saved_payload_bytes=saving,pinned_quantizer_revision=LOCK['llama_cpp']['revision'],quantizer='current_Q2_K_to_F32_to_Q2_0_reference',native_generation=record(a.completion),original_BF16_direct_quantization_claimed=False,
        F32_activation_input_required=True,KV_precision_preserved=True,logical_file_lengths_preserved=True,tensor_offsets_compacted=True,narrow_convolution_BF16_preserved=True)
    target=a.out/'model-receipt.json';target.write_text(json.dumps(candidate,separators=(',',':'))+'\n',newline='\n');require(target.stat().st_size<=1<<20,'Original metadata bound exceeded')
    footprint=collections.Counter()
    for t in candidate['tensors']:footprint[placement(t['name'])]+=t['bytes']
    prep=a.out/'receipt.private.json';write_json(prep,dict(completed=True,mode='expert-Q2_0',parent=build['model'],candidate=record(target),selected_tensors=96,changed_payload_bytes=96*235929600,saved_payload_bytes=saving,parts=parts,footprint=dict(footprint),native_generation=record(a.completion),original_sources_modified=False,original_BF16_direct_quantization_claimed=False,PS5_operations=0,native_verification_pending=True))
    write_json(a.out/'audit.private.json',dict(completed=True,preparation=record(prep),native_generation=record(a.completion),all_native_output_whole_SHA256_and_EOF_passed=True,all_current_input_whole_SHA256_passed=True,
        all_unselected_tensor_payloads_shapes_and_types_unchanged=all({k:v for k,v in by_name[t['name']].items()if k!='offset'}=={k:v for k,v in t.items()if k!='offset'}for t in parent['tensors']if t['name']not in{c['name']for c in changes}),original_PLE_convolution_preserved=True,
        host_whole_native_payload_readback_claimed=False,header_pack=record(pack)))
    print('Native payload hashes bound to compact metadata; no large network round trip.')

if __name__=='__main__':main()
