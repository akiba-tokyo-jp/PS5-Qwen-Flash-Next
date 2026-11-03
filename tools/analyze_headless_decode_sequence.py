#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compare complete headless ABBA rates without replaying native computation."""
import argparse
import json
import math
from pathlib import Path
import statistics
from build_performance_quantizer import record
from start_success_route import load,need,save


def exact(row):
    need(record(row['path'])==row,'Completed sequence evidence changed');return load(row['path'])


def compare(values):
    need(len(values)==4 and all(math.isfinite(x) and x>0 for x in values),'Four positive finite measurements required')
    A=[values[0],values[3]];B=[values[1],values[2]]
    spread=abs(A[1]-A[0]);gains=[b-a for a,b in zip(A,B)]
    return dict(control=A,candidate=B,control_mean=statistics.mean(A),candidate_mean=statistics.mean(B),
        rate_change_percent=100*(statistics.mean(B)/statistics.mean(A)-1),control_AA_spread=spread,
        paired_gains=gains,both_paired_gains_exceed_control_spread=min(gains)>spread,
        both_paired_regressions_exceed_control_spread=min(-x for x in gains)>spread)


def compare_time(values):
    need(len(values)==4 and all(math.isfinite(x) and x>=0 for x in values),'Four finite nonnegative native times required')
    A=[values[0],values[3]];B=[values[1],values[2]];control=statistics.mean(A);candidate=statistics.mean(B)
    spread=abs(A[1]-A[0]);savings=[a-b for a,b in zip(A,B)]
    return dict(control=A,candidate=B,control_mean=control,candidate_mean=candidate,control_AA_spread=spread,
        paired_savings_ms=savings,mean_time_reduction_percent=100*(1-candidate/control) if control else None,
        both_paired_time_savings_exceed_control_spread=min(savings)>spread,
        both_paired_time_regressions_exceed_control_spread=min(-x for x in savings)>spread)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--sequence',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();sequence=load(a.sequence)
    need(sequence['completed'] and sequence['order']==[0,1,1,0] and len(sequence['cases'])==4 and
        sequence['all_ordinary_closes_and_exact_restores'],'One positively closed complete headless ABBA required')
    terminals=[];roots=[];profiles=[];evidence=[record(a.sequence),sequence['numerical_proof']]
    proof=exact(sequence['numerical_proof']);need(proof['completed'],'Completed separate numerical qualification required')
    for row in sequence['cases']:
        terminal=exact(row['terminal']);closed=exact(row['closure']);plan=exact(row['plan']);package=exact(row['package'])
        need(terminal['completed'] and terminal['timings_usable_for_performance'] and len(terminal['requests'])==3 and
            terminal['all_model_source_device_owners_positively_retired'] and terminal['device_ledger_live_bytes']==0 and
            closed['ordinary_exit_observed'] and closed['current_seven_restored_and_native_hashed'] and not closed['unknown_completion'] and
            plan['package']==row['package'] and terminal['candidate_SELF_sha256']==package['SELF']['sha256'],
            'Actual exact SELF, three returned requests and positive ordinary restoration required')
        root=Path(row['root'])/'case';need(b'F32_row request=' not in (root/'native-stages.private.log').read_bytes(),
            'Qualification-only whole-vocabulary SHA may not enter the timing cohort')
        profiles.append(exact(package['effective_application_policy']['profile']))
        roots.append(root);terminals.append(terminal);evidence.extend((row['terminal'],row['closure'],row['plan'],row['package']))
    groups=[]
    ordinary_S1=sequence['scope']=='S1' and all(p['headless_audit_kind'] in
        ('S1-persistent-MTP-online','S1-ordinary-target-control') for p in profiles)
    cross_feature=ordinary_S1 and proof.get('scope')=='S1-ordinary-vs-retained'
    if cross_feature:
        need([p['headless_audit_kind'] for p in profiles]==['S1-ordinary-target-control','S1-persistent-MTP-online',
            'S1-persistent-MTP-online','S1-ordinary-target-control'] and proof['tokens_and_output_bytes_exact'] and
            proof['compact_retained_causal_and_lifetime_qualified'],'Explicit qualified feature comparison required')
    for index in range(3):
        requests=[t['requests'][index] for t in terminals];reference=requests[0];rates=[];routes=[]
        for root,r in zip(roots,requests):
            need(r['counting_quality_passed'] and r['full_F32_finite'] and r['request_reset_completed'] and
                r['token_ledger_closed_before_request_result'],'Every actual finite/counting/reset and durable completion must pass')
            m=r['metrics'];rate=(m['generated_tokens']-1)*1000/m['decode_ms']
            need(m['generated_tokens']>=2 and abs(rate-m['decode_tokens_per_second'])<=1e-9,'Original decode tok/s formula changed')
            rates.append(rate)
            path=root/'headless-observer'/('native.arm'+str(index)+'.routes.private.json');trace=load(path)
            need(trace['complete'] and not trace['capture_failed'] and trace['all_existing_downloads_and_synchronizations_returned'] and
                trace['sidecar_written_after_model_and_source_retirement'],'Complete actual ordered route capture required')
            routes.append(trace['records']);evidence.append(record(path))
        tokens=all(r['token_ids']==reference['token_ids'] and r['output_bytes']==reference['output_bytes'] for r in requests)
        ordered=all(r==routes[0] for r in routes)
        if cross_feature:
            need(tokens and routes[0]==routes[3] and routes[1]==routes[2],
                'Target outputs must agree and each feature must reproduce its own ordered routes')
            for arm,actual in ((0,routes[0]),(1,routes[1])):
                expected=exact(proof['route_evidence_by_feature'][arm][index])
                need(actual==expected['records'],'Each timed feature must match its numerical route qualification')
        else:need(tokens and ordered,'Timed target tokens, output bytes and ordered routes must agree')
        keys=('source_bytes','source_physical_read_bytes','source_physical_read_calls')
        source_equal=all(len({r['completed_performance']['delta'][k] for r in requests})==1 for k in keys)
        labels=('ordinary-cold','ordinary-retained-1','ordinary-retained-2') if ordinary_S1 else ('cold','retained','exact-prefix')
        spans={}
        for name in ('prefill_ms','TTFT_ms','total_ms'):
            spans[name]=compare_time([r['metrics'][name] for r in requests])
        spans['complete_request_span_ms']=compare_time([r['complete_request_span_ms'] for r in requests])
        groups.append(dict(condition=labels[index],native_arm=reference['arm'],tokens_and_output_bytes_exact=tokens,
            ordered_routes_exact=ordered,original_source_demand_equal=source_equal,
            qualified_cross_feature_computation=cross_feature,route_record_counts=[len(x) for x in routes],
            decode_tokens_per_second=compare(rates),additional_time_metrics=spans))
    lifecycle=None
    if sequence['scope']=='S1':
        audits=[t['audit'] for t in terminals]
        def span(t):
            audit=t['audit']
            if 'complete_sequence_including_final_auxiliary_retirement_ms' in audit:
                need(audit['all_auxiliary_owners_positively_retired'],'Final auxiliary retirement must be positively complete')
                return audit['complete_sequence_including_final_auxiliary_retirement_ms']
            return audit['complete_request_sequence_ms']
        clocks=[span(t) for t in terminals];whole=compare_time(clocks)
        lifecycle=dict(complete_three_request_span_ms=whole,
            auxiliary_context_creations=[x.get('auxiliary_context_creations',0) for x in audits],
            auxiliary_KV_clears=[x.get('auxiliary_KV_clears',0) for x in audits],
            retained_auxiliary=[x.get('retained_auxiliary',False) for x in audits],
            auxiliary_setup_and_final_retirement_included=True,exact_prefix_tested=False)
        if all(p['headless_audit_kind']=='S1-persistent-MTP-online' for p in profiles):
            need(lifecycle['auxiliary_context_creations']==[3,1,1,3] and lifecycle['auxiliary_KV_clears']==[3,3,3,3] and
                lifecycle['retained_auxiliary']==[False,True,True,False],'The actual native fresh/retained lifetime arms must execute')
    elif sequence['scope']=='P1':
        need([p['overrides']['native_P1_headless_arm'] for p in profiles]==[0,1,1,0],'Actual bounded P1 control/candidate sequence required')
    elif sequence['scope']=='G1':
        need([p['G1_arm'] for p in profiles]==['control','candidate','candidate','control'],'Actual linked fused sort arms required')
    elif sequence['scope']=='I1':
        from model_relative_prefetch_evidence import review
        need([p['I1_arm'] for p in profiles]==['control','candidate','candidate','control'],
             'Actual bounded source-prefetch arms required')
        lifecycle=dict(actual_source_prefetch=[review(t,enabled) for t,enabled in
            zip(terminals,(False,True,True,False))],
            complete_request_including_relative_setup_and_drain_ms=[compare_time([
                t['requests'][index]['complete_request_including_relative_setup_and_drain_ms']
                for t in terminals]) for index in range(3)])
    result=dict(completed=True,scope=sequence['scope'],primary_metric='(generated_tokens-1)/decode_seconds',
        groups=groups,auxiliary_lifecycle=lifecycle,all_twelve_requests_positively_completed=True,
        separate_numerical_proof=sequence['numerical_proof'],qualification_SHA_observer_excluded=True,
        all_ordinary_closes_and_exact_restores=True,production_adopted=False,PS5_operations=0,evidence=evidence)
    save(a.out,result)
    print(json.dumps(dict(completed=True,scope=sequence['scope'],groups=[dict(condition=g['condition'],
        **g['decode_tokens_per_second']) for g in groups],auxiliary_lifecycle=lifecycle,PS5_operations=0)))


if __name__=='__main__':main()
