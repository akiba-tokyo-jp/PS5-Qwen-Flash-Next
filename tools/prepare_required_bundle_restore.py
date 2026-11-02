#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Recover exact live bundle descriptions from the retained selected owner.

This prepares lossless copying of existing Q2 bytes. It does not quantize,
infer, modify a retained object, or access the console.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess

from build_performance_quantizer import record
from driver_table_storage import sections
from start_success_route import load,need,save
from success_case_control import PHYSICAL

KINDS={'bundle':336,'extra':84,'current':1024}


def prepare(current,metadata,workspace,kind,out):
    current=Path(current);metadata=Path(metadata);out=Path(out);out.mkdir(parents=True,exist_ok=False)
    retained=load(current/'provenance/retained-relink-inputs.private.json')
    owners=[r for r in retained if Path(r['original_path']).name=='owner.o'];need(len(owners)==1,'One actual retained owner required')
    owner=owners[0];need(record(owner['path'])=={k:owner[k] for k in ('path','bytes','sha256')},'Selected owner changed')
    raw=Path(owner['path']).read_bytes();table=sections(raw)
    def data(symbol):
        matches=[s for s in table if s['name']=='.rodata.'+symbol];need(len(matches)==1,'One original constant section required: '+symbol)
        return matches[0]['data']
    source_plan=load(current/'provenance/model-source-plan.private.json')
    sources={r['path']:r for r in source_plan['physical']+source_plan['backing']}
    need(len(sources)==518,'Exact selected 518 source identities required')
    mixed_path=metadata/'model-receipt.json';seal_path=metadata/'retained-mixed-proof.json'
    for path in (mixed_path,seal_path):
        checked=record(path);need(any(r['bytes']==checked['bytes'] and r['sha256']==checked['sha256'] for r in source_plan['backing']),
                                  'Captured original backing certificate differs')
    mixed=load(mixed_path);seal=load(seal_path)
    tensors={t['name']:t for t in mixed['tensors']};files={f['path']:f for f in mixed['files']}
    logical={f['path']:f for f in seal['logical_files']}
    count=KINDS[kind];prefix='Q2_'+kind
    pools=[s['data'] for s in table if s['name']=='.rodata.str1.1']
    need(len(pools)==1,'One exact original string pool required')
    strings=pools[0].split(b'\0')
    positions=[i for i,value in enumerate(strings) if re.fullmatch(rb'/app0/qwen-Q2-bundle-probe-[0-9a-f]{32}\.bin',value)]
    need(len(positions)==3,'Three original ordered source paths required')
    ordinal=list(KINDS).index(kind);position=positions[ordinal];path=strings[position].decode()
    suffix=Path(path).stem.removeprefix('qwen-Q2-bundle-probe-')
    scope=load(current/'qwen-runtime/development.json')['native_next_five_normal']
    if kind=='current':sha=scope['prior_sealed_pack_SHA256']
    else:
        digests=[value.decode() for value in strings[position+1:positions[ordinal+1]] if re.fullmatch(rb'[0-9a-f]{64}',value)]
        need(len(digests)==1,'One original whole digest adjacent to its exact source path required');sha=digests[0]
    previous=list(struct.unpack('<10Q',data(prefix+'_expected_identity')))
    need(previous[2:5]==[0o100444,0,0] and previous[5]==((count*1540096+65535)//65536)*65536,'Exact immutable pack geometry required')
    keys=list(struct.iter_unpack('<II',data(prefix+'_keys')))
    need(len(keys)==count and keys==sorted(set(keys)) and all(l<48 and e<512 for l,e in keys),'Original sorted unique keys required')
    physical=list(range(count))
    if kind=='current':
        physical=list(struct.unpack('<'+'I'*count,data(prefix+'_physical')))
        need(sorted(physical)==list(range(count)),'Original physical permutation required')
        need(re.fullmatch('[0-9a-f]{64}',sha) and scope['prior_sealed_pack_bytes']==previous[5],'Original current-pack seal binding required')
    else:need(sha.encode()+b'\0' in raw,'Original complete pack digest must remain compiled in the actual owner')
    need(path.encode()+b'\0' in raw,'Exact original compiled path required')
    ordered=[None]*count
    for key,index in zip(keys,physical):ordered[index]=key
    selected_sources=[];spans=[];experts=[]
    def source_index(path):
        row=sources[path]
        if row not in selected_sources:selected_sources.append(row)
        return selected_sources.index(row)
    for layer,expert in ordered:
        first=len(spans)
        for role,size,destination in (('gate',537600,0),('up',537600,537600),('down',460800,1075200)):
            if role=='down':
                matches=[p for p in sources if Path(p).name=='down-'+str(layer)+'.q2_0'];need(len(matches)==1,'One sealed original Down source required')
                part=matches[0];need(sources[part]['bytes']==512*size,'Whole original Down tensor required')
                spans.append(dict(source=source_index(part),offset=expert*size,bytes=size,destination=destination));continue
            tensor=tensors['blk.'+str(layer)+'.ffn_'+role+'_exps.weight']
            need(tensor['type']=='Q2_K' and tensor['bytes']==size*512,'Original Q2_K tensor geometry required')
            start=tensor['offset']+expert*size;file=files[tensor['file']]
            regions=[r for r in file['regions'] if r['logical_offset']<=start and start+size<=r['logical_offset']+r['bytes']]
            need(len(regions)==1 and regions[0]['storage']=='new','Already encoded retained Q2 bytes required')
            region=regions[0];at=region['storage_offset']+start-region['logical_offset'];left=size
            for part in logical[tensor['file']]['parts']:
                if not left:break
                if not part['offset']<=at<part['offset']+part['bytes']:continue
                take=min(left,part['offset']+part['bytes']-at)
                need(sources[part['path']]['identity']==part['identity'],'Exact retained packed source identity required')
                spans.append(dict(source=source_index(part['path']),offset=at-part['offset'],bytes=take,destination=destination+size-left))
                at+=take;left-=take
            need(left==0,'Complete quantized role bytes required')
        need(sum(r['bytes'] for r in spans[first:])==1536000,'All three unchanged roles required')
        experts.append(dict(layer=layer,expert=expert,first_span=first,spans=len(spans)-first))
    # The existing successful native CPU packer consumes this exact format.
    header='#pragma once\n#include <array>\n#include <cstdint>\n#define BUNDLE_PROBE_COUNT '+str(count)+'\n'
    header+='#define BUNDLE_PROBE_NONCE '+json.dumps(suffix)+'\n'
    header+='inline constexpr const char*bundle_probe_parent='+json.dumps(PHYSICAL)+';\n'
    header+='inline constexpr const char*bundle_probe_path='+json.dumps(PHYSICAL+path[5:])+';\n'
    header+='inline constexpr uint64_t bundle_probe_file_bytes='+str(previous[5])+'ULL;\n'
    header+='struct BundleProbeSource{const char*path;std::array<uint64_t,10>identity;};\ninline constexpr BundleProbeSource bundle_probe_sources[]={\n'
    for row in selected_sources:
        header+='{'+json.dumps(PHYSICAL+row['path'][5:])+',{'+','.join(str(v)+'ULL' for v in row['identity'])+'}},\n'
    header+='};\nstruct BundleProbeSpan{unsigned source;uint64_t offset,bytes,destination;};\ninline constexpr BundleProbeSpan bundle_probe_spans[]={\n'
    header+=''.join('{'+','.join(str(r[k])+'ULL' for k in ('source','offset','bytes','destination'))+'},\n' for r in spans)+'};\n'
    header+='struct BundleProbeExpert{unsigned layer,expert,first_span,spans;};\ninline constexpr BundleProbeExpert bundle_probe_experts[]={\n'
    header+=''.join('{'+','.join(str(r[k]) for k in ('layer','expert','first_span','spans'))+'},\n' for r in experts)+'};\n'
    header_path=out/'expert_q2_bundle_probe_plan.h';header_path.write_text(header,encoding='utf-8',newline='\n')
    llvm=Path(workspace)/'toolchain/llvm-mingw-20261006-ucrt-x86_64/bin'
    relocs=subprocess.check_output([str(llvm/'llvm-readobj.exe'),'--relocs',owner['path']],text=True)
    need(len(re.findall(r'R_X86_64_REX_GOTPCRELX '+prefix+'_expected_identity ',relocs))==1,
         'The actual owner must refer symbolically to the identity provider')
    plan=dict(completed=True,kind=kind,owner=owner,old_identity=previous,expected_SHA256=sha,output=PHYSICAL+path[5:],
        output_bytes=previous[5],identity_provider_symbol=prefix+'_expected_identity',sources=selected_sources,spans=spans,
        experts=experts,header=record(header_path),source_plan=record(current/'provenance/model-source-plan.private.json'),
        metadata=[record(mixed_path),record(seal_path)],quantization_changes=0,source_writes=0,PS5_operations=0,
        original_key_order_and_physical_permutation_preserved=True,required_startup_input_not_a_discardable_trial=True)
    save(out/'plan.private.json',plan)
    return plan


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('current','metadata','workspace','out'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--kind',choices=KINDS,required=True);args=parser.parse_args()
    plan=prepare(args.current,args.metadata,args.workspace,args.kind,args.out)
    print(json.dumps(dict(prepared=True,kind=plan['kind'],Experts=len(plan['experts']),bytes=plan['output_bytes'],
                          exact_old_whole_digest_bound=True,quantization_changes=0,PS5_operations=0)))


if __name__=='__main__':main()
