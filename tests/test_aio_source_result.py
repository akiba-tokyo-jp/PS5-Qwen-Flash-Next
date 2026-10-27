# SPDX-License-Identifier: MIT
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from aio_source_result import validate


class AIOResultTests(unittest.TestCase):
    def sample(self):
        rows=['BEGIN nonce='+'a'*32+' plan_sha256='+'b'*64+' GPU_calls=0 title_launches=0',
              *['context exact=1 canaries=1']*3,'AIO_INITIALIZE_RETURNED rc=0 canaries=1',
              'AIO_INVALID_FD_COMPLETED value=-9 terminal=4 retired_once=1']
        for n,m in enumerate((0,1,1,0,0,1,1,0)):
            rows.append(f'PAIR_RETURNED round={n} mode={m} elapsed_ns={100 if m else 200} bytes=6586368 original_hashes=1 identities=1 all_requests_retired=1')
        return '\n'.join(rows+['DIRECT_UNMAP_RETURNED rc=0','DIRECT_RELEASE_RETURNED rc=0',
            'END success=1 nonce='+'a'*32+' all_workers_joined=1 all_AIO_IDs_retired=1 Direct_released=1 GPU_calls=0 title_launches=0 no_retry=1'])

    def test_complete_reverse_comparison(self):
        result=validate(self.sample(),'a'*32,'b'*64)
        self.assertTrue(result['completed'])
        self.assertEqual(result['decision'],'source_fixture_winner')
        self.assertFalse(result['native_model_speed_qualified'])

    def test_unknown_or_missing_owners_refused(self):
        for text in ('all_workers_joined=0','all_AIO_IDs_retired=0','Direct_released=0'):
            key=text.split('=')[0]
            with self.assertRaises(ValueError):validate(self.sample().replace(key+'=1',text),'a'*32,'b'*64)
        with self.assertRaises(ValueError):validate(self.sample()+'\nRETAIN unknown_completion=1','a'*32,'b'*64)

    def test_geometry_hashes_and_incomplete_cohort_refused(self):
        for old,new in (('bytes=6586368','bytes=1'),('original_hashes=1','original_hashes=0'),
                        ('identities=1','identities=0'),('round=7','round=6'),('AIO_INITIALIZE_RETURNED rc=0','AIO_INITIALIZE_RETURNED rc=-1')):
            with self.assertRaises(ValueError):validate(self.sample().replace(old,new),'a'*32,'b'*64)


if __name__=='__main__':unittest.main()
