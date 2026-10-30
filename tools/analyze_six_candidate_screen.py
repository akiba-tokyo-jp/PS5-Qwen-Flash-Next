#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Analyze completed interleaved physical comparisons without rerunning them."""
import argparse,json,statistics
from pathlib import Path
from expert_q4 import require,record,write_json
from analyze_expert_routing_sharing import quality,whole_request,decode_interval,aggregate
from build_six_candidate_screen import ORDER

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('case','out'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();load=lambda p:json.loads(Path(p).read_text());root=a.case
    terminal=load(root/'native-model-terminal.private.json');closed=load(root/'restored-complete.private.json')
    require(terminal['completed']and terminal['all_model_source_device_owners_positively_retired']and terminal['device_ledger_live_bytes']==0,'Positive native retirement required')
    require(closed['completed']and closed['CPU_title_normally_closed']and closed['exact_prior_configuration_restored']and not closed['unknown_completion'],'Normal close and exact restoration required')
    require([r['mode']for r in terminal['requests']]==ORDER,'Declared physical order differs')
    requests=terminal['requests'];qualities=[];measured={};proofs=[]
    for mode in range(5):
        rows=[]
        for request in requests:
            if request['mode']!=mode:continue
            require(request['request_reset_completed']and request['full_F32_finite'],'Finite logits and complete reset required')
            route_path=root/f"native-arm{request['ordinal']}.routes.private.json";route=load(route_path);proofs.append(record(route_path))
            require(route['complete']and route['cache_reset_before_request'],'Actual cold route proof required')
            if request['counting']and request['ordinal']:
                points=[load(root/'IO-token-snapshots'/f"arm{request['ordinal']}-token-{i}.private.json")for i in range(1,request['metrics']['generated_tokens']+1)]
                row=decode_interval(request,points);row['whole_request']=whole_request(request);rows.append(row)
            elif not request['counting']:
                text=bytes(request['output_bytes']).decode('utf-8','strict')
                qualities.append(dict(mode=mode,task=request['quality_task'],output=text,**quality(request['quality_task'],text)))
            width=request['prefill_policy']['width'];require(width==16,'Actual width16 required')
            expected=8 if mode==1 else 6 if mode==2 else 10
            prefill_rows=request['prefill_policy']['calls']*48
            require(all(r['experts']==(expected if i<prefill_rows else 6)for i,r in enumerate(route['records'])),
                    'Actual prefill/decode Expert cardinality differs')
            if mode==4:require(request['actual_graph_reuses']>0,'The graph-reuse candidate must actually reuse graphs')
            else:require(request['actual_graph_reuses']==0,'Graph reuse escaped its scoped candidate')
        summary=aggregate(rows);timed=[r for r in requests if r['counting']and r['ordinal']and r['mode']==mode]
        summary.update(TTFT_ms_mean=statistics.mean(r['metrics']['TTFT_ms']for r in timed),
            total_ms_mean=statistics.mean(r['metrics']['total_ms']for r in timed),
            maximum_F32_difference=max(r['maximum_absolute_logit_error']for r in timed),
            actual_reuses=[r['actual_graph_reuses']for r in timed],
            quality_contents=sum(q['answer_content_passed']for q in qualities if q['mode']==mode),
            quality_strict=sum(q['strict_format_passed']for q in qualities if q['mode']==mode))
        measured[str(mode)]=summary
    decisions=[]
    for mode,A,B in ((1,[1,4],[2,3]),(2,[5,8],[6,7]),(3,[9,12],[10,11]),(4,[13,16],[14,15])):
        mean=lambda indices,key:statistics.mean(requests[i]['metrics'][key]for i in indices)
        total_reduction=1-mean(B,'total_ms')/mean(A,'total_ms')
        decode_ratio=mean(B,'decode_tokens_per_second')/mean(A,'decode_tokens_per_second')
        separated=max(requests[i]['metrics']['total_ms']for i in B)<min(requests[i]['metrics']['total_ms']for i in A)
        decisions.append(dict(mode=mode,controls=A,candidates=B,TTFT_reduction_fraction=1-mean(B,'TTFT_ms')/mean(A,'TTFT_ms'),
            whole_time_reduction_fraction=total_reduction,decode_speedup_fraction=decode_ratio-1,
            both_candidate_whole_times_below_both_controls=separated,
            eligible_for_normal_integration=separated and total_reduction>0 and measured[str(mode)]['quality_contents']==3,
            decline_in_decode_disclosed=decode_ratio<1))
    require(measured['0']['maximum_F32_difference']==0 and measured['4']['maximum_F32_difference']==0,'Exact unchanged and graph-reuse controls required')
    write_json(a.out,dict(completed=True,requests=32,model_loads=1,measured_modes=measured,decisions=decisions,
        fixed_quality=qualities,route_proofs=proofs,source=record(root/'native-model-terminal.private.json'),
        restoration=record(root/'restored-complete.private.json'),production_adopted=False,PS5_operations=0,CI_runs=0))
    print(json.dumps(dict(completed=True,decisions=decisions,measured_modes=measured),indent=2))
if __name__=='__main__':main()
