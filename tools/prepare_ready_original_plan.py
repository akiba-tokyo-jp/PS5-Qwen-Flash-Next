#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Bind ten actual selected Experts to existing sealed model-part byte ranges.

Only selected original envelopes are read. No repacking, conversion, model
arithmetic, source mutation, console operation or new weight corpus is used.
"""
import argparse,hashlib,json,os
from pathlib import Path
from build_preservation_integrity import record
from expert_route_result import validate_routes
from model_transport import writer_lease
EXPERT=3276800;STRIDE=3293184;ALIGN=16384
def prepare(layout,headers,routes,receipt,root,host,layer=0):
    if not(layout['all_original_logical_SHA256_matched']and layout['all_physical_part_SHA256_matched']and
        not layout['pending_operations']and layout['part_bytes']==512<<20 and receipt['outtype']=='bf16'and
        receipt['original_shards_verified']and receipt['original_revision']=='de4b8e4d43b917e7706784d8bb445c9af86a3540'):
        raise ValueError('Pinned original-precision sealed source required')
    logical={f['path']:f for f in layout['logical_files']};original={f['path']:f for f in receipt['files']}
    tensors={t['name']:(h['file'],t)for h in headers for t in h['tensors']}
    selected=None
    for index,row in enumerate(routes['records']):
        if row['tokens']!=1 or row['layer']!=layer or len(row['ids'])!=10 or len(set(row['ids']))!=10:continue
        ranges=[];valid=True
        for role in('gate','up','down'):
            name,t=tensors[f'blk.{layer}.ffn_{role}_exps.weight'];f=logical[name]
            if t['type']!=30 or t['bytes']!=512*EXPERT or original[name]['sha256']!=f['sha256'] or original[name]['bytes']!=f['bytes']:
                raise ValueError('Original BF16 tensor/receipt differs from sealed lineage')
            for expert in row['ids']:
                offset=t['file_offset']+expert*EXPERT;aligned=offset&~(ALIGN-1)
                matches=[p for p in f['parts']if p['offset']<=aligned and aligned+STRIDE<=p['offset']+p['bytes']]
                if len(matches)!=1:valid=False;break
                ranges.append((name,aligned,offset-aligned,matches[0]))
            if not valid:break
        if valid:selected=(index,row['ids'],ranges);break
    if selected is None:raise ValueError('No complete ten-Expert one-part-envelope decode record for the selected layer')
    index,experts,ranges=selected;files=[];sources={};matrices=[];opened={};identities={}
    try:
        for name,aligned,residue,part in ranges:
            path=host/name
            if name not in opened:
                f=path.open('rb');opened[name]=f;identities[name]=os.fstat(f.fileno())
                if identities[name].st_size!=logical[name]['bytes']:raise ValueError('Retained original logical source size changed')
            f=opened[name];f.seek(aligned);data=f.read(STRIDE)
            if len(data)!=STRIDE:raise ValueError('Original selected envelope did not return every byte')
            if part['path']not in sources:
                sources[part['path']]=len(files);files.append(dict(path=root.rstrip('/')+'/'+part['path'],bytes=part['bytes'],identity=part['identity'],sha256=part['sha256']))
            matrices.append(dict(source=sources[part['path']],offset=aligned-part['offset'],residue=residue,
                raw=hashlib.sha256(data[residue:residue+EXPERT]).hexdigest(),envelope=hashlib.sha256(data).hexdigest()))
        for name,f in opened.items():
            before=identities[name];after=os.fstat(f.fileno())
            if (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns)!=(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns):
                raise ValueError('Retained original source changed while reading selected ranges')
    finally:
        for f in opened.values():f.close()
    return dict(schema='ps5-qwen-ready-original-plan-v1',layer=layer,experts=experts,slots=[48+i//2 if i%2 else i//2 for i in range(10)],
        files=files,matrices=matrices,lineage=dict(original_revision=receipt['original_revision'],original_receipt_sha256=layout['original_receipt_sha256'],
            original_BF16_preserved=True),origin=dict(native_route_record=index,actual_recorded_selection=True,
            fixture_activation_and_weights_are_deterministic=True,model_hidden_state_not_captured=True))
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in('cache','routes','result','layout','headers','migration-plan','host-models','out'):p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--layer',type=int,default=0);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    receipt_path=a.host_models/'model-receipt.json'
    paths=[Path(__file__),a.routes,a.result,a.layout,a.headers,a.migration_plan,receipt_path]
    inputs=[record(p)for p in paths];load=lambda p:json.loads(p.read_bytes())
    routes=load(a.routes);terminal=load(a.result)
    validate_routes(routes,terminal,width=4,pid=terminal['pid'],run_id=terminal['run_id'],cold=routes['cache_reset_before_request'])
    with writer_lease(a.cache/'model-data-continuation.writer.lock'):
        plan=prepare(load(a.layout),load(a.headers),routes,load(receipt_path),load(a.migration_plan)['model_root'],a.host_models,a.layer)
        plan['lineage']['native_layout_seal_sha256']=inputs[3]['sha256'];plan['lineage']['headers_sha256']=inputs[4]['sha256'];plan['origin']['native_routes_sha256']=inputs[1]['sha256']
        raw=(json.dumps(plan,separators=(',',':'))+'\n').encode();assert len(raw)<=65536
        target=a.out/'plan.private.json';target.write_bytes(raw)
        assert inputs==[record(p)for p in paths]
        result=dict(schema='ps5-qwen-ready-original-plan-preparation-v1',inputs=inputs,plan=record(target),
            selected_original_envelopes=30,original_payload_bytes=30*EXPERT,physical_bytes_read=30*STRIDE,
            ten_unique_Experts=True,no_new_weight_corpus=True,host_model_arithmetic=False,PS5_operations=0,CI_runs=0)
        (a.out/'receipt.private.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items()if k not in('inputs','plan')}),flush=True)
if __name__=='__main__':main()
