# SPDX-License-Identifier: MIT
import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from lossless_codec_result import parse
class NativeDeliveryEvidence(unittest.TestCase):
    def setUp(self):
        self.manifest=dict(nonce='a'*32,rounds=2,samples=2,variants=['raw','exp','exp4'],
            extents=[[dict(requested=3276800),dict(requested=2457600),dict(requested=2457600)]for _ in range(2)])
        lines=['BEGIN nonce='+'a'*32+' GPU_calls=0 title_launches=0',
            'DIRECT_ALLOC_BEFORE bytes=8388608','DIRECT_ALLOC_RETURNED rc=0',
            'DIRECT_MAP_BEFORE bytes=8388608','DIRECT_MAP_RETURNED rc=0',
            'PACK_complete_SHA256_identity_EOF=1','ALL_65536_BF16_patterns_exact=1','EOF_BEFORE','EOF_RETURNED bytes=0']
        for r in range(2):
            for m in range(3):
                for i in range(2):
                    n=self.manifest['extents'][i][m]['requested'];restore=0 if m==0 else 10;read=100 if m==0 else 50
                    lines+=['READ_BEFORE bytes='+str(n),'READ_RETURNED bytes='+str(n),
                        f'SAMPLE round={r} mode={m} index={i} read_ns={read} restore_ns={restore} delivery_ns={read+restore} physical_bytes={n} exact_SHA256=1']
        lines+=['DIRECT_UNMAP_BEFORE','DIRECT_UNMAP_RETURNED rc=0','DIRECT_RELEASE_BEFORE','DIRECT_RELEASE_RETURNED rc=0',
            'END success=1 nonce='+'a'*32+' pending_reads=0 Direct_released=1 GPU_calls=0 title_launches=0 automatic_retry=0']
        self.text='\n'.join(lines)+'\n'
    def test_complete(self):
        r=parse(self.text.encode(),self.manifest)
        self.assertTrue(r['completed']);self.assertEqual(r['samples'],12)
        self.assertTrue(r['summary'][1]['clears_initial_delivery_gate'])
        self.assertFalse(r['whole_model_speed_qualified'])
    def test_refusals(self):
        changes=[('success=1','success=0'),('pending_reads=0','pending_reads=1'),('Direct_released=1','Direct_released=0'),
            ('exact_SHA256=1','exact_SHA256=0'),('delivery_ns=60','delivery_ns=61'),('GPU_calls=0','GPU_calls=1'),
            ('READ_RETURNED','READ_UNKNOWN'),('DIRECT_RELEASE_RETURNED rc=0','DIRECT_RELEASE_RETURNED rc=-1'),
            ('ALL_65536_BF16_patterns_exact=1','missing'),('PACK_complete_SHA256_identity_EOF=1','missing'),
            ('mode=2 index=1','mode=2 index=0'),('nonce='+'a'*32,'nonce='+'b'*32)]
        for before,after in changes:
            with self.subTest(before=before),self.assertRaises(ValueError):parse(self.text.replace(before,after,1).encode(),self.manifest)
    def test_incomplete(self):
        lines=self.text.splitlines();lines=[x for x in lines if not x.startswith('SAMPLE round=1 mode=2 index=1 ')]
        with self.assertRaises(ValueError):parse(('\n'.join(lines)+'\n').encode(),self.manifest)
    def test_wrong_transfer_size(self):
        m=copy.deepcopy(self.manifest);m['extents'][1][2]['requested']+=16384
        with self.assertRaises(ValueError):parse(self.text.encode(),m)
if __name__=='__main__':unittest.main()
