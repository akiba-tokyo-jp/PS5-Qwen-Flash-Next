# SPDX-License-Identifier: MIT
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from completion_delivery_result import parse,parse_preallocation_refusal
class CompletedDelivery(unittest.TestCase):
    def setUp(self):
        self.m=dict(nonce='c'*32,rounds=1,pack=dict(bytes=16384),variants=['raw_waves','raw_continuous','compressed_waves','compressed_continuous'],
            extents=[[dict(offset=(8<<20)+i*3276800,requested=3276800)for i in range(9)]for _ in range(2)])
        lines=['BEGIN nonce='+'c'*32+' io_bytes=8388608 destination_bytes=33554432 total_Direct_bytes=41943040 maximum_outstanding_reads=2 GPU_calls=0 title_launches=0',
            'DIRECT_ALLOC_BEFORE bytes=41943040','DIRECT_ALLOC_RETURNED rc=0','DIRECT_MAP_BEFORE bytes=41943040','DIRECT_MAP_RETURNED rc=0',
            'VERIFY_BEFORE bytes=16384','VERIFY_RETURNED bytes=16384','EOF_BEFORE','EOF_RETURNED bytes=0',
            'PACK_complete_SHA256_identity_EOF=1','ALL_65536_BF16_patterns_exact=1']
        for mode in range(4):
            lines.append(f'BATCH_BEGIN round=0 mode={mode}')
            for i,e in enumerate(self.m['extents'][mode>=2]):
                prefix=f'slot=0 id={mode*9+i} offset={e["offset"]} bytes={e["requested"]}'
                lines.extend(['IO_BEFORE '+prefix+' result=0 start_ns=0 end_ns=0',
                    'IO_RETURNED '+prefix+f' result=3276800 start_ns={i*20+1} end_ns={i*20+11}'])
            restore=0 if mode<2 else 20
            lines.extend([f'BATCH_DRAINED round=0 mode={mode} wall_ns=1000 restore_ns={restore} read_ns=90 physical_bytes=29491200',
                f'BATCH_EXACT round=0 mode={mode} complete_original_SHA256=9'])
        lines.extend(['DIRECT_UNMAP_BEFORE','DIRECT_UNMAP_RETURNED rc=0','DIRECT_RELEASE_BEFORE','DIRECT_RELEASE_RETURNED rc=0',
            'END success=1 nonce='+'c'*32+' pending_reads=0 all_workers_joined=1 Direct_released=1 GPU_calls=0 title_launches=0 automatic_retry=0'])
        self.text='\n'.join(lines)+'\n'
    def test_complete(self):
        proof=parse(self.text.encode(),self.m);self.assertEqual(proof['batches'],4)
        self.assertEqual(proof['rows'][0]['no_read_active_inside_span_ns'],80)
        self.assertFalse(proof['production_adoption_qualified'])
    def test_faults(self):
        changes=[('success=1','success=0'),('all_workers_joined=1','all_workers_joined=0'),
            ('GPU_calls=0','GPU_calls=1'),('destination_bytes=33554432','destination_bytes=0'),
            ('IO_RETURNED','IO_UNKNOWN'),('read_ns=90','read_ns=91'),('physical_bytes=29491200','physical_bytes=1'),
            ('complete_original_SHA256=9','complete_original_SHA256=8'),('result=3276800','result=1'),
            ('DIRECT_RELEASE_RETURNED rc=0','DIRECT_RELEASE_RETURNED rc=-1'),('VERIFY_RETURNED bytes=16384','VERIFY_RETURNED bytes=0'),
            ('BATCH_BEGIN round=0 mode=1','BATCH_BEGIN round=0 mode=0')]
        for a,b in changes:
            with self.subTest(a=a),self.assertRaises(ValueError):parse(self.text.replace(a,b,1).encode(),self.m)
    def test_zero_io_budget(self):
        m=dict(self.m,io_bytes=0)
        text=self.text.replace('io_bytes=8388608','io_bytes=0').replace('41943040','33554432')
        self.assertEqual(parse(text.encode(),m)['io_bytes'],0)
        with self.assertRaises(ValueError):parse(text.encode(),self.m)
    def test_positive_preallocation_refusal(self):
        m=dict(self.m,io_bytes=0,destination_bytes=10<<20)
        text=('BEGIN nonce='+'c'*32+' io_bytes=0 destination_bytes=10485760 total_Direct_bytes=10485760 maximum_outstanding_reads=2 GPU_calls=0 title_launches=0\n'
              'PREALLOC_HEADROOM free_first=1761 free_last=1761 minimum=898 reserved=206 additional_pages=640 required=1794 flexible_bytes=8554283008 rc=0\n'
              'END success=0 nonce='+'c'*32+' pending_reads=0 all_workers_joined=0 Direct_released=1 GPU_calls=0 title_launches=0 automatic_retry=0\n')
        proof=parse_preallocation_refusal(text.encode(),m)
        self.assertTrue(proof['completed']);self.assertFalse(proof['unknown_completion'])
        self.assertEqual(proof['allocations'],0)
        for a,b in [('success=0','success=1'),('pending_reads=0','pending_reads=1'),
                    ('required=1794','required=1000'),('free_first=1761 free_last=1761','free_first=2000 free_last=2000'),
                    ('Direct_released=1','Direct_released=0'),('END success','DIRECT_ALLOC_BEFORE bytes=10485760\nEND success'),
                    ('END success','UNKNOWN success')]:
            with self.subTest(a=a),self.assertRaises(ValueError):parse_preallocation_refusal(text.replace(a,b,1).encode(),m)
    def test_packed_three_matrices(self):
        m=dict(self.m,samples=3,variants=self.m['variants']+['packed_waves','packed_continuous'],
            extents=[x[:3]for x in self.m['extents']])
        lines=self.text.split('BATCH_BEGIN ',1)[0].splitlines()
        for mode in range(6):
            lines.append(f'BATCH_BEGIN round=0 mode={mode}')
            extents=m['extents'][2<=mode<4]
            if mode>=4:extents=[dict(offset=extents[0]['offset']+i*(4<<20),requested=(4<<20)if i<2 else 1441792)for i in range(3)]
            for i,e in enumerate(extents):
                prefix=f'slot=0 id={mode*3+i} offset={e["offset"]} bytes={e["requested"]}'
                lines+=['IO_BEFORE '+prefix+' result=0 start_ns=0 end_ns=0',
                    'IO_RETURNED '+prefix+f' result={e["requested"]} start_ns={i*20+1} end_ns={i*20+11}']
            restore=20 if 2<=mode<4 else 0;copy=20 if mode>=4 else 0
            lines+=[f'BATCH_DRAINED round=0 mode={mode} wall_ns=1000 restore_ns={restore} read_ns=30 physical_bytes=9830400 copy_ns={copy}',
                f'BATCH_EXACT round=0 mode={mode} complete_original_SHA256=3']
        lines+=self.text[self.text.index('DIRECT_UNMAP_BEFORE'):].splitlines()
        text='\n'.join(lines)+'\n';proof=parse(text.encode(),m);self.assertEqual(proof['batches'],6)
        self.assertEqual(proof['summary'][4]['median_copy_ms'],.00002)
        with self.assertRaises(ValueError):parse(text.replace('copy_ns=20','copy_ns=0',1).encode(),m)
        with self.assertRaises(ValueError):parse(text.replace('bytes=1441792','bytes=1441793',1).encode(),m)
if __name__=='__main__':unittest.main()
