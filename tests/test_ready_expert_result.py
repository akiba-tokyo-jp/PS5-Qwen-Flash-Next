# SPDX-License-Identifier: MIT
import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from ready_expert_result import validate_ready,validate_report,validate_stages,POLICY,HASHES
from test_split_bank_result import fixture as backing_sample

def sample():
    cases=[];prior=12;clock=100
    offsets=((4210688,7503872,10797056),(14090240,17383424,20676608))
    for index,mode in enumerate((0,1,2,2,1,0)):
        reads=[]
        for group in range(2):
            for role in range(3):
                raw,envelope=HASHES[role*2+group];begin=clock;clock+=10
                reads.append(dict(group=group,role=role,offset=offsets[group][role],bytes=3293184,begin_ns=begin,end_ns=clock,
                    original_raw_sha256=raw,original_envelope_sha256=envelope))
        submissions=[]
        for j,phase in enumerate((0,)if mode==0 else(1,2,3)):
            begin=clock;clock+=10
            submissions.append(dict(phase=phase,epoch=prior+j+1,begin_ns=begin,end_ns=clock,positive_synchronized_driver_completion=True))
        count=len(submissions)
        cases.append(dict(mode=mode,plan_epoch=index+1,prior_completed_GPU_epoch=prior,last_completed_GPU_epoch=prior+count,
            read_calls=6,GPU_graphs=count,source_to_output_ns=clock-reads[0]['begin_ns'],reads=reads,submissions=submissions,
            F64_reference_passed=True,same_F32_outputs_bit_exact=True,all_original_envelopes_and_canaries_intact=True,
            source_joined=True,wave_retired=True,output_F32_sha256='c'*64,contribution_F32_sha256='d'*64,
            maximum_absolute_error=1e-9,maximum_normalized_error=1e-4))
        prior+=count;clock+=10
    return dict(schema='ps5-qwen-ready-numerical-result-v1',cases=cases,unique_original_experts=2,original_contributions=10,
        source_IO_depth=1,source_coordinator_workers=1,Direct_read_calls=36,GPU_graphs=14,initial_positive_graph_epoch=12,
        final_positive_graph_epoch=26,reference_absolute_tolerance=1e-5,reference_relative_tolerance=1e-5,
        representative_speed_test=False,physical_GPU_timestamp_overlap_qualified=False,model_speed_qualified=False,production_adopted=False)

class ReadyResultTest(unittest.TestCase):
    def reject(self,change):
        r=sample();change(r)
        with self.assertRaises((ValueError,KeyError,TypeError)):validate_ready(r)
    def test_complete_and_optional_overlap(self):
        self.assertTrue(validate_ready(sample())['native_numerical_scope_passed'])
        # The numerical gate accepts either host interval outcome without a
        # hardware timestamp or representative speed claim.
        r=sample();c=r['cases'][2];c['submissions'][0]['begin_ns']=c['reads'][2]['end_ns']
        c['submissions'][0]['end_ns']=c['reads'][5]['end_ns']+1
        self.assertFalse(validate_ready(r)['model_speed_qualified'])
    def test_missing_and_changed_counts(self):
        for key in('Direct_read_calls','GPU_graphs','unique_original_experts','final_positive_graph_epoch'):
            self.reject(lambda r,k=key:r.__setitem__(k,r[k]+1))
        self.reject(lambda r:r['cases'].pop())
        self.reject(lambda r:r['cases'][0].__setitem__('GPU_graphs',3))
        self.reject(lambda r:r.__setitem__('GPU_graphs',True))
    def test_identity_precision_and_retirement(self):
        for key in('source_joined','wave_retired','F64_reference_passed','same_F32_outputs_bit_exact','all_original_envelopes_and_canaries_intact'):
            self.reject(lambda r,k=key:r['cases'][3].__setitem__(k,False))
        for key in('output_F32_sha256','contribution_F32_sha256'):
            self.reject(lambda r,k=key:r['cases'][4].__setitem__(k,'e'*64))
        self.reject(lambda r:r['cases'][0].__setitem__('maximum_normalized_error',1.01))
        self.reject(lambda r:r['cases'][1].__setitem__('maximum_absolute_error',float('nan')))
        self.reject(lambda r:r.__setitem__('reference_absolute_tolerance',1e-3))
    def test_source_and_dispatch_order(self):
        self.reject(lambda r:r['cases'][0]['reads'][0].__setitem__('offset',0))
        self.reject(lambda r:r['cases'][0]['reads'][0].__setitem__('original_raw_sha256','e'*64))
        self.reject(lambda r:r['cases'][1]['submissions'][0].__setitem__('begin_ns',1))
        self.reject(lambda r:r['cases'][1]['submissions'][1].__setitem__('epoch',999))
        self.reject(lambda r:r['cases'][1]['submissions'][2].__setitem__('positive_synchronized_driver_completion',False))
        self.reject(lambda r:r['cases'][1]['reads'][5].__setitem__('end_ns',r['cases'][1]['submissions'][0]['end_ns']+1))
    def test_no_speed_or_adoption_claim(self):
        for key in('representative_speed_test','physical_GPU_timestamp_overlap_qualified','model_speed_qualified','production_adopted'):
            self.reject(lambda r,k=key:r.__setitem__(k,True))
    def test_bound_whole_report(self):
        report,binding=backing_sample();binding['source_workers']=report['source_workers']=1
        report['ready_numerical']=sample();policy=dict(native_ready_expert_numerical=copy.deepcopy(POLICY),native_isolated_split_bank_title=binding)
        self.assertTrue(validate_report(report,policy,123)['native_numerical_scope_passed'])
        policy['native_ready_expert_numerical']['source_IO_depth']=True
        with self.assertRaises(ValueError):validate_report(report,policy,123)
    def test_bound_stage_plans(self):
        r=sample();lines=['split_bank_graph_before_submission']*12+['split_bank_graph_positive_idle_and_epoch_returned']*12
        for c in r['cases']:
            for read in c['reads']:
                lines.append('ready_numerical_read_before plan='+str(c['plan_epoch'])+' group='+str(read['group'])+' role='+str(read['role'])+
                    ' offset='+str(read['offset'])+' bytes='+str(read['bytes']))
                lines.append('ready_numerical_Direct_read_returned')
            for submission in c['submissions']:
                lines.append('ready_numerical_dispatch_before plan='+str(c['plan_epoch'])+' phase='+str(submission['phase'])+' epoch='+str(submission['epoch']))
                lines.append(('ready_expert_before_complete_serial_graph','ready_expert_before_first_group_graph',
                    'ready_expert_before_second_group_graph','ready_expert_before_original_reduction_graph')[submission['phase']])
                lines.append('ready_expert_graph_synchronized_driver_completion_returned')
        lines.append('split_bank_validation_completed_waiting_for_ordinary_close');text='\n'.join(lines)+'\n';validate_stages(text,r)
        for altered in(text.replace('plan=2','plan=7'),text.replace('ready_numerical_Direct_read_returned\n','',1),
            text.replace('epoch=13','epoch=14'),text+'failure\n'):
            with self.assertRaises(ValueError):validate_stages(altered,r)
if __name__=='__main__':unittest.main()
