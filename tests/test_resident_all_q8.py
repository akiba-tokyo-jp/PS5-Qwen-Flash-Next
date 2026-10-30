# SPDX-License-Identifier: MIT
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from resident_all_q8 import CONV, placement, selected, stored_shape


class ResidentQ8Scope(unittest.TestCase):
    def test_only_resident_bf16(self):
        for name in ('blk.0.attn_qkv.weight', 'output_hc_down.weight'):
            self.assertTrue(selected(dict(name=name, type='BF16')))
        for name in (CONV, 'token_embd.weight', 'per_layer_token_embd.weight', 'blk.48.attn_q.weight', 'blk.0.ffn_down_exps.weight'):
            self.assertFalse(selected(dict(name=name, type='BF16')))
        for kind in ('Q2_K', 'Q2_0', 'Q8_0', 'F32'):
            self.assertFalse(selected(dict(name='blk.0.attn_qkv.weight', type=kind)))

    def test_narrow_convolution_remains_bf16(self):
        with self.assertRaises(ValueError):
            stored_shape(dict(name=CONV, shape=[4,10240]))
        self.assertEqual(stored_shape(dict(name='blk.0.attn_qkv.weight', shape=[2560,10240])), [2560,10240])
        with self.assertRaises(ValueError):
            stored_shape(dict(name='unadmitted.weight', shape=[4,10240]))
        self.assertEqual(placement('blk.48.ffn_down_exps.weight'), 'skipped_mtp')


if __name__ == '__main__':
    unittest.main()
