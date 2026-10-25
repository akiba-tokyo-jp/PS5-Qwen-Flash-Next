# SPDX-License-Identifier: MIT
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from kernel_memory_trace_result import parse

class TraceResults(unittest.TestCase):
    def fixture(self):
        manifest=dict(nonce='unit-owner',canonical_SELF=dict(bytes=(1<<20)+17))
        lines=['BEGIN nonce=unit-owner trace_capacity=64 window=1048576 direct_mode=1 explicit_allocations=0 title_launches=0 GPU_calls=0']
        lines += [f'context phase={i} exact=1 canaries=1'for i in (1,2,3)]
        for offset,requested,n in [(0,1048576,1048576),(1048576,16384,17),(1048576,16384,17)]:
            lines+=['READ_BEFORE',f'READ_RETURNED offset={offset} requested={requested} bytes={n}']
        lines+=['DIRECT_EXACT bytes=1048593 calls=3 returned=3 complete_SHA256_identity_EOF=1','FILE_CLOSED success=1']
        phases=[0]*5+[1]+[2]*3+[4]*5
        lines += [f'SAMPLE seq={i} phase={p} ns={i+1} free_first=2000 free_last=2000 total=138739 minimum=898 reserved=206 target=2974 active=28000 inactive=72000 wired=35000 cache=0 page_bytes=16384'for i,p in enumerate(phases)]
        lines+=['END success=1 nonce=unit-owner samples=14 explicit_allocations=0 title_launches=0 GPU_calls=0 automatic_retry=0']
        return '\n'.join(lines).encode('ascii'),manifest
    def test_valid(self):
        raw,m=self.fixture();r=parse(raw,m)
        self.assertTrue(r['completed']);self.assertEqual(r['reads'],3)
        self.assertFalse(r['inactive_pages_counted_as_available']);self.assertFalse(r['full_model_admitted'])
    def network_fixture(self):
        raw,m=self.fixture();m['network_control']=True
        lines=raw.decode('ascii').splitlines()
        first=next(i for i,line in enumerate(lines)if line.startswith('SAMPLE '))
        samples=lines[first:-1]
        control=[samples[0].replace('phase=0','phase=5')for _ in range(17)]
        samples=samples[:5]+control+samples[5:]
        import re
        samples=[re.sub(r'seq=\d+ phase=(\d+) ns=\d+',lambda match:f'seq={i} phase={match[1]} ns={i+1}',line)for i,line in enumerate(samples)]
        lines=lines[:first]+['NETWORK_WINDOW_ENDED']+samples+[lines[-1].replace('samples=14','samples=31')]
        return '\n'.join(lines).encode('ascii'),m
    def test_network_control(self):
        raw,m=self.network_fixture();r=parse(raw,m)
        self.assertEqual(r['network_interval_delta_pages']['free_first'],0)
        self.assertEqual(r['samples'],31)
        for altered in (raw.replace(b'NETWORK_WINDOW_ENDED',b''),
                        raw.replace(b'NETWORK_WINDOW_ENDED',b'NETWORK_WINDOW_ENDED\nNETWORK_WINDOW_ENDED'),
                        raw.replace(b'phase=5',b'phase=0'),
                        raw.replace(b'free_first=2000 free_last=2000',b'free_first=1200 free_last=1200')):
            with self.subTest(change=altered),self.assertRaises(ValueError):parse(altered,m)
    def test_rejects_incomplete_or_changed_evidence(self):
        raw,m=self.fixture()
        for a,b in [(b'END success=1',b'END success=0'),(b'nonce=unit-owner',b'nonce=wrong'),
            (b'GPU_calls=0',b'GPU_calls=1'),(b'automatic_retry=0',b'automatic_retry=1'),
            (b'canaries=1',b'canaries=0'),(b'READ_BEFORE\n',b''),
            (b'requested=16384 bytes=17',b'requested=16384 bytes=16'),
            (b'FILE_CLOSED success=1',b'FILE_CLOSED success=0'),
            (b'page_bytes=16384',b'page_bytes=4096'),(b'free_last=2000',b'free_last=1000'),
            (b'complete_SHA256_identity_EOF=1',b'complete_SHA256_identity_EOF=0'),
            (b'phase=4 ns=10',b'phase=0 ns=10'),(b'ns=10 ',b'ns=1 '),
            (b'samples=14',b'samples=15'),(b'returned=3',b'returned=2'),
            (b'trace_capacity=64',b'trace_capacity=65')]:
            with self.subTest(change=a),self.assertRaises(ValueError):parse(raw.replace(a,b),m)
        with self.assertRaises(ValueError):parse(raw+b'\nEND success=1',m)

if __name__=='__main__':unittest.main()
