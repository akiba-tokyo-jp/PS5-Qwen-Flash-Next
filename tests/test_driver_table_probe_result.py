# SPDX-License-Identifier: MIT
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from driver_table_probe_result import validate
class Result(unittest.TestCase):
    def setUp(self):
        self.nonce='a'*32;self.digest='b'*64
        self.raw=f'BEGIN nonce={self.nonce} manifest_sha256={self.digest} tables=640 raw_bytes=7688966 packed_bytes=247740 GPU_calls=0 title_launches=0\n'
        for phase in range(1,4):
            self.raw+=f'context phase={phase} exact=1 canaries=1\n'
            for i in range(8):self.raw+=f'process phase={phase} expected=role{i} exact=1 canaries=1\n'
        self.raw+='RESTORE_RETURNED exact_hashes=1 codec_released=1 readonly_protection=1 elapsed_ns=1000000 scratch_peak=39928\n'
        self.raw+=f'END success=1 nonce={self.nonce} GPU_calls=0 title_launches=0 no_retry=1\n'
    def check(self,raw):return validate(raw,self.nonce,self.digest,640,7688966,247740)
    def test_positive(self):self.assertTrue(self.check(self.raw)['completed'])
    def test_unknown(self):
        with self.assertRaises(ValueError):self.check(self.raw[:self.raw.index('END ')])
    def test_integrity_and_ownership(self):
        for old,new in(('exact_hashes=1','exact_hashes=0'),('readonly_protection=1','readonly_protection=0'),('canaries=1','canaries=0'),('tables=640','tables=639')):
            with self.subTest(field=old),self.assertRaises(ValueError):self.check(self.raw.replace(old,new,1))
    def test_refusal(self):self.assertFalse(self.check(self.raw.replace('END success=1','END success=0'))['completed'])
if __name__=='__main__':unittest.main()
