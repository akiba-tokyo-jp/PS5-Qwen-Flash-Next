#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Review the finite ten-original-Expert source-to-output comparison."""
import argparse,hashlib,json,re
from pathlib import Path
from build_preservation_integrity import record
from split_bank_result import validate_report as validate_backing,require,integer,finite
from ready_expert_result import validate_ready,validate_stages,exact,POLICY
STRIDE=3293184
def parallel(a,b,files):
    x,y=files[a['source']]['identity'],files[b['source']]['identity']
    def fits(m,f):
        off=m['offset'];return off>=4<<20 and off+STRIDE<=f[5]and off%(1<<30)>=4<<20 and off%(1<<30)+STRIDE<=(1<<30)-(4<<20)
    return fits(a,x)and fits(b,y)and x[0]==y[0]and(x[1]!=y[1]or a['offset']//(1<<30)==b['offset']//(1<<30))
def packets(plan):
    batches=[]
    for group in range(2):
        for role in range(3):
            first=0
            while first<5:
                at=role*10+first*2+group;count=2 if first<4 and parallel(plan['matrices'][at],plan['matrices'][at+2],plan['files'])else 1
                batches.append((group,role,[first*2+group+j*2 for j in range(count)]));first+=count
    return batches
def validate_original(r,plan,plan_sha):
    require(type(r)is dict and r.get('schema')=='ps5-qwen-ready-original-result-v1','Exact original-source result required')
    for k,v in dict(unique_original_experts=10,original_contributions=10,source_IO_depth=2,source_coordinator_workers=1,
        inner_IO_workers=1,Direct_read_calls=180,GPU_graphs=14,initial_positive_graph_epoch=26,final_positive_graph_epoch=40).items():
        require(type(r.get(k))is int and r[k]==v,'Original-source finite count differs: '+k)
    require(r.get('model_source_plan_sha256')==plan_sha and r.get('actual_recorded_Expert_ids')==plan['experts']and len(set(plan['experts']))==10 and
        all(integer(v,0,511)for v in r['actual_recorded_Expert_ids']),'Exact original-source plan/selection required')
    require(r.get('representative_speed_test')is True and r.get('fixture_activation_and_weights_are_deterministic')is True,'Fixed ten-Expert fixture scope required')
    for k in('physical_GPU_timestamp_overlap_qualified','model_speed_qualified','production_adopted'):require(r.get(k)is False,'Fixture cannot qualify model/adoption or hardware overlap')
    require(r.get('reference_absolute_tolerance')==r.get('reference_relative_tolerance')==1e-5,'Original arithmetic limits required')
    cases=r.get('cases');require(type(cases)is list and len(cases)==6,'Complete forward/reverse original-source cohort required')
    expected=packets(plan);pair_count=sum(len(ids)==2 for _,_,ids in expected);require(pair_count>0,'Original source plan has no width-two packet')
    prior=26;last_end=0;output=contributions=None;overlap=[]
    for i,(c,mode)in enumerate(zip(cases,(0,1,2,2,1,0))):
        count=1 if mode==0 else 3
        for k,v in dict(mode=mode,plan_epoch=i+7,prior_completed_GPU_epoch=prior,last_completed_GPU_epoch=prior+count,read_calls=30,GPU_graphs=count).items():
            require(type(c.get(k))is int and c[k]==v,'Original-source phase/epoch differs: '+k)
        prior+=count
        for k in('F64_reference_passed','same_F32_outputs_bit_exact','all_original_envelopes_and_canaries_intact','source_joined','wave_retired'):
            require(c.get(k)is True,'Original arithmetic/ownership invariant failed: '+k)
        require(finite(c.get('maximum_absolute_error'),1e30)and finite(c.get('maximum_normalized_error'),1),'Original F64 arithmetic differs')
        for k in('output_F32_sha256','contribution_F32_sha256'):require(isinstance(c.get(k),str)and re.fullmatch('[0-9a-f]{64}',c[k]),'Complete original F32 identities required')
        if output is None:output,contributions=c['output_F32_sha256'],c['contribution_F32_sha256']
        require((output,contributions)==(c['output_F32_sha256'],c['contribution_F32_sha256']),'Original serial/split output bytes differ')
        owner=c.get('source_owner');require(type(owner)is dict and owner.get('reads')==c.get('reads')and type(owner.get('Direct_read_calls'))is int and
            owner['Direct_read_calls']==30 and type(owner.get('two_call_batches'))is int and owner['two_call_batches']==pair_count and
            type(owner.get('maximum_descriptor_cache'))is int and owner['maximum_descriptor_cache']==8 and integer(owner.get('peak_open_descriptors'),1,8)and
            integer(owner.get('descriptor_opens'),len(plan['files']),30)and type(owner.get('descriptor_closes'))is int and owner['descriptor_opens']==owner['descriptor_closes']and
            owner.get('inner_reader_joined')is True and owner.get('all_descriptors_closed')is True and owner.get('model_source_plan_sha256')==plan_sha and
            owner.get('CPU_only_source_fixture')is False and type(owner.get('source_IO_depth'))is int and owner['source_IO_depth']==2,
            'Original source lacks exact two-call/LRU/close evidence')
        reads=c['reads'];require(type(reads)is list and len(reads)==30,'All thirty original roles required');j=0;previous_batch_end=last_end
        group_end=[0,0]
        for batch,(group,role,ordinals)in enumerate(expected,1):
            end=previous_batch_end
            for ordinal in ordinals:
                read=reads[j];m=plan['matrices'][role*10+ordinal]
                for k,v in dict(id=j+1,ordinal=ordinal,group=group,role=role,source=m['source'],offset=m['offset'],bytes=STRIDE,batch=batch,batch_calls=len(ordinals)).items():
                    require(type(read.get(k))is int and read[k]==v,'Original source byte/slot/batch differs: '+k)
                require(read.get('original_raw_sha256')==m['raw']and read.get('original_envelope_sha256')==m['envelope'],'Original source hash differs')
                require(integer(read.get('begin_ns'),previous_batch_end,2**63-1)and integer(read.get('end_ns'),read['begin_ns']+1,2**63-1),'Original returned read interval differs')
                end=max(end,read['end_ns']);j+=1
            previous_batch_end=end;group_end[group]=end
        submits=c.get('submissions');require(type(submits)is list and len(submits)==count,'All original graph completions required')
        submit_end=last_end
        for n,(s,phase)in enumerate(zip(submits,(0,)if mode==0 else(1,2,3))):
            require(type(s.get('phase'))is int and s['phase']==phase and type(s.get('epoch'))is int and s['epoch']==c['prior_completed_GPU_epoch']+n+1 and
                s.get('positive_synchronized_driver_completion')is True,'Original graph phase/epoch is incomplete')
            require(integer(s.get('begin_ns'),submit_end,2**63-1)and integer(s.get('end_ns'),s['begin_ns']+1,2**63-1),'Original graph intervals differ');submit_end=s['end_ns']
        require(submits[0]['begin_ns']>=group_end[0 if mode==2 else 1],'Original graph started before its complete source group')
        if mode!=0:require(submits[1]['begin_ns']>=max(group_end[1],submits[0]['end_ns']),'Second graph began before source/first graph completion')
        active=sum(max(0,min(read['end_ns'],submits[0]['end_ns'])-max(read['begin_ns'],submits[0]['begin_ns']))for read in reads if read['group']==1)
        if mode!=2:require(active==0,'Serial original-source control overlapped reads and graph API')
        else:overlap.append(active>0)
        last_end=max(previous_batch_end,submit_end)
        require(integer(c.get('source_to_output_ns'),last_end-reads[0]['begin_ns'],120_000_000_000),'Original duration omits source or graph work')
    a0,b0,c0,c1,b1,a1=[c['source_to_output_ns']for c in cases]
    gains=[a0/c0-1,a1/c1-1];spread=max(abs(a1/a0-1),abs(c1/c0-1))
    winner=all(v>spread for v in gains)and all(overlap)
    decision='fixture_winner_requires_model_validation'if winner else'fixture_loser'if all(v < -spread for v in gains)else'inconclusive'
    return dict(native_original_scope_passed=True,comparison_decision=decision,forward_reverse_gains=gains,observed_two_arm_spread=spread,
        source_GPU_API_overlap_in_both_candidate_cases=all(overlap),source_calls_per_run=30,source_payload_bytes_per_run=98304000,
        two_call_batches_per_run=pair_count,split_serial_to_one_graph_ratios=[b0/a0,b1/a1],
        may_integrate_model_for_separate_qualification=winner,physical_GPU_timestamp_overlap_qualified=False,
        model_speed_qualified=False,production_adopted=False,ordinary_OS_close_and_restore_review_required=True)
def validate_original_stages(text,original,plan):
    lines=text.splitlines();expected=[];phases=[]
    for case in original['cases']:
        reads=case['reads'];at=0
        for batch,(group,role,ordinals)in enumerate(packets(plan),1):
            events=''.join(str(reads[at+j]['id'])+':'+str(reads[at+j]['offset'])+':'+str(STRIDE)+','for j in range(len(ordinals)))
            expected.append('ready_original_batch_before plan='+str(case['plan_epoch'])+' operation='+str(batch)+' group='+str(group)+' role='+str(role)+' calls='+str(len(ordinals))+' events='+events);at+=len(ordinals)
        phases += ['ready_original_dispatch_before plan='+str(case['plan_epoch'])+' phase='+str(s['phase'])+' epoch='+str(s['epoch'])for s in case['submissions']]
    require([l for l in lines if l.startswith('ready_original_batch_before ')]==expected and
        lines.count('ready_original_batch_all_calls_and_byte_proofs_returned')==len(expected),'Original durable batch plans/returned calls differ')
    require([l for l in lines if l.startswith('ready_original_dispatch_before ')]==phases,'Original durable graph epochs differ')
def validate_app_namespace(proof,policy,plan):
    require(type(policy)is dict and set(policy)=={'schema','canonical_root','directory_identity','receipt_identity','allow_app0_device_translation'} and
        policy['schema']=='ps5-qwen-ready-original-app-namespace-v1' and policy['allow_app0_device_translation']is True,'Exact application namespace policy required')
    root=policy['canonical_root'];require(type(root)is str and root.startswith('/data/')and len(root)<1024 and not root.endswith('/')and
        '..'not in root and '\0'not in root and '\\'not in root,'Sealed canonical model root required')
    require(type(proof)is dict and len(proof)==8 and proof.get('schema')==policy['schema']and
        proof.get('all_nine_non_device_fields_exact')is True and proof.get('original_receipt_SHA256_checked')is True and
        proof.get('all_part_bytes_still_checked_before_GPU')is True,'Complete original namespace evidence required')
    source=proof.get('canonical_source_device');app=proof.get('application_device')
    require(integer(source,1,2**64-1)and integer(app,1,2**64-1),'Exact source/application device pair required')
    for key,kind in (('directory_identity',0o040000),('receipt_identity',0o100000)):
        expected=policy[key];actual=proof.get(key)
        require(type(expected)is list and type(actual)is list and len(expected)==len(actual)==10 and
            all(integer(v,0,2**64-1)for v in expected+actual)and expected[0]==source and actual[0]==app and expected[1:]==actual[1:]and
            expected[1]>0 and expected[5]>0 and expected[2]&0o170000==kind and not expected[2]&0o022,'Namespace anchor fields differ')
    require(all(f['path'].startswith(root+'/')and len(f['path'])>len(root)+1 and f['identity'][0]==source for f in plan['files']),
        'Original part lies outside the canonical namespace')

def validate_combined(report,policy,plan,sha,text,pid):
    expected=dict(schema='ps5-qwen-ready-original-policy-v1',enabled=True,same_title_numerical_gate_required=True,unique_original_experts=10,source_IO_depth=2,cohort_runs=6,source_plan_sha256=sha)
    require(exact(policy.get('native_ready_expert_original'),expected)and exact(policy.get('native_ready_expert_numerical'),POLICY),'Exact original/numerical policies required')
    if 'native_ready_expert_original_namespace'in policy:
        validate_app_namespace(report.get('original_source_namespace'),policy['native_ready_expert_original_namespace'],plan)
        require(text.splitlines().count('ready_original_app_namespace_bound_before_GPU')==1,'Single pre-GPU namespace binding required')
    validate_backing(report,policy['native_isolated_split_bank_title'],pid,ready_numerical=True,original_source=True,scoped_memory='native_split_bank_phase_memory'in policy);validate_ready(report['ready_numerical'])
    if 'native_split_bank_phase_memory'in policy:
        expected_memory=dict(schema='ps5-qwen-split-bank-phase-memory-v1',enabled=True,GPU_extra_operational_pages=1024,model_loads=0,
            regular_model_startup_target_unchanged=True,operational_floor_unchanged=True)
        require(exact(policy['native_split_bank_phase_memory'],expected_memory)and report.get('scoped_GPU_phase_memory')is True and
            type(report.get('scoped_GPU_required_free_pages'))is int and report['scoped_GPU_required_free_pages']==2178 and
            integer(report.get('kernel_free_after_CPU_source_before_GPU'),2178,1000000),'Exact scoped fixture GPU memory admission required')
    result=validate_original(report.get('ready_original'),plan,sha)
    numerical_end=max(s['end_ns']for c in report['ready_numerical']['cases']for s in c['submissions'])
    require(report['ready_original']['cases'][0]['reads'][0]['begin_ns']>=numerical_end,'Original source started before the complete numerical prerequisite')
    validate_stages(text,report['ready_numerical'],additional_ready_cases=6);validate_original_stages(text,report['ready_original'],plan)
    lines=text.splitlines();last_numerical=max(i for i,l in enumerate(lines)if l.startswith('ready_numerical_dispatch_before '))
    returned=next(i for i in range(last_numerical+1,len(lines))if lines[i]=='ready_expert_graph_synchronized_driver_completion_returned')
    require(next(i for i,l in enumerate(lines)if l.startswith('ready_original_batch_before '))>returned,'Durable journal does not place original reads after the numerical gate')
    return result
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in('report','policy','plan','stages','out'):p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--expected-pid',type=int,required=True);a=p.parse_args();paths=[a.report,a.policy,a.plan,a.stages];inputs=[record(p)for p in paths]
    report,policy,plan=[json.loads(p.read_bytes())for p in paths[:3]];sha=inputs[2]['sha256']
    result=validate_combined(report,policy,plan,sha,a.stages.read_text(),a.expected_pid)
    require(inputs==[record(p)for p in paths],'Original cohort review inputs changed')
    with a.out.open('x',encoding='utf-8')as f:json.dump(dict(schema='ps5-qwen-ready-original-review-v1',inputs=inputs,**result),f,indent=2);f.write('\n')
    print(json.dumps(result),flush=True)
if __name__=='__main__':main()
