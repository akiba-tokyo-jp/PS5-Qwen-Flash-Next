# SPDX-License-Identifier: MIT
import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from palette_gpu_result import parse

class PaletteResults(unittest.TestCase):
    def fixture(self):
        p={'native_palette_validation':{'rounds':6,'samples':[{'raw':{'requested':3276800},'encoded':{'requested':2408448}}for _ in range(9)]}}
        rows=[dict(round=r,sample=s,mode=(r+o)%2,read_ns=70 if(r+o)%2 else 100,
            dispatch_completion_ns=5,delivery_ns=80 if(r+o)%2 else 100,
            physical_bytes=2408448 if(r+o)%2 else 3276800,original_SHA256_exact=True)
            for r in range(6)for s in range(9)for o in range(2)]
        result=dict(schema='ps5-qwen-exact-palette-GPU-result-v1',pid=42,passed=True,all65536_BF16_patterns_exact=True,
            positive_device_idle_and_epoch_retirement=True,all_fences_positively_completed=True,source_file_closed=True,
            palette_delivery_includes_validation_dispatch_fence=True,model_loaded=False,full_model_inference=False,
            quantization=False,raw_delivery_includes_copy_check=False,GPU_dispatches=110,original_matrix_deliveries=108,
            automatic_retries=0,live_GPU_buffer_bytes=8<<20,rounds=rows)
        return result,p
    def test_complete_delivery_is_only_a_screen(self):
        result,p=self.fixture();r=parse(result,p,42)
        self.assertEqual(r['paired_round_median_ratio'],1.25);self.assertTrue(r['initial_delivery_screen_passed'])
        self.assertFalse(r['production_adoption']);self.assertFalse(r['full_model_admitted'])
        for row in result['rounds']:
            if row['mode']:row['delivery_ns']=120
        self.assertFalse(parse(result,p,42)['initial_delivery_screen_passed'])
    def test_refuses_incomplete_or_unfair_results(self):
        result,p=self.fixture()
        for key,value in [('pid',43),('passed',1),('source_file_closed',False),('all_fences_positively_completed',False),
            ('positive_device_idle_and_epoch_retirement',False),('raw_delivery_includes_copy_check',True),
            ('quantization',True),('GPU_dispatches',109),('automatic_retries',1),('live_GPU_buffer_bytes',16<<20)]:
            altered=copy.deepcopy(result);altered[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):parse(altered,p,42)
        for key,value in [('delivery_ns',110),('read_ns',-1),('dispatch_completion_ns',True),
                          ('physical_bytes',3276801),('original_SHA256_exact',False),('mode',1)]:
            altered=copy.deepcopy(result);altered['rounds'][0][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):parse(altered,p,42)
        altered=copy.deepcopy(result);altered['rounds'][1]['delivery_ns']=74
        with self.assertRaises(ValueError):parse(altered,p,42)
        with self.assertRaises(ValueError):parse(dict(result,rounds=result['rounds'][:-1]),p,42)
if __name__=='__main__':unittest.main()
