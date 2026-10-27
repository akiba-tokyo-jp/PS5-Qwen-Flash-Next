# SPDX-License-Identifier: MIT
from pathlib import Path
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from predictive_worker_result import validate
class WorkerResultTests(unittest.TestCase):
    def fixture(self):
        nonce='a'*32;plan='b'*64
        rows=[f'BEGIN nonce={nonce} plan_sha256={plan} Direct_bytes=9912320 rounds=4 roles=3 GPU_calls=0 title_launches=0']
        rows+=['context exact=1 canaries=1']*3
        rows+=['DIRECT_ALLOC_RETURNED rc=0','DIRECT_MAP_RETURNED rc=0','WORKER_START_RETURNED persistent=1']
        for n in range(4):
            rows+=[f'JOB_BEFORE round={n} roles=3 expected_bytes=9879552']
            rows+=[f'ROLE_RETURNED round={n} role={i} bytes=3293184 errno=0 begin_ns={100+i*10} end_ns={110+i*10}'for i in range(3)]
            rows+=[f'JOB_RETURNED round={n} elapsed_ns=40 foreground_ns=10 wait_ns=30 exact_hashes_and_canaries=1 foreground_cost_control=1 pending=0']
        rows+=['WORKER_JOINED persistent_lifetimes=1 jobs=4','DIRECT_UNMAP_RETURNED rc=0','DIRECT_RELEASE_RETURNED rc=0',
            f'END success=1 nonce={nonce} worker_joined=1 Direct_released=1 GPU_calls=0 title_launches=0 no_retry=1']
        return '\n'.join(rows),nonce,plan
    def test_complete_is_not_a_model_speed_result(self):
        result=validate(*self.fixture());self.assertEqual(result['original_role_deliveries'],12)
        self.assertFalse(result['native_model_speed_qualified']);self.assertFalse(result['GPU_overlap_qualified'])
    def test_missing_changed_or_uncertain_result_refuses(self):
        raw,nonce,plan=self.fixture()
        for old,new in(('ROLE_RETURNED round=0 role=0','omitted'),('bytes=3293184','bytes=3293183'),
            ('exact_hashes_and_canaries=1','exact_hashes_and_canaries=0'),('pending=0','pending=1'),
            ('DIRECT_RELEASE_RETURNED rc=0','DIRECT_RELEASE_RETURNED rc=1'),('worker_joined=1','worker_joined=0'),
            ('foreground_ns=10','foreground_ns=11')):
            with self.assertRaises(ValueError):validate(raw.replace(old,new,1),nonce,plan)
        with self.assertRaises(ValueError):validate(raw+'\nRETAIN unknown_completion=1',nonce,plan)
    def test_returned_refusal_is_not_success(self):
        raw,nonce,plan=self.fixture();result=validate(raw.replace('END success=1','END success=0'),nonce,plan)
        self.assertFalse(result['completed']);self.assertTrue(result['returned_known_refusal'])
if __name__=='__main__':unittest.main()
