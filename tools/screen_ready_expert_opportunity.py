#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Screen an unchanged-packet, serial-pair ready-wave opportunity from saved routes."""
import argparse,json,os,subprocess
from pathlib import Path
from check_model_checkpoint import record
from check_cache_capacity import bound
from expert_route_result import validate_routes
from replay_expert_routes import RouteCache
ROOT=Path(__file__).resolve().parents[1]
EXPERT_BYTES=3276800

def original_packets(fills):
    """Follow the maintained cache loop, including its next-two consumption."""
    result=[];i=0
    while i<len(fills):
        n=1
        while i+n<len(fills) and fills[i+n][0]==fills[i][0]+n and fills[i+n][1]==fills[i][1]+n:n+=1
        if n>1:result.append(('scatter',fills[i:i+n]));i+=n
        else:
            count=min(2,len(fills)-i);result.append(('owned',fills[i:i+count]));i+=count
    return result

def parallel_extent(offset,size,identity):
    within=offset%(1<<30)
    return bool(identity[0] and identity[1] and size and offset<identity[5] and size<=identity[5]-offset and
        within>=4<<20 and within<=(1<<30)-(4<<20) and size<=(1<<30)-(4<<20)-within)

def independent_predicate(packet,files):
    spans=[];direct=True
    for index,offset in packet:
        size=files[index][5];fits=offset<=size and EXPERT_BYTES<=size-offset
        aligned=offset&~16383 if fits else 0
        n=(offset-aligned+EXPERT_BYTES+16383)&~16383 if fits else 0
        direct&=fits and n<=size-aligned
        spans.append((index,aligned,n))
    adjacent=len(packet)==2 and packet[0][0]==packet[1][0] and packet[1][1]-packet[0][1]==EXPERT_BYTES
    direct&=not adjacent;parallel=False
    if direct and len(packet)==2:
        a,b=spans;first,second=files[a[0]],files[b[0]]
        parallel=(parallel_extent(a[1],a[2],first) and parallel_extent(b[1],b[2],second) and first[0]==second[0] and
            (first[1]!=second[1] or a[1]//(1<<30)==b[1]//(1<<30)))
    return [bool(direct),bool(parallel),sum(s[2]for s in spans),bool(adjacent)]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in('workspace','cache','manifest','geometry-receipt','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    headers=a.cache/'performance-layout-screen-1374/headers.private.json'
    seal=a.cache/'split512-layout-seal-1640/native-integrity.private.json'
    files=[Path(__file__),a.manifest,a.geometry_receipt,headers,seal,ROOT/'tests/ready_source_schedule.cpp',
        ROOT/'native/app/source_read_schedule.h',ROOT/'native/app/padded_bank.h',ROOT/'tools/replay_expert_routes.py',
        ROOT/'patches/native-model-io/0002-llama-moe-cache.patch',ROOT/'native/app/mapped_source.h']
    geometry=json.loads(a.geometry_receipt.read_text())
    if geometry.get('native_buffer_or_GPU_qualification')is not False or geometry.get('native_metadata_bytes')!=432:
        raise ValueError('Exact unqualified split-bank metadata receipt required')
    manifest=json.loads(a.manifest.read_text());layout=json.loads(seal.read_text())
    if manifest.get('schema')!='ps5-qwen-capacity-replay-inputs-v1' or len(manifest.get('requests',[]))!=3:
        raise ValueError('Three bound original requests required')
    if layout['part_bytes']!=512<<20 or layout['pending_operations'] or not layout['all_original_logical_SHA256_matched']:
        raise ValueError('Complete original-precision 512 MiB layout seal required')
    logical={f['path']:f for f in layout['logical_files']};identities=[];parts={};tensors={}
    for name,f in logical.items():
        parts[name]=[]
        for part in f['parts']:
            if part['bytes']!=part['identity'][5]:raise ValueError('Physical part size differs')
            index=len(identities);identities.append(part['identity']);parts[name].append((part['offset'],part['offset']+part['bytes'],index))
    for h in json.loads(headers.read_text()):
        for t in h['tensors']:
            if t['name'].endswith(('.ffn_gate_exps.weight','.ffn_up_exps.weight','.ffn_down_exps.weight')):
                if t['type']!=30 or t['bytes']!=512*EXPERT_BYTES:raise ValueError('Original BF16 expert geometry differs')
                tensors[t['name']]=(h['file'],t['file_offset'])
    queries=[];lookup={};requests=[];candidate_examples=[];cache=None
    for ordinal,item in enumerate(manifest['requests']):
        rp=bound(item['routes']);tp=bound(item['result']);files.extend((rp,tp))
        trace=json.loads(rp.read_text());terminal=json.loads(tp.read_text())
        validate_routes(trace,terminal,width=4,pid=terminal['pid'],run_id=terminal['run_id'],cold=ordinal<2)
        if ordinal<2:cache=RouteCache()
        totals=dict(hits=0,misses=0,unique=0);rows=[]
        for route in trace['records']:
            before=set(cache.mapping);step=cache.step(route)
            for key in totals:totals[key]+=step[key]
            if route['tokens']!=1:continue
            layer=route['layer'];selected=set(route['ids']);selected_groups={int(cache.mapping[layer*512+e]>=26)for e in selected}
            fills=[(e,cache.mapping[layer*512+e])for e in sorted(selected)if layer*512+e not in before]
            packets=original_packets(fills);physical=[]
            for role in('gate','up','down'):
                name,base=tensors[f'blk.{layer}.ffn_{role}_exps.weight']
                for kind,entries in packets:
                    if kind=='scatter':physical.append(dict(kind=kind,entries=entries,role=role));continue
                    query=[]
                    for expert,slot in entries:
                        offset=base+expert*EXPERT_BYTES
                        matches=[(start,index)for start,end,index in parts[name]if start<=offset<end]
                        if len(matches)!=1:raise ValueError('Expert origin must resolve to one sealed part')
                        start,index=matches[0];query.append([index,offset-start])
                    key=tuple(tuple(x)for x in query)
                    if key not in lookup:lookup[key]=len(queries);queries.append(query)
                    physical.append(dict(kind=kind,entries=entries,query=lookup[key],role=role))
            rows.append(dict(layer=layer,selected_groups=sorted(selected_groups),packets=physical))
        if totals!=dict(hits=trace['cache_hits'],misses=trace['cache_misses'],unique=trace['unique_selected_experts']):
            raise ValueError('Replay differs from completed native counters')
        requests.append(dict(ordinal=ordinal,rows=rows))
    data=a.out/'packets.private.json';data.write_text(json.dumps(dict(files=identities,packets=queries),separators=(',',':'))+'\n');files.append(data)
    fixed=[record(f)for f in files];host=a.workspace/'toolchain/msys-clang64/clang64/bin'
    up=a.cache/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569';exe=a.out/'schedule.exe'
    commands=[[str(host/'clang++.exe'),'-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'native/app'),
        '-I',str(up/'vendor'),str(ROOT/'tests/ready_source_schedule.cpp'),'-o',str(exe)],[str(exe),str(data)]]
    env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''))
    for i,c in enumerate(commands):
        r=subprocess.run(c,capture_output=True,timeout=120,env=env);(a.out/f'{i}.private.log').write_bytes(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace')[-2000:])
    actual=json.loads(r.stdout)
    if actual!=[independent_predicate(q,identities)for q in queries]:raise ValueError('Actual native predicates differ from independent replay')
    summaries=[]
    for request in requests:
        total=dict(ordinal=request['ordinal'],decode_layer_steps=len(request['rows']),both_selected_groups=0,
            scatter_packets=0,direct_single_packets=0,direct_parallel_pairs=0,direct_serial_pairs=0,staged_packets=0,
            cross_group_direct_pairs=0,eligible_steps=0,eligible_serial_packets=0)
        for row in request['rows']:
            both=row['selected_groups']==[0,1];total['both_selected_groups']+=both;eligible=[]
            for packet in row['packets']:
                if packet['kind']=='scatter':total['scatter_packets']+=1;continue
                direct,parallel,_,_=actual[packet['query']];entries=packet['entries']
                if not direct:total['staged_packets']+=1
                elif len(entries)==1:total['direct_single_packets']+=1
                else:
                    total['direct_parallel_pairs'if parallel else'direct_serial_pairs']+=1
                    total['cross_group_direct_pairs']+=int(entries[0][1]>=26)!=int(entries[1][1]>=26)
                    # After all OTHER original packets return, read zero is synchronous;
                    # consume zero may compute the opposite group while read one runs.
                    if both and not parallel:eligible.append(packet)
            if eligible:
                total['eligible_steps']+=1;total['eligible_serial_packets']+=len(eligible)
                if row['layer']in(0,23,47) and len(candidate_examples)<12:
                    candidate_examples.append(dict(ordinal=request['ordinal'],layer=row['layer'],last_packet=eligible[0]))
        total['eligible_step_fraction']=total['eligible_steps']/total['decode_layer_steps']
        summaries.append(total)
    assert fixed==[record(f)for f in files]
    result=dict(schema='ps5-qwen-ready-expert-opportunity-v1',requests=summaries,unique_physical_queries=len(queries),
        original_native_route_counters_exact=True,actual_Cpp_source_predicates_match_Python=True,
        whole_original_packets_preserved=True,additional_payload_bytes=0,additional_source_read_calls=0,
        requires_new_independent_backing_and_graph_qualification=True,current_shared_backing_eligible=False,
        actual_overlap_or_speed_measured=False,PS5_operations=0,model_arithmetic=False,CI_runs=0)
    (a.out/'examples.private.json').write_text(json.dumps(candidate_examples,indent=2)+'\n')
    (a.out/'receipt.private.json').write_text(json.dumps(dict(result,inputs=fixed,commands=commands),indent=2)+'\n')
    print(json.dumps(result),flush=True)
if __name__=='__main__':main()
