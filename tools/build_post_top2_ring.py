#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compare four leases with a five-lease no-copy ring on the actual source owner."""
import argparse,json
from pathlib import Path
from build_cache_capacity_1125 import literal
from build_next_five_comparison import update_sources
from build_speculative_batch_probe import once
from expert_q4 import record,require,write_json
from qualify_post_top2_reporting import transform as reporting
from ring_stream_source import transform
from scoped_native_variant import link,seal
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('parent','proof','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();n=json.loads(a.parent.read_text());proof=json.loads(a.proof.read_text())
    require(proof['completed']and proof['cases']==8 and proof['maximum_simultaneous_reads']==4,'Positive ownership and error-drain proof required')
    old=n['GDN_model_comparison']['scope'];require(old['candidate']=='Q4-cache3712-Top2','Actual Top2/Q4 provider required')
    a.out.mkdir(parents=True,exist_ok=False);header=a.out/'speed-streaming.private.h';header.write_text(transform(),newline='\n')
    require(record(header)['sha256']==proof['owned_source']['sha256'],'Tested ring bytes required')
    scope=dict(old,schema='ps5-qwen-post-top2-ring-v1',candidate='five-lease-no-copy-ring',candidate_id=1,
        control_Experts=2,candidate_Experts=2,CPU_workers=4,maximum_simultaneous_reads=4,control_leases=4,candidate_leases=5,
        extra_owned_CPU_bytes_in_both_arms=2097152,extra_copy_bytes=0,read_alignment=16384,positive_completion_preserved=True)
    ec=n['compile_commands'][0];oc=n['all_Q2_optimized_monitor']['commands'][1]
    entry=Path(ec[ec.index('-c')+1]).read_text();owner=Path(oc[oc.index('-c')+1]).read_text()
    require('#include "speed-streaming.private.h"'in owner,'Actual streaming owner include required')
    actual_header=Path('D:/PS5-AI/qwen-flash-next/build/Speed-confirmation-12380/speed-streaming.private.h')
    require(actual_header.read_bytes()==(ROOT/'native/app/streaming_read_pool.h').read_bytes(),'Selected compiled streaming implementation must equal the tested baseline')
    entry='extern "C" void qwen_post_ring_select(bool);\n'+entry
    entry=once(entry,literal(old),literal(scope));entry=once(entry,'qwen_next_select(arm?2:0);','qwen_next_select(2);qwen_post_ring_select(arm==1);')
    entry=once(entry,'arm==0?"Q4-cache3712-Top6":"Q4-cache3712-Top2";','arm==0?"Top2-four-lease":"Top2-five-lease-no-copy";')
    for before,after in [('compare&&arm==0&&rows!=io_rows[hash_arm]','compare&&rows!=io_rows[hash_arm]'),
        ('compare&&arm==0&&(io_max_error!=0||bitwise_error)','compare&&(io_max_error!=0||bitwise_error)'),
        ('else if(arm==0&&(result.token_ids!=speed_ids[hash_arm][task]||result.output_bytes!=speed_bytes[hash_arm][task]))','else if(result.token_ids!=speed_ids[hash_arm][task]||result.output_bytes!=speed_bytes[hash_arm][task])'),
        ('if(compare&&arm==0&&!same_routes)','if(compare&&!same_routes)')]:entry=once(entry,before,after)
    entry=reporting(entry)
    owner='namespace {bool post_ring_selected=false;}\nextern "C" void qwen_post_ring_select(bool v){post_ring_selected=v;}\nextern "C" bool qwen_post_ring_enabled(){return post_ring_selected;}\n'+owner
    oldheader=Path(oc[oc.index('-c')+1]).parent/'limit-winner-bundle.private.h';bundle=a.out/oldheader.name;bundle.write_bytes(oldheader.read_bytes())
    r,jobs,sources=link(a.parent,a.out,dict(entry=(ec,entry),owner=(oc,owner)),[Path(__file__),a.proof,header,bundle,actual_header,ROOT/'tools/ring_stream_source.py',ROOT/'tools/qualify_post_top2_reporting.py'])
    update_sources(r,jobs,sources);r['GDN_model_comparison']['scope']=scope
    r['next_five_comparison'].update(scope=scope,actual_sources=sources,commands=jobs,production_adopted=False)
    r['post_top2_ring']=dict(scope=scope,actual_sources=sources,commands=jobs,header=record(header),ownership_proof=record(a.proof))
    seal(r,a.workspace,a.cache,a.out)
    write_json(a.out/'core-safety.private.json',dict(completed=True,kind='five_lease_zero_copy_ring',scope=scope,candidate=record(a.out/'receipt.private.json'),original_GPU_and_weights_unchanged=True,PS5_operations=0,CI_runs=0))

if __name__=='__main__':main()
