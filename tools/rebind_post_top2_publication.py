#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Bind identical model bytes at a fresh runtime directory without recompilation."""
import argparse,json
from pathlib import Path,PurePosixPath
from active_native_inputs import active_link_inputs
from expert_q4 import require,record,write_json
from scoped_native_variant import seal

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('native','publication','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();n=json.loads(a.native.read_text());old_record=n['precision_candidate']['publication_plan']
    require(record(old_record['path'])==old_record,'Old publication plan changed')
    old=json.loads(Path(old_record['path']).read_text());pub=json.loads(a.publication.read_text())
    require(pub['completed']and pub['Direct_positively_retired']and pub['GPU_calls']==0,'Complete positively retired native publication required')
    new_record=pub['base_build'];require(record(new_record['path'])==new_record,'Actual publication build changed')
    new=json.loads(Path(new_record['path']).read_text())
    source_seal=pub['source_integrity'];require(record(source_seal['path'])==source_seal,'Published source integrity changed')
    require(old['candidate_receipt']==new['candidate_receipt']==pub['candidate']and old['parent_receipt']==new['parent_receipt'],
        'Data-only binding requires identical complete candidate and parent receipts')
    def payloads(m):
        return sorted((PurePosixPath(x['destination']).name,x['local']['bytes'],x['local']['sha256'])for x in m['files'])
    require(payloads(old)==payloads(new)and old['part_count']==new['part_count']and old['header_count']==new['header_count'],
        'Every file name, complete SHA256 and extent must be identical')
    for r in active_link_inputs(n):require(record(r['path'])==r,'Actual compiled provider changed')
    artifact=Path(n['artifact']['path']);require(record(artifact)==n['artifact'],'Actual native image changed')
    raw=artifact.read_bytes()
    require(old['app0_directory'].encode()not in raw and old['new_directory'].encode()not in raw,
        'An embedded old publication directory requires an actual application rebuild')
    a.out.mkdir(parents=True,exist_ok=False)
    n['precision_candidate']['publication_plan']=new_record
    n['post_top2_publication_binding']=dict(implementation=record(__file__),source_native=record(a.native),
        previous_publication_plan=old_record,actual_publication=record(a.publication),actual_publication_plan=new_record,
        source_integrity=source_seal,all_model_bytes_identical=True,actual_native_image_unchanged=True,
        no_old_target_directory_embedded=True,runtime_directory_and_source_identities_native_verified=True,
        recompilations=0,PS5_operations=0,CI_runs=0)
    n['inputs_before'] +=[record(__file__),record(a.native),record(a.publication),new_record,source_seal]
    seal(n,a.workspace,a.cache,a.out)
    write_json(a.out/'core-safety.private.json',dict(completed=True,kind='identical_weight_bytes_fresh_runtime_binding',
        candidate=record(a.out/'receipt.private.json'),actual_native_image_unchanged=True,
        model_receipt_SHA256=pub['candidate']['sha256'],PS5_operations=0,CI_runs=0))

if __name__=='__main__':main()
