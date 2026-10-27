# SPDX-License-Identifier: MIT
import copy,json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from ready_original_CPU_result import validate,WIDTHS
from ready_original_result import packets,STRIDE
from test_ready_original_result import sample
def fixture(durations=(1000000,700000,700100,1000100,1000000,700000,700100,1000100)):
    _,plan=sample();lines=['context phase='+str(i)+' exact=1 canaries=1'for i in(1,2,3)];clock=1000
    lines+=['process phase='+str(p)+' owner='+str(i)+' exact=1 canaries=1'for p in(1,2,3)for i in range(8)]
    cases=[]
    for index,width in enumerate(WIDTHS):
        groups=packets(plan)if width==2 else[(g,r,[i*2+g])for g in range(2)for r in range(3)for i in range(5)]
        reads=[]
        for batch,(group,role,ids)in enumerate(groups,1):
            events=''
            for j,ordinal in enumerate(ids):
                m=plan['matrices'][role*10+ordinal];row=dict(id=len(reads)+1,ordinal=ordinal,group=group,role=role,source=m['source'],offset=m['offset'],bytes=STRIDE,
                    batch=batch,batch_calls=len(ids),begin_ns=clock+j,end_ns=clock+10+j,original_raw_sha256=m['raw'],original_envelope_sha256=m['envelope'])
                reads.append(row);events+=str(row['id'])+':'+str(row['offset'])+':'+str(STRIDE)+','
            clock+=20;lines+=['ready_original_CPU_batch_before GPU_calls=0 operation='+str(batch)+' group='+str(group)+' role='+str(role)+' calls='+str(len(ids))+' events='+events,
                'ready_original_CPU_batch_all_calls_and_byte_proofs_returned']
        case=dict(schema='ps5-qwen-ready-original-CPU-case-v1',index=index,CPU_only_source_fixture=True,Vulkan_owner_claimed=False,model_loaded=False,GPU_calls=0,
            source_IO_depth=width,model_source_plan_sha256='c'*64,Direct_read_calls=30,two_call_batches=sum(len(ids)==2 for _,_,ids in groups),maximum_descriptor_cache=8,
            peak_open_descriptors=3,descriptor_opens=3,descriptor_closes=3,inner_reader_joined=True,all_descriptors_closed=True,reads=reads,elapsed_ns=durations[index])
        cases.append(case);lines.append('CPU_CASE_RESULT '+json.dumps(case));clock+=durations[index]
    lines+=['DIRECT_UNMAP_RETURNED rc=0','DIRECT_RELEASE_RETURNED rc=0','CPU_READS_RETURNED_AND_JOINED result=1 both_scratch_boundary_canaries=1',
        'END success=1 nonce=nonce all_workers_joined=1 Direct_released=1 pending_reads=0 GPU_calls=0 title_launches=0 no_retry=1']
    return '\n'.join(lines),plan,cases
class CPUResult(unittest.TestCase):
    def test_native_source_winner_is_not_model_adoption(self):
        text,plan,_=fixture();r=validate(text,plan,'c'*64,'nonce');self.assertEqual(r['source_comparison_decision'],'source_fixture_winner');self.assertFalse(r['model_speed_qualified'])
    def test_loss_and_noise(self):
        t,p,_=fixture((1000000,1300000,1300100,1000100)*2);self.assertEqual(validate(t,p,'c'*64,'nonce')['source_comparison_decision'],'source_fixture_loser')
        t,p,_=fixture((1000000,700000,1200000,1000100)*2);self.assertEqual(validate(t,p,'c'*64,'nonce')['source_comparison_decision'],'inconclusive')
    def test_resource_and_byte_faults(self):
        for key,value in(('source_IO_depth',3),('descriptor_closes',0),('inner_reader_joined',False),('CPU_only_source_fixture',False),('Vulkan_owner_claimed',True),('elapsed_ns',1)):
            t,p,c=fixture();bad=copy.deepcopy(c[0]);bad[key]=value;t=t.replace('CPU_CASE_RESULT '+json.dumps(c[0]),'CPU_CASE_RESULT '+json.dumps(bad))
            with self.assertRaises(ValueError):validate(t,p,'c'*64,'nonce')
        t,p,c=fixture();bad=copy.deepcopy(c[0]);bad['reads'][0]['original_raw_sha256']='e'*64
        with self.assertRaises(ValueError):validate(t.replace('CPU_CASE_RESULT '+json.dumps(c[0]),'CPU_CASE_RESULT '+json.dumps(bad)),p,'c'*64,'nonce')
    def test_failed_completion_or_journal_cannot_pass(self):
        t,p,_=fixture()
        for a,b in(('END success=1','END success=0'),('Direct_released=1','Direct_released=0'),('both_scratch_boundary_canaries=1','both_scratch_boundary_canaries=0'),
            ('ready_original_CPU_batch_all_calls_and_byte_proofs_returned','missing'),('operation=1 ','operation=90 ')):
            with self.assertRaises(ValueError):validate(t.replace(a,b,1),p,'c'*64,'nonce')
    def test_missing_case_nonce_or_context(self):
        t,p,_=fixture()
        for bad in(t.replace('CPU_CASE_RESULT ','missing ',1),t.replace('nonce=nonce','nonce=other'),t.replace('context phase=1 exact=1','context phase=1 exact=0')):
            with self.assertRaises(ValueError):validate(bad,p,'c'*64,'nonce')
if __name__=='__main__':unittest.main()
