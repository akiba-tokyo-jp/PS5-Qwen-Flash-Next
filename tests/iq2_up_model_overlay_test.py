#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise complete serialized GGUF descriptors without tensor payload allocation."""
import copy
from pathlib import Path
import struct
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from audit_shared_q8_headers import parse
from prepare_iq2_up_model_overlay import rewrite_header


def main():
    kinds = dict(Q2_K=10, Q2_0=41, IQ2_XXS=16)
    rows = [dict(name='blk.0.ffn_gate_exps.weight', shape=[2560, 640, 512], type='Q2_K', bytes=275251200),
            dict(name='blk.0.ffn_up_exps.weight', shape=[2560, 640, 512], type='Q2_K', bytes=275251200),
            dict(name='blk.0.ffn_down_exps.weight', shape=[640, 2560, 512], type='Q2_0', bytes=235929600)]
    header = bytearray(struct.pack('<IIQQ', 0x46554747, 3, len(rows), 0))
    cursor = 0
    for t in rows:
        name = t['name'].encode()
        header += struct.pack('<Q', len(name)) + name + struct.pack('<I', len(t['shape']))
        header += struct.pack('<' + 'Q' * len(t['shape']), *t['shape'])
        header += struct.pack('<IQ', kinds[t['type']], cursor)
        t['offset'] = cursor
        cursor += t['bytes']
    header += bytes((-len(header)) % 32)
    for t in rows:
        t['offset'] += len(header)
    original = bytes(header)
    changed = copy.deepcopy(rows)
    changed[1].update(type='IQ2_XXS', bytes=216268800)
    output, end = rewrite_header(original, rows, changed, kinds)
    result = parse(output)
    assert original == bytes(header)
    assert result[0] == ('blk.0.ffn_gate_exps.weight', [2560, 640, 512], 10, 0)
    assert result[1] == ('blk.0.ffn_up_exps.weight', [2560, 640, 512], 16, 275251200)
    assert result[2] == ('blk.0.ffn_down_exps.weight', [640, 2560, 512], 41, 491520000)
    assert end == len(header) + 727449600
    negative = 0
    for key, value in (('name', 'blk.1.ffn_up_exps.weight'), ('shape', [2560, 639, 512]), ('offset', 0), ('type', 'IQ2_XXS')):
        bad = copy.deepcopy(rows)
        bad[1][key] = value
        try:
            rewrite_header(original, bad, copy.deepcopy(changed), kinds)
        except RuntimeError:
            negative += 1
        else:
            raise AssertionError('Altered complete original descriptor was admitted: ' + key)
    print(dict(completed=True, positive_controls=5, negative_controls=negative, allocated_tensor_payload_bytes=0, PS5_operations=0))


if __name__ == '__main__':
    main()
