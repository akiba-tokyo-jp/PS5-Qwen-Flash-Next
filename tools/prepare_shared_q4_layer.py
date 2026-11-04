#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compose a new shared-Q4 layer while preserving the current 109-matrix layer."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

from build_performance_quantizer import record
from start_success_route import load,need,save


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('delta','audit','out'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();delta=load(args.delta);audit=load(args.audit)
    need(audit['completed'] and audit['input']==record(args.delta) and audit['all_pack_extents_hashes_and_padding_pass'],
         'The independent complete Q1 layout audit is required')
    need(record(delta['control']['path'])==delta['control'] and record(delta['pack']['path'])==delta['pack'],
         'Authenticated current recipe and Q1 payload required')
    current=load(delta['control']['path']);candidate=load(args.delta.parent/'candidate-model.private.json')
    need(len(current['precision_overlay']['tensors'])==109 and len(delta['tensors'])==144,'The exact 109 plus 144 layers required')
    need(candidate['precision_overlay']==current['precision_overlay'],'Current precision layer changed')
    before={t['name']:t for t in current['tensors']};after={t['name']:t for t in candidate['tensors']}
    changed={t['name'] for t in delta['tensors']}
    need(len(changed)==144 and not changed.intersection(t['name'] for t in current['precision_overlay']['tensors']),
         'The additional and retained tensor sets must be disjoint')
    for name,row in after.items():
        if name not in changed:
            need({k:v for k,v in row.items() if k!='offset'}=={k:v for k,v in before[name].items() if k!='offset'},
                 'Unselected tensor payload, shape or precision changed')
    args.out.mkdir(parents=True,exist_ok=False);headers=[]
    replacements={h['file']:h for h in delta['headers']}
    for old in current['precision_overlay']['headers']:
        if old['file'] in replacements:
            value=replacements.pop(old['file']);need(record(value['path'])=={k:value[k] for k in ('path','bytes','sha256')},'Q1 prefix changed')
            raw=Path(value['path']).read_bytes()
        else:
            # The output matrix remains the already selected Q4 payload and
            # prefix; copying its small prefix does not copy its weight pack.
            part=current['precision_overlay']['parts'][old['part']]
            with Path(part['path']).open('rb') as stream:stream.seek(old['pack_offset']);raw=stream.read(old['bytes'])
            need(len(raw)==old['bytes'] and hashlib.sha256(raw).hexdigest()==old['sha256'],'Retained current prefix differs')
        path=args.out/old['file'];path.write_bytes(raw);headers.append(dict(file=old['file'],**record(path)))
    for name,value in sorted(replacements.items()):
        need(record(value['path'])=={k:value[k] for k in ('path','bytes','sha256')},'Additional Q1 prefix changed')
        path=args.out/name;shutil.copyfile(value['path'],path);headers.append(dict(file=name,**record(path)))
    need(len(headers)==51 and len({h['file'] for h in headers})==51,'The complete union of current and Q1 prefixes required')
    pack=args.out/'shared-q4.bin';shutil.copyfile(delta['pack']['path'],pack)
    need(record(pack)['sha256']==delta['pack']['sha256'],'Copied Q1 payload changed')
    changes=[{k:t[k] for k in ('name','file','shape','type','bytes','pack_offset','payload_sha256',
        'control_type','control_bytes','control_payload_sha256','original_BF16_payload_sha256')} for t in delta['tensors']]
    candidate['shared_Q4_overlay']=dict(schema='ps5-qwen-additional-shared-Q4-layer-v1',
        parent={k:delta['control'][k] for k in ('bytes','sha256')},tensors=changes,
        headers=[{k:h[k] for k in ('file','bytes','sha256')} for h in headers],
        pack={k:record(pack)[k] for k in ('bytes','sha256')},saved_payload_bytes=117964800,
        original_109_matrix_precision_layer_unchanged=True,encoded_directly_from_original_BF16=True)
    path=args.out/'model-receipt.json';path.write_text(json.dumps(candidate,separators=(',',':')),encoding='utf-8',newline='\n')
    need(path.stat().st_size<=1<<20,'The complete additional receipt exceeds the existing bound')
    report=dict(completed=True,parent=delta['control'],candidate=record(path),pack=record(pack),headers=headers,
        delta=record(args.delta),audit=record(args.audit),selected_tensors=144,total_Q4_matrices=253,
        prior_precision_layer_unchanged=True,old_weight_packs_copied=0,
        new_source_files=53,new_payload_bytes=record(pack)['bytes'],saved_device_weight_bytes=117964800,
        complete_virtual_file_lengths_unchanged=all(a['bytes']==b['bytes'] for a,b in zip(candidate['files'],current['files'])),
        native_source_publication_pending=True,native_quality_or_speed_measured=False,PS5_operations=0,production_adopted=False)
    save(args.out/'result.private.json',report)
    print(json.dumps({k:v for k,v in report.items() if k not in ('parent','candidate','pack','headers','delta','audit')}))


if __name__=='__main__':main()
