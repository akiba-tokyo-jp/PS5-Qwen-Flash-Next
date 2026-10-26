# SPDX-License-Identifier: MIT
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from vector_layout_result import validate
def evidence():
    manifest=dict(nonce='abcd',source_integrity_scope='selected slices with sealed identities',groups=[[
        dict(offset=4194304+(i%2*3+i//2)*3293184,source_offset=i*16384)for i in range(6)]for _ in range(3)])
    lines=['context stage=1 exact=1 canaries=1','context stage=2 exact=1 canaries=1',
        'PACK_complete_SHA256_identity_EOF=1','ORIGINAL_selected_18_envelopes_SHA256_sealed_identity_EOF=1']
    lines+=['EOF_RETURNED pack=1 bytes=0']+[f'EOF_RETURNED group={g} item={i} bytes=0'for g in range(3)for i in range(6)]
    ident=0
    for round_ in range(8):
        for group in range(3):
            for mode in range(2):
                key=f'round={round_} group={group} mode={mode}';count=2 if mode else 6;events=[];plans=[]
                for i in range(count):
                    ident+=1;offset=manifest['groups'][group][i]['offset'if mode else 'source_offset'];size=(3 if mode else 1)*3293184
                    plan=f'{ident}:{offset}:{size}';plans.append(plan);events.append(plan+':1:1:'+str(size)+':100:150')
                lines+=['BATCH_BEGIN '+key,'LAYOUT_PLAN mode='+str(mode)+' events='+','.join(plans),
                    'LAYOUT_RETURNED count='+str(count)+' uncertain=0 events='+','.join(events),
                    'BATCH_DRAINED '+key+f' wall_ns={800 if mode else 1000} source_ns={700 if mode else 900} physical_bytes={6*3293184} copies=0',
                    'BATCH_EXACT '+key+' original_SHA256=6 envelope_SHA256=6 tail_canary=1']
    lines+=['context stage=3 exact=1 canaries=1','DIRECT_UNMAP_RETURNED rc=0','DIRECT_RELEASE_RETURNED rc=0',
        'END success=1 nonce=abcd all_workers_joined=1 Direct_released=1 pending_reads=0 GPU_calls=0 title_launches=0 no_retry=1']
    return '\n'.join(lines),manifest
class Controls(unittest.TestCase):
    def test_complete(self):
        raw,m=evidence();self.assertTrue(validate(raw,m)['fixture_gate_passed'])
    def test_journal_only_gain_fails(self):
        raw,m=evidence();r=validate(raw.replace('source_ns=700','source_ns=950').replace('wall_ns=800','wall_ns=990'),m)
        self.assertGreater(r['timings']['wall_ns']['paired_median_ratio'],1);self.assertFalse(r['fixture_gate_passed'])
    def test_uncertainty_and_corruption(self):
        raw,m=evidence()
        for bad in (raw.replace('uncertain=0','uncertain=1',1),raw.replace('Direct_released=1','Direct_released=0'),
            raw.replace('bytes=0','bytes=16384',1),raw.replace('source_ns=900','source_ns=0',1),
            raw.replace('original_SHA256=6','original_SHA256=5',1),raw.replace('canaries=1','canaries=0',1),
            raw.replace('1:0:3293184:1:1:3293184:100:150','1:0:3293184:1:1:1:100:150',1),
            raw.replace('LAYOUT_PLAN mode=0 events=1:0:','LAYOUT_PLAN mode=0 events=1:16384:',1),
            raw.replace('BATCH_BEGIN round=0 group=0 mode=0','BATCH_BEGIN round=0 group=1 mode=0',1),
            raw.replace('LAYOUT_RETURNED count=6','LAYOUT_RETURNED count=2',1)):
            with self.subTest(bad=bad[:30]):
                with self.assertRaises(ValueError):validate(bad,m)
if __name__=='__main__':unittest.main()
