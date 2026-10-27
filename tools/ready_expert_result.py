#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Review the numerical ready-expert cohort; never infer a model-speed winner."""
import argparse,json,re
from pathlib import Path
from build_preservation_integrity import record
from split_bank_result import validate_report as validate_backing,require,integer,finite,HASHES
POLICY=dict(schema='ps5-qwen-ready-numerical-policy-v1',enabled=True,unique_original_experts=2,
    original_contributions=10,cohort_runs=6,source_IO_depth=1,representative_speed_test=False)
def exact(a,b):return type(a)is type(b)and(a==b if not isinstance(a,dict)else a.keys()==b.keys()and all(exact(a[k],b[k])for k in a))
def sha(s):return isinstance(s,str)and re.fullmatch('[0-9a-f]{64}',s)is not None
def validate_ready(r):
    require(type(r)is dict and r.get('schema')=='ps5-qwen-ready-numerical-result-v1','Exact ready numerical report required')
    for k,v in dict(unique_original_experts=2,original_contributions=10,source_IO_depth=1,source_coordinator_workers=1,
        Direct_read_calls=36,GPU_graphs=14,initial_positive_graph_epoch=12,final_positive_graph_epoch=26).items():
        require(type(r.get(k))is int and r[k]==v,'Ready finite count differs: '+k)
    for k in('representative_speed_test','physical_GPU_timestamp_overlap_qualified','model_speed_qualified','production_adopted'):
        require(r.get(k)is False,'A repeated-ID numerical gate cannot qualify speed/adoption: '+k)
    require(r.get('reference_absolute_tolerance')==r.get('reference_relative_tolerance')==1e-5,'Original numerical limits required')
    cases=r.get('cases');require(type(cases)is list and len(cases)==6,'All six serial/split/reverse controls required')
    prior=12;last_end=0;output=contributions=None
    offsets=((4210688,7503872,10797056),(14090240,17383424,20676608))
    for index,(case,mode)in enumerate(zip(cases,(0,1,2,2,1,0))):
        require(type(case)is dict,'Ready numerical case required');count=1 if mode==0 else 3
        for k,v in dict(mode=mode,plan_epoch=index+1,prior_completed_GPU_epoch=prior,last_completed_GPU_epoch=prior+count,read_calls=6,GPU_graphs=count).items():
            require(type(case.get(k))is int and case[k]==v,'Ready numerical ordering/count differs: '+k)
        prior+=count
        require(integer(case.get('source_to_output_ns'),1,60_000_000_000),'Finite source-to-output duration required')
        for k in('F64_reference_passed','same_F32_outputs_bit_exact','all_original_envelopes_and_canaries_intact','source_joined','wave_retired'):
            require(case.get(k)is True,'Ready numerical/source/retirement invariant failed: '+k)
        require(finite(case.get('maximum_absolute_error'),1e30)and finite(case.get('maximum_normalized_error'),1),'Ready F64 error invalid')
        require(sha(case.get('output_F32_sha256'))and sha(case.get('contribution_F32_sha256')),'Output and all original contribution identities required')
        if output is None:output,contributions=case['output_F32_sha256'],case['contribution_F32_sha256']
        require(case['output_F32_sha256']==output and case['contribution_F32_sha256']==contributions,'Serial/split F32 bytes differ')
        reads=case.get('reads');submissions=case.get('submissions')
        require(type(reads)is list and len(reads)==6 and type(submissions)is list and len(submissions)==count,'Complete returned read/dispatch intervals required')
        read_end=last_end
        for j,read in enumerate(reads):
            require(type(read)is dict,'Ready read interval object required')
            group,role=divmod(j,3);raw,envelope=HASHES[role*2+group]
            for k,v in dict(group=group,role=role,offset=offsets[group][role],bytes=3293184).items():
                require(type(read.get(k))is int and read[k]==v,'Ready original source interval differs: '+k)
            require(read.get('original_raw_sha256')==raw and read.get('original_envelope_sha256')==envelope,'Ready source hashes differ')
            require(integer(read.get('begin_ns'),read_end,2**63-1)and integer(read.get('end_ns'),read['begin_ns']+1,2**63-1),'Ready read interval reordered')
            read_end=read['end_ns']
        submit_end=last_end
        for j,(submission,phase)in enumerate(zip(submissions,(0,)if mode==0 else(1,2,3))):
            require(type(submission)is dict and type(submission.get('phase'))is int and submission['phase']==phase and
                type(submission.get('epoch'))is int and submission['epoch']==case['prior_completed_GPU_epoch']+j+1 and
                submission.get('positive_synchronized_driver_completion')is True,'Ready positive dispatch phase/epoch differs')
            require(integer(submission.get('begin_ns'),submit_end,2**63-1)and integer(submission.get('end_ns'),submission['begin_ns']+1,2**63-1),'Ready dispatch interval reordered')
            submit_end=submission['end_ns']
        require(submissions[0]['begin_ns']>=reads[2 if mode==2 else 5]['end_ns'],'GPU started before its complete source group')
        if mode!=0:require(submissions[1]['begin_ns']>=max(read_end,submissions[0]['end_ns']),'Second GPU group started before source/previous completion')
        if mode!=2:require(read_end<=submissions[0]['begin_ns'],'A serial control overlapped source with graph dispatch')
        require(case['source_to_output_ns']>=max(read_end,submit_end)-reads[0]['begin_ns'],'Reported duration omits returned source/graph work')
        # Releasing the second group precedes the graph API call by design.
        # Do not require or infer hardware overlap from host API intervals.
        last_end=max(read_end,submit_end)
    return dict(native_numerical_scope_passed=True,cohort_runs=6,additional_GPU_graphs=14,unique_original_experts=2,
        representative_ten_unique_expert_test_required=True,physical_GPU_timestamp_overlap_qualified=False,
        full_model_integration_qualified=False,model_speed_qualified=False,production_adopted=False)
def validate_stages(text,ready):
    require(type(text)is str and 0<len(text.encode())<=8<<20,'Bounded complete native stage journal required')
    lines=text.splitlines()
    require(lines[-1]=='split_bank_validation_completed_waiting_for_ordinary_close','Positive final native phase required')
    for phase,count in dict(split_bank_graph_before_submission=12,split_bank_graph_positive_idle_and_epoch_returned=12,
        ready_numerical_Direct_read_returned=36,ready_expert_before_complete_serial_graph=2,ready_expert_before_first_group_graph=4,
        ready_expert_before_second_group_graph=4,ready_expert_before_original_reduction_graph=4,
        ready_expert_graph_synchronized_driver_completion_returned=14).items():
        require(lines.count(phase)==count,'Finite native stage count differs: '+phase)
    reads=[line for line in lines if line.startswith('ready_numerical_read_before ')]
    dispatch=[line for line in lines if line.startswith('ready_numerical_dispatch_before ')]
    require(reads==['ready_numerical_read_before plan='+str(c['plan_epoch'])+' group='+str(r['group'])+' role='+str(r['role'])+
        ' offset='+str(r['offset'])+' bytes='+str(r['bytes'])for c in ready['cases']for r in c['reads']], 'Durable original read plans differ from native results')
    require(dispatch==['ready_numerical_dispatch_before plan='+str(c['plan_epoch'])+' phase='+str(s['phase'])+' epoch='+str(s['epoch'])
        for c in ready['cases']for s in c['submissions']],'Durable native graph epochs/plans differ from native results')
def validate_report(report,policy,expected_pid):
    require(exact(policy.get('native_ready_expert_numerical'),POLICY),'Exact predeclared numerical policy required')
    validate_backing(report,policy['native_isolated_split_bank_title'],expected_pid,ready_numerical=True)
    result=validate_ready(report.get('ready_numerical'));result['ordinary_OS_close_and_restore_review_required']=True;return result
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in('report','policy','stages','out'):p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--expected-pid',type=int,required=True);a=p.parse_args();inputs=[record(a.report),record(a.policy),record(a.stages)]
    report=json.loads(a.report.read_bytes());result=validate_report(report,json.loads(a.policy.read_bytes()),a.expected_pid)
    validate_stages(a.stages.read_text(),report['ready_numerical'])
    require(inputs==[record(a.report),record(a.policy),record(a.stages)],'Frozen ready report/policy/stages changed')
    with a.out.open('x',encoding='utf-8')as f:json.dump(dict(schema='ps5-qwen-ready-numerical-review-v1',inputs=inputs,**result),f,indent=2);f.write('\n')
    print(json.dumps(result),flush=True)
if __name__=='__main__':main()
