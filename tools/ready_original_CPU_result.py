#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Review real original-source CPU delivery; never qualify GPU/model speed."""
import json,re
from ready_original_result import packets,STRIDE
from split_bank_result import require,integer
WIDTHS=(1,2,2,1,1,2,2,1)
def validate(text,plan,sha,nonce):
    lines=text.splitlines();ends=[l for l in lines if l.startswith('END ')]
    require(len(ends)==1 and 'success=1 'in ends[0]and 'nonce='+nonce+' 'in ends[0]and
        'all_workers_joined=1 Direct_released=1 pending_reads=0 GPU_calls=0 title_launches=0 no_retry=1'in ends[0],
        'CPU source lacks positive completion and returned Direct backing')
    require(not any(l.startswith(('RETAIN','CPU_SOURCE_REFUSAL'))for l in lines),'CPU source refused or retained an unknown owner')
    for marker in('DIRECT_UNMAP_RETURNED rc=0','DIRECT_RELEASE_RETURNED rc=0',
        'CPU_READS_RETURNED_AND_JOINED result=1 both_scratch_boundary_canaries=1'):
        require(lines.count(marker)==1,'Missing CPU lifetime/canary proof: '+marker)
    contexts=[l for l in lines if l.startswith('context ')]
    require(len(contexts)==3 and all('exact=1'in l and'canaries=1'in l for l in contexts),'Three exact native context guards required')
    for phase in(1,2,3):
        owners=[l for l in lines if l.startswith('process phase='+str(phase)+' ')]
        require(len(owners)==8 and all('exact=1'in l and'canaries=1'in l for l in owners),'Eight exact native owners required in every context phase')
    cases=[json.loads(l[len('CPU_CASE_RESULT '):])for l in lines if l.startswith('CPU_CASE_RESULT ')]
    require(len(cases)==8,'Two complete reversed source cohorts required');last=0;durations=[];batch_plans=[];batch_returns=0
    for index,(case,width)in enumerate(zip(cases,WIDTHS)):
        require(case.get('schema')=='ps5-qwen-ready-original-CPU-case-v1'and type(case.get('index'))is int and case['index']==index and
            case.get('CPU_only_source_fixture')is True and case.get('Vulkan_owner_claimed')is False and case.get('model_loaded')is False and
            type(case.get('GPU_calls'))is int and case['GPU_calls']==0 and type(case.get('source_IO_depth'))is int and case['source_IO_depth']==width,
            'CPU fixture scope/index differs')
        expected=packets(plan)if width==2 else[(g,r,[i*2+g])for g in range(2)for r in range(3)for i in range(5)]
        pairs=sum(len(ids)==2 for _,_,ids in expected)
        require(case.get('model_source_plan_sha256')==sha and type(case.get('Direct_read_calls'))is int and case['Direct_read_calls']==30 and
            type(case.get('two_call_batches'))is int and case['two_call_batches']==pairs and type(case.get('maximum_descriptor_cache'))is int and
            case['maximum_descriptor_cache']==8 and integer(case.get('peak_open_descriptors'),1,8)and
            integer(case.get('descriptor_opens'),len(plan['files']),30)and type(case.get('descriptor_closes'))is int and
            case['descriptor_opens']==case['descriptor_closes']and case.get('inner_reader_joined')is True and case.get('all_descriptors_closed')is True,
            'CPU cache/worker/read count differs')
        reads=case.get('reads');require(type(reads)is list and len(reads)==30,'Thirty exact original roles required');at=0;first=None
        for batch,(group,role,ids)in enumerate(expected,1):
            end=last;events=''
            for ordinal in ids:
                row=reads[at];matrix=plan['matrices'][role*10+ordinal]
                for k,v in dict(id=at+1,ordinal=ordinal,group=group,role=role,source=matrix['source'],offset=matrix['offset'],bytes=STRIDE,batch=batch,batch_calls=len(ids)).items():
                    require(type(row.get(k))is int and row[k]==v,'CPU original source row differs: '+k)
                require(row.get('original_raw_sha256')==matrix['raw']and row.get('original_envelope_sha256')==matrix['envelope'],'CPU source byte proof differs')
                require(integer(row.get('begin_ns'),last,2**63-1)and integer(row.get('end_ns'),row['begin_ns']+1,2**63-1),'CPU read interval differs')
                if first is None:first=row['begin_ns']
                end=max(end,row['end_ns']);events+=str(row['id'])+':'+str(row['offset'])+':'+str(STRIDE)+',';at+=1
            last=end;batch_returns+=1
            batch_plans.append('ready_original_CPU_batch_before GPU_calls=0 operation='+str(batch)+' group='+str(group)+' role='+str(role)+' calls='+str(len(ids))+' events='+events)
        require(integer(case.get('elapsed_ns'),last-first,50_000_000_000),'CPU duration omits actual reads');durations.append(case['elapsed_ns'])
    require([l for l in lines if l.startswith('ready_original_CPU_batch_before ')]==batch_plans and
        lines.count('ready_original_CPU_batch_all_calls_and_byte_proofs_returned')==batch_returns,'CPU durable batch journal differs')
    gains=[];spreads=[]
    for at in(0,4):
        a,b,c,d=durations[at:at+4];gains.extend((a/b-1,d/c-1));spreads.append(max(abs(d/a-1),abs(c/b-1)))
    bound=max(spreads);decision='source_fixture_winner'if all(g>bound for g in gains)else'source_fixture_loser'if all(g < -bound for g in gains)else'inconclusive'
    return dict(schema='ps5-qwen-ready-original-CPU-review-v1',completed=True,native_original_source_qualified=True,
        cases=8,original_matrix_deliveries=240,source_payload_bytes=8*30*3276800,physical_bytes=8*30*STRIDE,
        source_comparison_decision=decision,elapsed_ns=durations,paired_source_gains=gains,observed_drift_bound=bound,
        all_reads_and_hashes_returned=True,all_workers_joined=True,Direct_released=True,unknown_completion=False,
        GPU_calls=0,title_launches=0,GPU_numerics_qualified=False,model_speed_qualified=False,production_adopted=False)
