# SPDX-License-Identifier: MIT
import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from indexed_vector_result import validate_fixture
def fixture(modern=True):
    rows=[]
    for k,n,v in ((2560,640,1),(2560,640,10),(640,2560,1),(640,2560,10)):
        row=dict(columns=k,rows=n,input_vectors=v,passed=True,max_absolute_error=2e-8,
                 first_ms=[10.0,9.0],warm_mean_ms=[8.0,7.0])
        if modern:row['non_BF16_exact_F32_inputs']=sum((c*11+s)%13!=6 for s in range(v)for c in range(k))
        rows.append(row)
    r=dict(schema='ps5-qwen-BF16-indexed-vector-fixture-v'+('2'if modern else'1'),model_loaded=False,
           positive_completion_and_retirement=True,graphs_per_strategy=3,selected_experts=10,
           repeated_and_boundary_IDs=True,maximum_BF16_bank_bytes=32768000,cases=rows,
           path_counters=dict(BF16_indexed_matrix_calls=12,BF16_indexed_vector_calls=16 if modern else 12))
    if modern:r.update(additional_non_dyadic_vector_graphs_per_layout=1,timed_strategy_inputs_identical=True,
                       reference_accumulation='F64',maximum_absolute_error_limit=1e-6)
    return r
class FixtureAdmission(unittest.TestCase):
    def test_current_and_legacy(self):
        self.assertTrue(validate_fixture(fixture(),True)['non_dyadic_F32_inputs_qualified'])
        self.assertFalse(validate_fixture(fixture(False))['non_dyadic_F32_inputs_qualified'])
        with self.assertRaises(ValueError):validate_fixture(fixture(False),True)
    def test_refusals(self):
        for change in ('nan','infinite','negative','over_limit','shape','unreturned','population','missing_graph','different_timed_inputs'):
            with self.subTest(change=change):
                r=copy.deepcopy(fixture())
                if change in ('nan','infinite','negative','over_limit'):
                    r['cases'][0]['max_absolute_error']={'nan':float('nan'),'infinite':float('inf'),'negative':-1,'over_limit':1.1e-6}[change]
                elif change=='shape':r['cases'][1]['input_vectors']=2
                elif change=='unreturned':r['positive_completion_and_retirement']=False
                elif change=='population':r['cases'][0]['non_BF16_exact_F32_inputs']=0
                elif change=='missing_graph':r['path_counters']['BF16_indexed_vector_calls']=15
                else:r['timed_strategy_inputs_identical']=False
                with self.assertRaises(ValueError):validate_fixture(r,True)
if __name__=='__main__':unittest.main()
