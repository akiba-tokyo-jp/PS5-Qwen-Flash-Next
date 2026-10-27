# SPDX-License-Identifier: MIT
import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from ready_original_result import packets,validate_original,validate_original_stages,validate_combined
from ready_expert_result import POLICY
from test_ready_expert_result import sample as numerical_sample
from test_split_bank_result import fixture as backing_sample
def sample(durations=(1000,1100,800,805,1110,1005)):
    plan=dict(experts=list(range(10)),files=[dict(identity=[1,i+2,0,0,0,512<<20,0,0,0,0])for i in range(3)],matrices=[])
    for role in range(3):
        for ordinal in range(10):plan['matrices'].append(dict(source=role,offset=(4<<20)+ordinal*3293184,residue=32,raw=str(ordinal)*64,envelope=str(role)*64))
    expected=packets(plan);cases=[];prior=26;clock=100
    for index,(mode,duration)in enumerate(zip((0,1,2,2,1,0),durations)):
        reads=[];group_end=[0,0]
        for batch,(group,role,ordinals)in enumerate(expected,1):
            for j,ordinal in enumerate(ordinals):
                m=plan['matrices'][role*10+ordinal]
                reads.append(dict(id=len(reads)+1,ordinal=ordinal,group=group,role=role,source=role,offset=m['offset'],bytes=3293184,
                    begin_ns=clock+j,end_ns=clock+8+j*2,batch=batch,batch_calls=len(ordinals),original_raw_sha256=m['raw'],original_envelope_sha256=m['envelope']))
            clock+=20;group_end[group]=reads[-1]['end_ns']
        submits=[]
        for j,phase in enumerate((0,)if mode==0 else(1,2,3)):
            begin=group_end[0]+1 if mode==2 and j==0 else clock
            end=clock+5 if mode==2 and j==0 else clock+10
            submits.append(dict(phase=phase,epoch=prior+j+1,begin_ns=begin,end_ns=end,positive_synchronized_driver_completion=True));clock=end+10
        count=len(submits);cases.append(dict(mode=mode,plan_epoch=index+7,prior_completed_GPU_epoch=prior,last_completed_GPU_epoch=prior+count,
            read_calls=30,GPU_graphs=count,F64_reference_passed=True,same_F32_outputs_bit_exact=True,all_original_envelopes_and_canaries_intact=True,
            source_joined=True,wave_retired=True,maximum_absolute_error=1e-8,maximum_normalized_error=.001,output_F32_sha256='a'*64,
            contribution_F32_sha256='b'*64,reads=reads,submissions=submits,source_to_output_ns=duration,
            source_owner=dict(reads=copy.deepcopy(reads),Direct_read_calls=30,two_call_batches=12,maximum_descriptor_cache=8,peak_open_descriptors=3,
                descriptor_opens=3,descriptor_closes=3,inner_reader_joined=True,all_descriptors_closed=True,model_source_plan_sha256='c'*64)))
        prior+=count;clock+=10
    r=dict(schema='ps5-qwen-ready-original-result-v1',unique_original_experts=10,original_contributions=10,source_IO_depth=2,
        source_coordinator_workers=1,inner_IO_workers=1,Direct_read_calls=180,GPU_graphs=14,initial_positive_graph_epoch=26,final_positive_graph_epoch=40,
        model_source_plan_sha256='c'*64,actual_recorded_Expert_ids=list(range(10)),representative_speed_test=True,fixture_activation_and_weights_are_deterministic=True,
        physical_GPU_timestamp_overlap_qualified=False,model_speed_qualified=False,production_adopted=False,reference_absolute_tolerance=1e-5,reference_relative_tolerance=1e-5,cases=cases)
    return r,plan
class OriginalResult(unittest.TestCase):
    def reject(self,change):
        r,p=sample();change(r)
        with self.assertRaises((ValueError,KeyError,TypeError)):validate_original(r,p,'c'*64)
    def test_fixture_winner_is_not_model_adoption(self):
        r,p=sample();v=validate_original(r,p,'c'*64);self.assertEqual(v['comparison_decision'],'fixture_winner_requires_model_validation');self.assertFalse(v['production_adopted'])
    def test_loss_noise_and_missing_overlap(self):
        r,p=sample((1000,1100,1300,1310,1110,1005));self.assertEqual(validate_original(r,p,'c'*64)['comparison_decision'],'fixture_loser')
        r,p=sample((1000,1100,900,1100,1110,1005));self.assertEqual(validate_original(r,p,'c'*64)['comparison_decision'],'inconclusive')
        r,p=sample();c=r['cases'][2];c['submissions'][0]['begin_ns']=c['reads'][-1]['end_ns']+1
        self.assertEqual(validate_original(r,p,'c'*64)['comparison_decision'],'inconclusive')
    def test_ownership_counts_and_precision(self):
        self.reject(lambda r:r['cases'][0]['source_owner'].__setitem__('peak_open_descriptors',9))
        self.reject(lambda r:r['cases'][0]['source_owner'].__setitem__('inner_reader_joined',False))
        self.reject(lambda r:r['cases'][0]['source_owner'].__setitem__('descriptor_closes',2))
        self.reject(lambda r:r['cases'][0].__setitem__('maximum_normalized_error',1.01))
        self.reject(lambda r:r['cases'][5].__setitem__('contribution_F32_sha256','e'*64))
        self.reject(lambda r:r.__setitem__('actual_recorded_Expert_ids',[False,1,2,3,4,5,6,7,8,9]))
    def test_source_corruption_and_disorder(self):
        for key,value in(('source',2),('original_raw_sha256','e'*64),('ordinal',1),('batch',99)):
            self.reject(lambda r,k=key,v=value:r['cases'][0]['reads'][0].__setitem__(k,v))
        self.reject(lambda r:r['cases'][0].__setitem__('source_to_output_ns',1))
        self.reject(lambda r:r['cases'][0]['submissions'][0].__setitem__('begin_ns',1))
        self.reject(lambda r:r['cases'][3].__setitem__('last_completed_GPU_epoch',99))
    def test_no_false_model_claim(self):
        for key in('model_speed_qualified','production_adopted','physical_GPU_timestamp_overlap_qualified'):self.reject(lambda r,k=key:r.__setitem__(k,True))
    def test_native_journal_binding(self):
        r,p=sample();lines=[]
        for c in r['cases']:
            at=0
            for batch,(group,role,ordinals)in enumerate(packets(p),1):
                events=''.join(str(c['reads'][at+j]['id'])+':'+str(c['reads'][at+j]['offset'])+':3293184,'for j in range(len(ordinals)))
                lines.append('ready_original_batch_before plan='+str(c['plan_epoch'])+' operation='+str(batch)+' group='+str(group)+' role='+str(role)+' calls='+str(len(ordinals))+' events='+events)
                lines.append('ready_original_batch_all_calls_and_byte_proofs_returned');at+=len(ordinals)
            for s in c['submissions']:lines.append('ready_original_dispatch_before plan='+str(c['plan_epoch'])+' phase='+str(s['phase'])+' epoch='+str(s['epoch']))
        text='\n'.join(lines);validate_original_stages(text,r,p)
        for bad in(text.replace('plan=7','plan=9'),text.replace('ready_original_batch_all_calls_and_byte_proofs_returned','missing',1)):
            with self.assertRaises(ValueError):validate_original_stages(bad,r,p)
    def test_complete_gate_and_cross_cohort_order(self):
        original,p=sample();numerical=numerical_sample();report,binding=backing_sample();binding['source_workers']=report['source_workers']=2
        shift=max(s['end_ns']for c in numerical['cases']for s in c['submissions'])+100
        for c in original['cases']:
            for row in c['reads']+c['submissions']:row['begin_ns']+=shift;row['end_ns']+=shift
            c['source_owner']['reads']=copy.deepcopy(c['reads'])
        report.update(ready_original=original,ready_numerical=numerical)
        policy=dict(native_isolated_split_bank_title=binding,native_ready_expert_numerical=copy.deepcopy(POLICY),native_ready_expert_original=dict(
            schema='ps5-qwen-ready-original-policy-v1',enabled=True,same_title_numerical_gate_required=True,unique_original_experts=10,source_IO_depth=2,cohort_runs=6,source_plan_sha256='c'*64))
        phases=('ready_expert_before_complete_serial_graph','ready_expert_before_first_group_graph','ready_expert_before_second_group_graph','ready_expert_before_original_reduction_graph')
        lines=[]
        for _ in range(12):lines+=['split_bank_graph_before_submission','split_bank_graph_positive_idle_and_epoch_returned']
        for c in numerical['cases']:
            for row in c['reads']:
                lines+=['ready_numerical_read_before plan='+str(c['plan_epoch'])+' group='+str(row['group'])+' role='+str(row['role'])+' offset='+str(row['offset'])+' bytes='+str(row['bytes']),'ready_numerical_Direct_read_returned']
            for s in c['submissions']:lines+=['ready_numerical_dispatch_before plan='+str(c['plan_epoch'])+' phase='+str(s['phase'])+' epoch='+str(s['epoch']),phases[s['phase']],'ready_expert_graph_synchronized_driver_completion_returned']
        for c in original['cases']:
            at=0
            for batch,(group,role,ordinals)in enumerate(packets(p),1):
                events=''.join(str(c['reads'][at+j]['id'])+':'+str(c['reads'][at+j]['offset'])+':3293184,'for j in range(len(ordinals)))
                lines+=['ready_original_batch_before plan='+str(c['plan_epoch'])+' operation='+str(batch)+' group='+str(group)+' role='+str(role)+' calls='+str(len(ordinals))+' events='+events,'ready_original_batch_all_calls_and_byte_proofs_returned'];at+=len(ordinals)
            for s in c['submissions']:lines+=['ready_original_dispatch_before plan='+str(c['plan_epoch'])+' phase='+str(s['phase'])+' epoch='+str(s['epoch']),phases[s['phase']],'ready_expert_graph_synchronized_driver_completion_returned']
        lines.append('split_bank_validation_completed_waiting_for_ordinary_close');text='\n'.join(lines)
        self.assertFalse(validate_combined(report,policy,p,'c'*64,text,123)['production_adopted'])
        altered=copy.deepcopy(report);altered['ready_numerical']['cases'][0]['source_joined']=False
        with self.assertRaises(ValueError):validate_combined(altered,policy,p,'c'*64,text,123)
        altered=copy.deepcopy(report);altered['ready_original']['cases'][0]['reads'][0]['begin_ns']=1
        with self.assertRaises(ValueError):validate_combined(altered,policy,p,'c'*64,text,123)
        reordered=list(lines);index=next(i for i,l in enumerate(reordered)if l.startswith('ready_original_batch_before '));line=reordered.pop(index);reordered.insert(0,line)
        with self.assertRaises(ValueError):validate_combined(report,policy,p,'c'*64,'\n'.join(reordered),123)
if __name__=='__main__':unittest.main()
