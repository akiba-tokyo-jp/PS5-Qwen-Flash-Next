# SPDX-License-Identifier: MIT
import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from vector_bank_result import validate,validate_compact_stages

def good():
    r=dict(schema='ps5-qwen-vector-bank-result-v1',pid=7,original_matrix_deliveries=408,GPU_graphs=204,
        scalar_read_calls=204,vector_read_calls=68,device_ledger_live_bytes=0,device_ledger_peak_bytes=768<<20,
        copy_bytes=0,model_loaded=False,real_bank_slots=[0,52],selected_IDs=[52,0,26,0,50,2,52,13,25,42],
        non_BF16_exact_input_values=100,maximum_absolute_error=1e-8,shader_CPU_verified_assets=1527,shader_module_inputs_after_CPU_verification=2)
    for key in ('F64_reference_passed','F32_inputs_non_BF16_exact','same_F32_outputs_bit_exact','all_30_residues_passed',
        'canaries_intact','all_IO_returned_and_closed','all_workers_joined','all_three_strong_bank_leases_returned',
        'positive_device_idle_and_epoch_retirement','all_used_shader_inputs_SHA256_checked','all_shader_input_leases_returned'):r[key]=True
    r['batches']=[dict(round=round,group=g,mode=m,timed=True,delivery_wall_ns=100 if m else 120,physical_bytes=6*3293184,copies=0)
        for round in range(8)for g in range(3)for m in range(2)]
    r['batches'] += [dict(round=0,group=g,mode=m,timed=False,delivery_wall_ns=100,physical_bytes=6*3293184,copies=0)for g in range(3,13)for m in range(2)]
    return r

def compact_good():
    r=good();r['schema']='ps5-qwen-vector-bank-result-compact-v2';ident=0
    for n,row in enumerate(r['batches']):
        start=1000+n*1000;duration=80 if row['mode']else 100
        row.update(source_begin_ns=start,source_end_ns=start+duration,source_critical_ns=duration,batch_safety_records=2,io_events=[])
        for i in range(2 if row['mode']else 6):
            ident+=1;size=(3 if row['mode']else 1)*3293184
            row['io_events'].append([ident,4194304+i*size,size,True,True,size,start+1,start+duration-1])
    return r

class Controls(unittest.TestCase):
    def test_durable_binding(self):
        r=compact_good();lines=[]
        for b in r['batches']:
            lines+=['vector_bank_IO_batch_plan group='+str(b['group'])+' mode='+str(b['mode'])+' events='+','.join(':'.join(str(int(v))for v in e[:3])for e in b['io_events']),
                'vector_bank_IO_batch_returned count='+str(len(b['io_events']))+' uncertain=0 events='+','.join(':'.join(str(int(v))for v in e)for e in b['io_events']),
                'vector_bank_batch_exact_GPU_fences_completed']
        stages='\n'.join(lines);self.assertTrue(validate_compact_stages(r,stages)['all_durable_plans_and_returns_match'])
        for bad in ('\n'.join(lines[1:]),stages.replace('uncertain=0','uncertain=1',1),stages.replace('group=0','group=1',1),stages+'\nvector_bank_IO_before id=1'):
            with self.assertRaises(ValueError):validate_compact_stages(r,bad)
    def test_compact_complete(self):
        review=validate(compact_good(),7)
        self.assertTrue(review['fixture_gate_passed']);self.assertEqual(review['compact_IO_events'],272)
    def test_journal_only_win_refused(self):
        r=compact_good()
        for row in r['batches']:
            if row['mode']:
                row['source_critical_ns']=110;row['source_end_ns']=row['source_begin_ns']+110;row['delivery_wall_ns']=115
        review=validate(r,7)
        self.assertGreater(review['paired_median_ratio'],1);self.assertFalse(review['fixture_gate_passed'])
    def test_compact_bad_events(self):
        edits=[lambda r:r['batches'][0]['io_events'].pop(),
            lambda r:r['batches'][0]['io_events'][0].__setitem__(3,False),
            lambda r:r['batches'][0]['io_events'][0].__setitem__(4,False),
            lambda r:r['batches'][0]['io_events'][0].__setitem__(5,1),
            lambda r:r['batches'][0]['io_events'][0].__setitem__(0,2),
            lambda r:r['batches'][0]['io_events'][0].__setitem__(6,0),
            lambda r:r['batches'][0]['io_events'][0].__setitem__(7,1000000),
            lambda r:r['batches'][0]['io_events'][0].__setitem__(1,1),
            lambda r:r['batches'][0].__setitem__('batch_safety_records',1),
            lambda r:r['batches'][0].__setitem__('source_critical_ns',True),
            lambda r:r['batches'][0].__setitem__('source_end_ns',999)]
        for edit in edits:
            r=compact_good();edit(r)
            with self.assertRaises(ValueError):validate(r,7)
    def test_compact_missing_fields(self):
        for key in ('source_critical_ns','source_begin_ns','source_end_ns','batch_safety_records','io_events'):
            r=compact_good();del r['batches'][0][key]
            with self.assertRaises(ValueError):validate(r,7)
    def test_complete(self):self.assertTrue(validate(good(),7)['fixture_gate_passed'])
    def test_known_loss(self):
        r=good()
        for row in r['batches']:
            if row['mode']==1:row['delivery_wall_ns']=140
        self.assertFalse(validate(r,7)['fixture_gate_passed'])
    def test_each_missing_field(self):
        for key in good():
            with self.subTest(key=key):
                r=good();del r[key]
                with self.assertRaises(ValueError):validate(r,7)
    def test_owner_and_uncertainty(self):
        with self.assertRaises(ValueError):validate(good(),8)
        for key in ('all_workers_joined','all_IO_returned_and_closed','same_F32_outputs_bit_exact','positive_device_idle_and_epoch_retirement'):
            r=good();r[key]=False
            with self.assertRaises(ValueError):validate(r,7)
    def test_cohort(self):
        for mutation in ('missing','duplicate','copies','types','nan'):
            r=good()
            if mutation=='missing':r['batches'].pop()
            if mutation=='duplicate':r['batches'][-1]=copy.deepcopy(r['batches'][0])
            if mutation=='copies':r['batches'][0]['copies']=1
            if mutation=='types':r['batches'][0]['round']=False
            if mutation=='nan':r['maximum_absolute_error']=float('nan')
            with self.assertRaises(ValueError):validate(r,7)

if __name__=='__main__':unittest.main()
